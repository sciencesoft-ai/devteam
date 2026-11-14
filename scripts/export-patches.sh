#!/usr/bin/env bash
# Regenerate patches/ from the commits on devteam-dev in $WORK_DIR
# (everything after tag devteam-upstream). Run after scripts/patch-dev.sh + edits.
source "$(dirname "$0")/lib.sh"

git -C "$WORK_DIR" rev-parse -q --verify refs/tags/devteam-upstream >/dev/null \
  || die "$WORK_DIR was not set up by scripts/patch-dev.sh"

# Overlay/rebrand output must never end up in a patch.
if [ -n "$(git -C "$WORK_DIR" status --porcelain)" ]; then
  die "uncommitted changes in $WORK_DIR; commit or discard them first"
fi

find "$PATCH_DIR" -maxdepth 1 -name '*.patch' -delete
git -C "$WORK_DIR" format-patch -q --zero-commit --no-signature --no-stat \
    --full-index -N -o "$PATCH_DIR" devteam-upstream..HEAD
# Number in tens so a patch can be inserted later without renaming the rest.
i=0
for p in $(find "$PATCH_DIR" -maxdepth 1 -name '*.patch' | sort); do
  i=$((i + 10))
  name="$(basename "$p" | sed -E 's/^[0-9]+-//')"
  mv "$p" "$PATCH_DIR/$(printf '%04d' "$i")-$name"
done
log "exported $((i / 10)) patch(es) to patches/"
git -C "$DEVTEAM_ROOT" status --short -- patches/
