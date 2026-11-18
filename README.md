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

Leave the internal names alone: `KIROCREW_*` env vars, the `kiro_crew` package, the in-install `kirocrew` launcher, the MCP server and default-agent id `kirocrew`. Renaming them would conflict on every sync. What DevTeam *publishes* is configured instead (next section).

## Side by side with stock Kiro Crew

Everything DevTeam publishes outside its own install comes from the **Side-by-side install** section of `devteam.conf`. That lets a machine run DevTeam and Kiro Crew together, and it lets a different distribution change these values without touching patches.

| Setting | DevTeam | Upstream | What it controls |
|---|---|---|---|
| `CLI_NAME` | `devteam` | `kirocrew` | Command on PATH (`~/.local/bin/devteam`), bundle `bin/devteam[.cmd]`, console script, `--version`, CLI usage. No `kirocrew` is published on PATH. Agents get both names in their private `<home>/kirocrew-bin/`. |
| `DATA_HOME` | `~/.devteam` | `~/.kiro/crew` | Default data home for the gateway, CLI and desktop app. Exported as `KIROCREW_HOME` at startup, so child processes use it too. The legacy `~/.kirocrew` migration is off. |
| `GATEWAY_PORT` | `5486` | `5476` | Default dashboard and gateway port. Upstream treats 5476 as a lock, so two products must not share it. |
| `DEFAULT_AGENT` | `claude` | `kas` | Harness used when `agent.acp_backend` is unset. An explicit choice is kept. |
| `URL_SCHEME` | `devteam` | `kirocrew` | Desktop deep links. |
| `SERVICE_NAME` | `devteam` | `kirocrew` | systemd unit, and the launchd label `dev.<name>.gateway`. |
| `DESKTOP_PACKAGE_NAME` | `devteam-desktop` | `kirocrew-desktop` | Desktop app data folder (`%APPDATA%\devteam-desktop`, `~/.config/devteam-desktop`) and Linux executable. |

How it's applied: patch `0010` makes upstream read these values from `src/kiro_crew/_distribution.py`, `website/electron/distribution.js` and `website/src/distribution.ts`, which hold upstream's values. `scripts/distribution.py` regenerates all three from `devteam.conf` during `prepare.sh`, and updates the packaging metadata to match.

Some state is still shared with stock Kiro Crew:

- A `KIROCREW_HOME` or `KIROCREW_PORT` exported in your shell still wins, for both products.
- kiro-cli's own `~/.kiro` (agents, settings) is shared. It belongs to kiro-cli, and only the Kiro or KAS backends use it.
- Existing data isn't migrated. To bring a Kiro Crew setup over, copy `~/.kiro/crew` to `~/.devteam` while both apps are stopped.

## User-visible text

`scripts/rewrite_strings.py` runs at the end of `prepare.sh`. It rewrites only text people read: string literals (never comments, docstrings or identifiers), dashboard catalog values in all 12 languages, HTML pages, the installer and the install scripts.

| What | Becomes | Where it's defined |
|---|---|---|
| "Kiro Crew" / "KiroCrew" in prose | `PRODUCT_NAME` | `rebrand/strings-rules.json` |
| `kirocrew <command>` hints | `CLI_NAME <command>` | `rebrand/strings-rules.json` |
| Kiro Crew's GitHub repo, issues, discussions, Discord | `REPO_URL` (source and doc links go to `SOURCE_REPO_URL`) | `rebrand/strings-rules.json` |
| "Kiro" as the assistant's name ("Things Kiro made for you"), and Kiro-branded art names | Neutral wording ("your agent", "built-in Chromium") | `rebrand/i18n-overrides.json`, per key and per language |
| The installer's "default agent requires Kiro CLI" page and the install scripts | Claude Code and its setup guide, when `DEFAULT_AGENT=claude` | `rewrite_agent_prerequisite()` |

Some text is deliberately left alone:

- **Kiro service text** (Kiro CLI, Kiro sign-in, Kiro credits, KAS). It's accurate for anyone who picks the Kiro backend.
- **Working service URLs** (the App catalog, Kiro sign-in endpoints, kiro-cli downloads, speech model downloads, the cloud bootstrap's git clone). Changing them would break features.
- **Links to specific upstream issues and PRs.**
- **Log messages, `src/kiro_crew/docs/`, and the security and sandbox modules.** The security strings include patterns the checks match on, so rewriting them could weaken a rule.

The overrides record the English text they were written against. If upstream rewords one of those strings, `prepare.sh` fails and names the key, so the translation can be reviewed rather than silently replacing the new text.

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
