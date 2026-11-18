"""Apply literal substitution rules (file<TAB>old<TAB>new on stdin) under a root dir.

Each rule must match at least once; otherwise exit non-zero so upstream drift
is caught at build time.
"""
import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(sys.argv[1])
    failures = []
    for lineno, raw in enumerate(sys.stdin.read().splitlines(), 1):
        if not raw.strip():
            continue
        try:
            rel, old, new = raw.split("\t")
        except ValueError:
            failures.append(f"rule {lineno}: expected 3 tab-separated fields")
            continue
        path = root / rel
        if not path.is_file():
            failures.append(f"{rel}: file not found")
            continue
        with open(path, encoding="utf-8", newline="") as fh:  # keep line endings as-is
            text = fh.read()
        count = text.count(old)
        if count == 0:
            failures.append(f"{rel}: no match for {old!r}")
            continue
        text = text.replace(old, new)
        if path.suffix == ".json":
            try:
                json.loads(text)
            except ValueError as exc:
                failures.append(f"{rel}: invalid JSON after {old!r} -> {new!r}: {exc}")
                continue
        path.write_text(text, encoding="utf-8", newline="")
        print(f"  {count:3d}x  {rel}: {old}  ->  {new}")
    for f in failures:
        print(f"  FAIL  {f}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
