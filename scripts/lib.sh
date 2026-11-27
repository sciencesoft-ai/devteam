#!/usr/bin/env bash
# Shared helpers for DevTeam scripts. Source, don't run.
set -euo pipefail

DEVTEAM_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../devteam.conf
source "$DEVTEAM_ROOT/devteam.conf"

# Prepared upstream tree (git-ignored). Override with WORK_DIR=...
WORK_DIR="${WORK_DIR:-$DEVTEAM_ROOT/work/kirocrew}"
PATCH_DIR="$DEVTEAM_ROOT/patches"
OVERLAY_DIR="$DEVTEAM_ROOT/overlay"
DEV_BRANCH="devteam-dev"
# Windows runners: set PYTHON=python (python3 there may be the Store stub).
PYTHON="${PYTHON:-python3}"

log()  { printf '\033[1;36m[devteam]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[devteam] error:\033[0m %s\n' "$*" >&2; exit 1; }

devteam_version() { echo "${UPSTREAM_REF#v}-${DEVTEAM_RELEASE}"; }

# Patches in apply order (numeric file-name prefix).
patch_list() { find "$PATCH_DIR" -maxdepth 1 -name '*.patch' | sort; }

# Identity for the throw-away commits made inside WORK_DIR.
git_work() {
  git -C "$WORK_DIR" -c user.name="devteam-build" -c user.email="devteam-build@localhost" \
      -c commit.gpgsign=false "$@"
}
