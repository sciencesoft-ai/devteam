#!/usr/bin/env bash
# Produce the DevTeam source tree in $WORK_DIR:
#   1. fresh checkout of UPSTREAM_REF (fork first, canonical upstream as fallback)
#   2. apply patches/*.patch as commits (git am)
#   3. copy overlay/ over the tree
#   4. apply value substitutions (scripts/rebrand.sh)
# Idempotent: always starts from a clean checkout.
source "$(dirname "$0")/lib.sh"

log "upstream ref: $UPSTREAM_REF"
rm -rf "$WORK_DIR"
mkdir -p "$(dirname "$WORK_DIR")"
git init -q "$WORK_DIR"
git_work remote add origin "$UPSTREAM_REPO"
git_work remote add canonical "$UPSTREAM_CANONICAL"

fetch_ref() {  # remote
  git_work fetch -q --depth 1 "$1" "refs/tags/$UPSTREAM_REF:refs/tags/$UPSTREAM_REF" 2>/dev/null
}
if fetch_ref origin; then
  log "fetched $UPSTREAM_REF from fork"
elif fetch_ref canonical; then
  log "fork lacks $UPSTREAM_REF; fetched from canonical upstream (run upstream-sync to mirror tags)"
else
  die "tag $UPSTREAM_REF not found in $UPSTREAM_REPO or $UPSTREAM_CANONICAL"
fi
git_work checkout -q -b "$DEV_BRANCH" "refs/tags/$UPSTREAM_REF"

# --- patches ---------------------------------------------------------------
mapfile -t PATCHES < <(patch_list)
if ((${#PATCHES[@]})); then
  log "applying ${#PATCHES[@]} patch(es)"
  for p in "${PATCHES[@]}"; do
    if ! git_work am -q --3way "$p"; then
      git_work am --abort || true
      die "patch failed to apply: $(basename "$p")  (fix with scripts/patch-dev.sh, then scripts/export-patches.sh)"
    fi
    log "  ok  $(basename "$p")"
  done
fi
git_work tag -f devteam-patched >/dev/null

# --- overlay -----------------------------------------------------------------
if find "$OVERLAY_DIR" -type f ! -name README.md | grep -q .; then
  log "copying overlay/"
  (cd "$OVERLAY_DIR" && find . -type f ! -name README.md -print0) |
    while IFS= read -r -d '' f; do
      install -D -m 0644 "$OVERLAY_DIR/$f" "$WORK_DIR/$f"
    done
fi

# --- distribution identity (data home, port, CLI name, default agent, ...) ----
log "writing distribution identity"
PRODUCT_NAME="$PRODUCT_NAME" CLI_NAME="$CLI_NAME" DATA_HOME="$DATA_HOME" \
GATEWAY_PORT="$GATEWAY_PORT" DEFAULT_AGENT="$DEFAULT_AGENT" URL_SCHEME="$URL_SCHEME" \
SERVICE_NAME="$SERVICE_NAME" DESKTOP_PACKAGE_NAME="$DESKTOP_PACKAGE_NAME" \
  "$PYTHON" -I "$DEVTEAM_ROOT/scripts/distribution.py" "$WORK_DIR" \
  || die "distribution identity failed (see message above)"

# --- value substitutions -----------------------------------------------------
"$DEVTEAM_ROOT/scripts/rebrand.sh"

# --- user-visible text --------------------------------------------------------
if [ ! -d "$DEVTEAM_ROOT/scripts/strings/node_modules/@babel/parser" ]; then
  log "installing the text-rewrite parser (scripts/strings)"
  npm ci --prefix "$DEVTEAM_ROOT/scripts/strings" --silent --no-audit --no-fund \
    || die "npm ci in scripts/strings failed (Node.js is required)"
fi
log "rewriting user-visible text"
PRODUCT_NAME="$PRODUCT_NAME" CLI_NAME="$CLI_NAME" REPO_URL="$REPO_URL" \
SOURCE_REPO_URL="$SOURCE_REPO_URL" DEFAULT_AGENT="$DEFAULT_AGENT" \
  "$PYTHON" -I "$DEVTEAM_ROOT/scripts/rewrite_strings.py" "$WORK_DIR" \
  || die "text rewrite failed (see message above)"

echo "$(devteam_version)" > "$WORK_DIR/.devteam-version"
log "prepared $(devteam_version) in $WORK_DIR"
