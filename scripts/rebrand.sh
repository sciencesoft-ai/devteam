#!/usr/bin/env bash
# Value substitutions applied to $WORK_DIR after patches and overlay.
#
# For changes that are "swap value A for value B" (hosts, names, ids) this is
# sturdier than a patch: it doesn't depend on surrounding lines, so upstream
# churn nearby doesn't break it. Every rule REQUIRES at least one match, so if
# upstream moves or renames a value the build fails loudly instead of shipping
# a binary that still points at Kiro's update servers.
#
# Rule format (one per line):  file<TAB>old<TAB>new   (new may be empty = delete)
#
# Windows signing: upstream signs through its own AWS Signer hook
# (win.signtoolOptions.sign). We drop that hook so electron-builder signs with
# our certificate from WIN_CSC_LINK / WIN_CSC_KEY_PASSWORD; no cert -> unsigned.
# Internals (KIROCREW_* env vars, ~/.kiro/crew, kiro_crew package) are left
# alone on purpose: renaming them would conflict on every upstream sync.
source "$(dirname "$0")/lib.sh"

UPD_OLD="https://updates.crew.kiro.dev"
DL_OLD="https://download.crew.kiro.dev"

# install.sh (the pip/curl route) resolves the data home and port itself.
INSTALL_HOME="\$HOME/${DATA_HOME#\~/}"

RULES="$(cat <<EOF
install.sh	KIROCREW_DATA_DIR="\${KIROCREW_HOME:-\$HOME/.kiro/crew}"	KIROCREW_DATA_DIR="\${${ENV_PREFIX}_HOME:-$INSTALL_HOME}"
install.sh	KIROCREW_PORT="\${KIROCREW_PORT:-5476}"	KIROCREW_PORT="\${${ENV_PREFIX}_PORT:-$GATEWAY_PORT}"
src/kiro_crew/platform/update_layout.py	$UPD_OLD	$UPDATE_FEED_BASE
src/kiro_crew/platform/update_layout.py	$DL_OLD	$DOWNLOAD_BASE
website/electron/auto-update.js	$UPD_OLD	$UPDATE_FEED_BASE
website/electron/auto-update.js	$DL_OLD	$DOWNLOAD_BASE
website/electron/package.json	$UPD_OLD	$UPDATE_FEED_BASE
cli.sh	$UPD_OLD	$UPDATE_FEED_BASE
cli.sh	$DL_OLD	$DOWNLOAD_BASE
install.sh	$DL_OLD	$DOWNLOAD_BASE
setup.sh	$DL_OLD	$DOWNLOAD_BASE
minimal_install.sh	$DL_OLD	$DOWNLOAD_BASE
website/electron/package.json	"appId": "com.amazon.kiro.crew"	"appId": "$APP_ID"
website/electron/package.json	"productName": "KiroCrew"	"productName": "$PRODUCT_NAME"
website/electron/package.json	"Amazon Web Services, Inc."	"$WIN_PUBLISHER_NAME"
packaging/build-desktop.sh	PRODUCT_NAME="KiroCrew Nightly"	PRODUCT_NAME="$PRODUCT_NAME Nightly"
packaging/build-desktop.sh	PRODUCT_NAME="KiroCrew"	PRODUCT_NAME="$PRODUCT_NAME"
packaging/build-desktop.sh	KiroCrew Nightly	$PRODUCT_NAME Nightly
website/electron/package.json	"maintainer": "Kiro Crew Maintainers <maintainers@crew.kiro.dev>"	"maintainer": "$PACKAGE_MAINTAINER"
website/electron/package.json	"sign": "./scripts/sign-windows.js",	
website/electron/main.js	"com.amazon.kiro.crew.nightly"	"$APP_ID.nightly"
website/electron/main.js	"com.amazon.kiro.crew"	"$APP_ID"
packaging/build-desktop.sh	-c.win.appId=com.amazon.kiro.crew.nightly	-c.win.appId=$APP_ID.nightly
packaging/build-desktop.sh	-c.nsis.guid=0f417bf9-2759-51d6-acfb-f864805d1f41	-c.nsis.guid=$NIGHTLY_NSIS_GUID
EOF
)"

log "applying value substitutions"
"$PYTHON" -I "$DEVTEAM_ROOT/scripts/rebrand.py" "$WORK_DIR" <<<"$RULES" \
  || die "rebrand failed (an upstream value moved; update scripts/rebrand.sh)"
