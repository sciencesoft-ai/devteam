# DevTeam

DevTeam is a custom distribution of [KiroCrew](https://github.com/kirodotdev/kirocrew).
This repo holds no copy of the upstream code. It holds:

- the pinned upstream version
- our changes, kept as patches, overlay files and value substitutions
- the build and sync automation

Each build starts from a clean upstream release tag and applies those changes on top.

```
devteam.conf          pinned upstream tag, product name, app id, update hosts, signing names
patches/              our code changes, as a git format-patch series (applied in order)
overlay/              whole files copied over the tree (icons, banner, default config)
extensions/           DevTeam skills / MCP servers / hooks / Apps — no patching needed
certs/                public signing certificates (never private keys) + how to trust them
scripts/
  prepare.sh          tag checkout → patches → overlay → rebrand  (output: work/kirocrew)
  rebrand.sh/.py      literal value swaps (update hosts, appId, product name); fail if a value is gone
  build.sh [target]   prepare + upstream `make <target>` (wheel | desktop | test); artifacts → dist/
  patch-dev.sh        set up work/kirocrew for editing patches
  export-patches.sh   write the edited commits back into patches/
  check-upstream.sh   newest stable upstream tag
.github/workflows/
  build.yml           prepare + build wheel on every push / PR
  build-windows.yml   signed NSIS installer (windows-latest); verifies the signer thumbprint
  upstream-sync.yml   daily: new stable tag → PR (or an issue if patches break)
```

Repos:

- `sciencesoft-ai/KiroCrew` is our fork. We use it as a mirror and to send PRs back upstream. We never ship from it.
- `kirodotdev/kirocrew` is the canonical upstream. `prepare.sh` falls back to it when the fork doesn't carry the pinned tag yet.

## Build

Requirements: git, Python 3.12+, Node 22.12+, make.

```bash
scripts/build.sh            # → dist/kirocrew-<ver>-py3-none-any.whl  (installs `kirocrew` and `devteam`)
scripts/build.sh desktop    # DMG / AppImage — see upstream docs/build/desktop-app.md for host needs
```

Windows installer: the build runs in CI (`build-windows.yml`, or run it by hand from the Actions tab). To build locally on Windows, use Git Bash with Node 24, Python 3.12 and uv:

```bash
PYTHON=python scripts/prepare.sh
cd work/kirocrew
WIN_CSC_LINK=/c/path/devteam-codesign.pfx WIN_CSC_KEY_PASSWORD=... bash packaging/build-desktop.sh
# → website/electron/dist/DevTeam Setup <ver>.exe
```

## Where a change goes (try in this order)

1. **Extension points:** skills, MCP servers, hooks, Apps, `config.json` defaults, security policy JSON. Put these in `extensions/` or `overlay/`. No patch needed.
2. **Overlay:** a whole file replaced, for example icons. Mirror the upstream path under `overlay/`.
3. **Value substitution:** a host, a name or an id. Add a rule to `scripts/rebrand.sh`.
4. **Patch:** a logic change that is small and covers one concern.
5. **Upstream PR:** if a patch only adds an option or a hook, send it upstream from the fork and delete the patch once a release includes it.

Leave the internal names alone: `KIROCREW_*` env vars, `~/.kiro/crew`, the `kiro_crew` package and the `kirocrew` command. Renaming them would conflict on every sync.

## Editing patches

```bash
scripts/patch-dev.sh                 # work/kirocrew = tag + one commit per patch
cd work/kirocrew
# new patch:      edit files; git commit -m "area: what and why"
# change a patch: git rebase -i devteam-upstream   (edit / fixup that commit)
cd ../.. && scripts/export-patches.sh
git add patches && git commit
```

## Moving to a new upstream release

`upstream-sync.yml` handles this daily. To do it by hand:

1. Set `UPSTREAM_REF` in `devteam.conf` and reset `DEVTEAM_RELEASE="1"`.
2. Run `scripts/prepare.sh`.
3. If a patch fails, run `scripts/patch-dev.sh`, resolve the conflict, then `scripts/export-patches.sh`.
4. If a rebrand rule fails, upstream moved or renamed the value. Update `scripts/rebrand.sh`.

Versions are labelled `<upstream tag>+devteam.<DEVTEAM_RELEASE>`, for example `v0.12.2+devteam.1`. Bump `DEVTEAM_RELEASE` for each DevTeam-only release on the same upstream tag.

## Before the first public release

- [ ] Real update and download hosts in `devteam.conf`. The placeholders end in `.invalid` on purpose, so that auto-update fails closed instead of installing stock KiroCrew.
- [ ] Host the update feed. electron-updater reads `<UPDATE_FEED_BASE>/feed/<channel>/latest-*.yml`, and the Python updater uses the same two bases. See upstream `docs/build/release.md`.
- [x] Windows signing: self-signed `CN=ScienceSoft AI DevTeam`, expires 2027-11-15. See `certs/README.md`, including how to trust it on user machines.
- [ ] macOS signing and notarization (Apple Developer ID), wheel signing keys, and a release workflow that publishes to the update feed.
- [ ] DevTeam icons and banner in `overlay/` (paths below).
- [ ] `PACKAGE_MAINTAINER` in `devteam.conf`.
- [ ] Decide on the `kirocrew://` URL scheme. It is left unchanged for now because the app's code uses it.
- [ ] Telemetry: upstream ships it **off** by default (`telemetry` config section). Keep it off, or point the beacon endpoint at our own collector.
- [ ] About 13 upstream test files pin Kiro's update hosts and appId. `scripts/build.sh test` fails on those until they are patched or skipped.
- [ ] Apache-2.0: keep upstream `LICENSE`, `NOTICE` and `THIRD-PARTY-NOTICES` in what we ship. `patches/` documents our modifications. Don't ship Kiro or AWS names or logos as our branding.

## CI secrets

| Secret | Used by | Purpose |
|---|---|---|
| `FORK_PUSH_TOKEN` | upstream-sync | Fine-grained PAT with contents write on `sciencesoft-ai/KiroCrew`. Syncs the fork's main and creates release tags there. Optional. |
| `WIN_CSC_LINK` | build-windows | Base64 of the Windows code-signing `.pfx` (see `certs/README.md`). |
| `WIN_CSC_KEY_PASSWORD` | build-windows | Password for that `.pfx`. |
| `SYNC_PR_TOKEN` | upstream-sync | PAT used to open sync PRs, so that `build.yml` runs on them. Optional. |
