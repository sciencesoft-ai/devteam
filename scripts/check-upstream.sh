#!/usr/bin/env bash
# Print the newest stable upstream tag (vX.Y.Z, no -insider/-nightly/-rc).
# Exit 10 if it equals UPSTREAM_REF, 0 if newer one exists (printed on stdout).
source "$(dirname "$0")/lib.sh"

latest="$(git ls-remote --tags --refs "$UPSTREAM_CANONICAL" \
  | sed 's#.*refs/tags/##' \
  | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' \
  | sort -V | tail -1)"
[ -n "$latest" ] || die "no stable tags found at $UPSTREAM_CANONICAL"

echo "$latest"
[ "$latest" != "$UPSTREAM_REF" ] || exit 10
