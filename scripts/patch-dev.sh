#!/usr/bin/env bash
# Set up $WORK_DIR for editing patches.
#
# Leaves branch devteam-dev = upstream tag + one commit per patch, with NO
# overlay or rebrand applied, so commits you make contain only real changes.
#
#   scripts/patch-dev.sh
#   cd work/kirocrew
#   # new patch:   edit, git commit -m "area: what and why"
#   # amend patch: git rebase -i devteam-upstream   (edit / fixup the commit)
#   cd ../.. && scripts/export-patches.sh
source "$(dirname "$0")/lib.sh"

rm -rf "$WORK_DIR"
mkdir -p "$(dirname "$WORK_DIR")"
git init -q "$WORK_DIR"
git_work remote add origin "$UPSTREAM_REPO"
git_work remote add canonical "$UPSTREAM_CANONICAL"
git_work fetch -q --depth 1 origin "refs/tags/$UPSTREAM_REF:refs/tags/$UPSTREAM_REF" 2>/dev/null \
  || git_work fetch -q --depth 1 canonical "refs/tags/$UPSTREAM_REF:refs/tags/$UPSTREAM_REF" \
  || die "tag $UPSTREAM_REF not found"
git_work checkout -q -b "$DEV_BRANCH" "refs/tags/$UPSTREAM_REF"
git_work tag -f devteam-upstream >/dev/null

mapfile -t PATCHES < <(patch_list)
for p in "${PATCHES[@]}"; do
  git_work am -q --3way "$p" || die "conflict in $(basename "$p"): resolve in $WORK_DIR, 'git am --continue', apply the rest with 'git am --3way ../../patches/<next>.patch', then export"
done
log "ready: $WORK_DIR on $DEV_BRANCH (${#PATCHES[@]} patch commits on top of tag devteam-upstream)"
log "your git identity is used for new commits; run scripts/export-patches.sh when done"
