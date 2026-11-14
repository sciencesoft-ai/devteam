#!/usr/bin/env bash
# Prepare the DevTeam tree, then run an upstream make target inside it.
#
#   scripts/build.sh            # make wheel   (default)
#   scripts/build.sh desktop    # make desktop (DMG / AppImage; needs node, see upstream docs/build)
#   scripts/build.sh test       # upstream test suite on the DevTeam tree
#   SKIP_PREPARE=1 scripts/build.sh wheel   # reuse an existing work/ tree
source "$(dirname "$0")/lib.sh"

TARGET="${1:-wheel}"
EDITION="${EDITION:-oss}"

[ "${SKIP_PREPARE:-0}" = 1 ] || "$DEVTEAM_ROOT/scripts/prepare.sh"

log "make $TARGET EDITION=$EDITION  ($(devteam_version))"
make -C "$WORK_DIR" "$TARGET" EDITION="$EDITION"

mkdir -p "$DEVTEAM_ROOT/dist"
if compgen -G "$WORK_DIR/dist/*" >/dev/null; then
  cp -a "$WORK_DIR"/dist/* "$DEVTEAM_ROOT/dist/"
  log "artifacts copied to dist/"
fi
