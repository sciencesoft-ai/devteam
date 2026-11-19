"""Rebrand user-visible text in the prepared tree.

Rewrites ONLY text a person reads: string literals (never docstrings, comments or
identifiers), dashboard catalog values, HTML, installer messages. Rules live in
rebrand/strings-rules.json (product name, `kirocrew <cmd>` hints, Kiro Crew's own
GitHub/Discord links); per-key catalog rewrites in every language live in
rebrand/i18n-overrides.json; the installer's default-agent prerequisite page is
rewritten for DEFAULT_AGENT=claude.

Out of scope here, on purpose:
  - log messages (logger calls) and the docs shipped under src/kiro_crew/docs/;
  - src/kiro_crew/security/ and the sandbox modules: their strings include patterns
    the security checks match on, and rewriting a pattern could weaken a rule;
  - Kiro-service text (Kiro CLI, Kiro sign-in, KAS): accurate for anyone who picks
    the Kiro backend; and working service URLs (app catalog, sign-in endpoints).

Usage: rewrite_strings.py <tree>    (values from devteam.conf via environment)
"""
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
HERE = Path(__file__).resolve().parent
DEVTEAM = HERE.parent


def env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        sys.exit(f"rewrite_strings: {name} not set")
    return value


PRODUCT = env("PRODUCT_NAME")
CLI = env("CLI_NAME")
REPO = env("REPO_URL").rstrip("/")
SRC = env("SOURCE_REPO_URL").rstrip("/")
AGENT = env("DEFAULT_AGENT")
for url in (REPO, SRC):
    if not url.startswith("https://"):
        sys.exit(f"rewrite_strings: {url} must be an https:// URL")

values = {"{PRODUCT}": PRODUCT, "{CLI}": CLI, "{REPO_HP}": REPO[len("https://"):], "{SRC_HP}": SRC[len("https://"):],
          "{REPO_PATH}": REPO[len("https://github.com/"):] if REPO.startswith("https://github.com/") else "kirodotdev/KiroCrew"}
spec = json.loads((DEVTEAM / "rebrand/strings-rules.json").read_text(encoding="utf-8"))
RULES = []
for group in ("links", "product", "cli"):
    for r in spec[group]:
        rep = r["replace"]
        for k, v in values.items():
            rep = rep.replace(k, v)
        RULES.append({"find": r["find"], "replace": rep, "prose_only": r.get("prose_only", False), "group": group})


def py_rules(groups):
    out = []
    for r in RULES:
        if r["group"] in groups:
            out.append((re.compile(r["find"]), re.sub(r"\$(\d)", r"\\\1", r["replace"].replace("\\", "\\\\")), r["prose_only"]))
    return out


ALL = py_rules({"links", "product", "cli"})
NO_CLI = py_rules({"links", "product"})


def rewrite_text(text, rules=ALL):
    prose = bool(re.search(r"\s", text))
    for rx, rep, prose_only in rules:
        if prose_only and not prose:
            continue
        text = rx.sub(rep, text)
    return text


TEST = re.compile(r"(^|/)(test|tests|__tests__|e2e|playwright|fixtures|mocks?)(/|$)|\.(test|spec|stories)\.|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$")
SKIP_PY = re.compile(r"^src/kiro_crew/(security/|sandbox[^/]*\.py$|hooks\.py$|hook_runtime/|docs/|_distribution\.py$)")
LOGGER = re.compile(r"^(logger|log|_log|_logger|LOGGER|logging)$")
LOG_METHODS = {"debug", "info", "warning", "warn", "error", "exception", "critical", "log"}


def git_files(*pathspecs):
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--", *pathspecs], capture_output=True, text=True, check=True)
    return [p for p in out.stdout.split() if not TEST.search(p)]


# ---------------------------------------------------------------- Python ----
def is_log_call(node):
    f = getattr(node, "func", None)
    if not isinstance(f, ast.Attribute) or f.attr not in LOG_METHODS:
        return False
    base = f.value
    name = getattr(base, "id", None) or getattr(base, "attr", None) or ""
    return bool(LOGGER.match(name)) or name.endswith("logger") or name.endswith("_log")


def rewrite_python(rel):
    path = ROOT / rel
    raw = path.read_bytes()
    if b"iro" not in raw:
        return 0
    try:
        tree = ast.parse(raw)
    except SyntaxError:
        return 0
    skip = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list):
            for stmt in body:
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                    skip.add(id(stmt.value))  # docstrings and bare string statements
        if isinstance(node, ast.Call) and is_log_call(node):
            for sub in ast.walk(node):
                skip.add(id(sub))
    lines = raw.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln))
    spans = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)) or id(node) in skip:
            continue
        if "iro" not in node.value or node.end_lineno is None:
            continue
        s = starts[node.lineno - 1] + node.col_offset
        e = starts[node.end_lineno - 1] + node.end_col_offset
        piece = raw[s:e].decode("utf-8")
        prose = bool(re.search(r"\s", node.value))
        new = piece
        for rx, rep, prose_only in ALL:
            if prose_only and not prose:
                continue
            new = rx.sub(rep, new)
        if new != piece:
            spans.append((s, e, new.encode("utf-8")))
    if not spans:
        return 0
    # Nested f-string parts can overlap their parent only if both were taken; keep outermost-first unique.
    spans.sort(key=lambda t: t[0], reverse=True)
    out = raw
    last_start = None
    for s, e, text in spans:
        if last_start is not None and e > last_start:
            continue
        out = out[:s] + text + out[e:]
        last_start = s
    ast.parse(out)  # must still parse
    path.write_bytes(out)
    return len(spans)


# ------------------------------------------------------------- data files ---
COMMENT = {".sh": re.compile(r"^\s*#"), ".ps1": re.compile(r"^\s*#"), ".nsh": re.compile(r"^\s*[;#]")}


def rewrite_lines(rel, rules=ALL):
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    if "iro" not in text:
        return 0
    cm = COMMENT.get(path.suffix)
    n = 0
    out = []
    for line in text.splitlines(keepends=True):
        if cm is None or not cm.match(line):
            new = rewrite_text(line, rules)
            n += new != line
            line = new
        out.append(line)
    if n:
        path.write_text("".join(out), encoding="utf-8", newline="")
    return n


# ---------------------------------------------------------------- catalogs ---
def map_strings(obj, fn):
    if isinstance(obj, dict):
        return {k: map_strings(v, fn) for k, v in obj.items()}
    if isinstance(obj, list):
        return [map_strings(v, fn) for v in obj]
    return fn(obj) if isinstance(obj, str) else obj


def set_key(d, dotted, value):
    parts = dotted.split(".")
    for p in parts[:-1]:
        if p not in d or not isinstance(d[p], dict):
            return False
        d = d[p]
    if parts[-1] not in d:
        return False
    d[parts[-1]] = value
    return True


def get_key(d, dotted):
    for p in dotted.split("."):
        if not isinstance(d, dict) or p not in d:
            return None
        d = d[p]
    return d


def rewrite_catalogs():
    loc = ROOT / "website/src/i18n/locales"
    overrides = json.loads((DEVTEAM / "rebrand/i18n-overrides.json").read_text(encoding="utf-8"))
    upstream_en = {}
    for fn in ("en.json", "en.manual.json"):
        data = json.loads((loc / fn).read_text(encoding="utf-8"))
        for k in overrides:
            v = get_key(data, k)
            if v is not None:
                upstream_en[k] = (fn, v)
    stale = [k for k, row in overrides.items() if k not in upstream_en or upstream_en[k][1] != row["upstream_en"]]
    if stale:
        sys.exit("rewrite_strings: upstream changed the English source of these overridden keys; "
                 "review and update rebrand/i18n-overrides.json:\n  " + "\n  ".join(stale))
    keep = json.loads((DEVTEAM / "rebrand/i18n-keep.json").read_text(encoding="utf-8"))["keys"]
    changed = 0
    for file in sorted(loc.glob("*.json")):
        lang = file.stem
        if lang == "en-XA":
            continue  # pseudo-locale, regenerated from en below
        data = json.loads(file.read_text(encoding="utf-8"))
        before = json.dumps(data, ensure_ascii=False)
        kept = {k: get_key(data, k) for k in keep}
        data = map_strings(data, rewrite_text)
        for k, v in kept.items():
            if v is not None:
                set_key(data, k, v)
        target_lang = "en" if lang in ("en", "en.manual") else lang
        for key, row in overrides.items():
            if target_lang in row and get_key(data, key) is not None:
                set_key(data, key, row[target_lang])
        after = json.dumps(data, ensure_ascii=False)
        if after != before:
            file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="")
            changed += 1
    gen = ROOT / "website/scripts/gen-pseudolocale.mjs"
    if gen.is_file():
        r = subprocess.run(["node", str(gen)], cwd=ROOT / "website", capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"rewrite_strings: gen-pseudolocale failed:\n{r.stderr[-2000:]}")
    return changed


# ------------------------------------------------------ default-agent text ---
CLAUDE_SETUP = "https://code.claude.com/docs/en/setup"


def rewrite_agent_prerequisite():
    """The Windows installer's Finish page and the shell installers tell a new user
    what the DEFAULT agent needs. With DEFAULT_AGENT=claude that is Claude Code."""
    if AGENT != "claude":
        return 0
    n = 0
    nsh = ROOT / "website/electron/build/installer.nsh"
    text = nsh.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    out = []
    for line in lines:
        if line.startswith(("LangString KiroCliPrerequisiteText ", "LangString KiroCliPrerequisiteLink ")):
            # Only the quoted text: the LangString id is referenced elsewhere as $(KiroCli...).
            head, sep, value = line.partition('"')
            new = head + sep + value.replace("kiro-cli login", "claude").replace("Kiro CLI", "Claude Code").replace("Kiro", "Claude")
            n += new != line
            line = new
        out.append(line)
    text = "".join(out)
    old_link = '!define MUI_FINISHPAGE_LINK_LOCATION "https://kiro.dev/cli/"'
    if old_link not in text or n < 2:
        sys.exit("rewrite_strings: installer.nsh prerequisite page changed upstream; update rewrite_agent_prerequisite()")
    text = text.replace(old_link, f'!define MUI_FINISHPAGE_LINK_LOCATION "{CLAUDE_SETUP}"')
    nsh.write_text(text, encoding="utf-8", newline="")
    n += 1

    # Shell installers (pip / curl route): message lines, and setup.sh's presence check.
    subs = [
        ("The default Kiro agent requires Kiro CLI", "The default agent requires Claude Code"),
        ("Kiro CLI is required for the default agent", "Claude Code is required for the default agent"),
        ("https://kiro.dev/cli/ and run: kiro-cli login", f"{CLAUDE_SETUP} and run: claude"),
        ("https://kiro.dev/cli/", CLAUDE_SETUP),
        ("_check kiro-cli", "_check claude"),
        ("(which kiro-cli)", "(which claude)"),
        ("✅ kiro-cli", "✅ claude"),
        ("Sign in separately with: kiro-cli login", "Sign in separately by running: claude"),
        ("kiro-cli login", "claude"),
        ("Kiro CLI", "Claude Code"),
    ]
    for rel in ("install.sh", "minimal_install.sh", "setup.sh"):
        path = ROOT / rel
        if not path.is_file():
            continue
        changed = 0
        out = []
        for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
            if re.match(r"\s*#", line) or not re.search(r"Kiro CLI|kiro-cli|kiro\.dev/cli|default Kiro agent", line):
                out.append(line)
                continue
            if "kas install" in line and "no kiro-cli" in line:
                changed += 1  # the KAS-engine alternative only applies to a Kiro default
                continue
            new = line
            for old, rep in subs:
                new = new.replace(old, rep)
            changed += new != line
            out.append(new)
        if not changed:
            sys.exit(f"rewrite_strings: {rel}: no default-agent prerequisite text found; update rewrite_agent_prerequisite()")
        path.write_text("".join(out), encoding="utf-8", newline="")
        n += changed
    return n


def main():
    total = {}
    # Python sources (backend, CLI, built-in skills' scripts)
    py = [p for p in git_files("src/kiro_crew") if p.endswith(".py") and not SKIP_PY.search(p)]
    total["python"] = sum(rewrite_python(p) for p in py)
    # Text/data shipped in the package (agent prompts, skills, pages) -- not the docs tree
    data = [p for p in git_files("src/kiro_crew") if re.search(r"\.(md|j2|jinja|txt|html|htm|json|ya?ml)$", p)
            and not SKIP_PY.search(p) and not p.endswith(".generated.json")]
    total["package text"] = sum(rewrite_lines(p) for p in data)
    # Dashboard + desktop shell code
    js = [p for p in git_files("website/src", "website/electron")
          if re.search(r"\.(ts|tsx|js|cjs|mjs|jsx)$", p) and "/node_modules/" not in p
          and not p.startswith(("website/electron/scripts/", "website/src/i18n/locales/")) and not p.endswith(".d.ts")]
    rules_file = ROOT.parent / ".strings-rules.expanded.json"
    rules_file.write_text(json.dumps(RULES), encoding="utf-8", newline="")
    r = subprocess.run(["node", str(HERE / "strings/rewrite_js.js"), str(rules_file)],
                       input="\n".join(str(ROOT / p) for p in js), capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"rewrite_strings: JS pass failed:\n{r.stderr[-2000:]}")
    total["js/ts"] = json.loads(r.stdout)["edits"]
    # Pages, manifest, desktop HTML, installers
    pages = ["website/index.html", "website/public/manifest.json"] + [
        p for p in git_files("website/electron") if p.endswith((".html", ".nsh")) and "/node_modules/" not in p]
    total["pages/installer"] = sum(rewrite_lines(p) for p in pages if (ROOT / p).is_file())
    scripts = [p for p in ("cli.sh", "install.sh", "setup.sh", "minimal_install.sh", "cloud-install.sh", "install.ps1") if (ROOT / p).is_file()]
    total["install scripts"] = sum(rewrite_lines(p) for p in scripts)
    # Desktop build script: app names it hands electron-builder (menu entry, macOS
    # display name). Product name only -- its `kirocrew` references are functional.
    total["desktop build"] = rewrite_lines("packaging/build-desktop.sh", NO_CLI)
    # Desktop package metadata a person sees: macOS app name, permission prompts, About.
    pkg = ROOT / "website/electron/package.json"
    data = json.loads(pkg.read_text(encoding="utf-8"))
    new = map_strings(data, lambda v: rewrite_text(v, NO_CLI))
    if new != data:
        pkg.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="")
    total["desktop package"] = int(new != data)
    total["catalog files"] = rewrite_catalogs()
    total["agent prerequisite"] = rewrite_agent_prerequisite()
    print("  strings: " + ", ".join(f"{k} {v}" for k, v in total.items()))
    regenerate_indexes()


def regenerate_indexes():
    """The dashboard build refuses generated indexes that no longer match the
    source (settings registry, UI location index). The text above changed the
    source, so regenerate them -- here, so every build route (make, the desktop
    script) starts from a consistent tree."""
    web = ROOT / "website"
    npm = "npm.cmd" if os.name == "nt" else "npm"
    if not (web / "node_modules").is_dir():
        r = subprocess.run([npm, "ci", "--no-audit", "--no-fund"], cwd=web, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"rewrite_strings: npm ci in website/ failed:\n{r.stderr[-2000:]}")
    for script in ("gen:settings", "gen:ui"):
        r = subprocess.run([npm, "run", "--silent", script], cwd=web, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"rewrite_strings: npm run {script} failed:\n{(r.stdout + r.stderr)[-2000:]}")
    print("  regenerated: settings registry, UI location index")


main()
