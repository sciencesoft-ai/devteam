"""Apply literal substitution rules (file<TAB>old<TAB>new on stdin) under a root dir.

Each rule must match at least once; otherwise exit non-zero so upstream drift
is caught at build time.
"""
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
        text = path.read_text(encoding="utf-8")
        count = text.count(old)
        if count == 0:
            failures.append(f"{rel}: no match for {old!r}")
            continue
        path.write_text(text.replace(old, new), encoding="utf-8")
        print(f"  {count:3d}x  {rel}: {old}  ->  {new}")
    for f in failures:
        print(f"  FAIL  {f}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
