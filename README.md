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
overlay/              whole files copied over the tree (generated artwork, default config)
brand/                artwork masters (icon, mark, lockup, character) and the Open Sans fonts
extensions/           DevTeam skills / MCP servers / hooks / Apps — no patching needed
certs/                public signing certificates (never private keys) + how to trust them
scripts/
  prepare.sh          tag checkout → patches → overlay → rebrand  (output: work/kirocrew)
  rebrand.sh/.py      literal value swaps (update hosts, appId, product name); fail if a value is gone
  build.sh [target]   prepare + upstream `make <target>` (wheel | desktop | test); artifacts → dist/
  patch-dev.sh        set up work/kirocrew for editing patches
  brand_assets.py     regenerate all artwork in overlay/ and brand/ (see overlay/README.md)
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
| `DATA_HOME` | `~/.devteam` | `~/.kiro/crew` | Default data home for the gateway, CLI and desktop app. `DEVTEAM_HOME` overrides it. Exported as `KIROCREW_HOME` at startup, so child processes use it too. The legacy `~/.kirocrew` migration is off. |
| `GATEWAY_PORT` | `5486` | `5476` | Default dashboard and gateway port. `DEVTEAM_PORT` overrides it. Upstream treats 5476 as a lock, so two products must not share it. |
| `ENV_PREFIX` | `DEVTEAM` | `KIROCREW` | The variables users set: `DEVTEAM_HOME`, `DEVTEAM_PORT`, `DEVTEAM_TELEMETRY_DISABLED`. A `KIROCREW_HOME` or `KIROCREW_PORT` in the user's shell is ignored (patch `0020`). `KIROCREW_TELEMETRY_DISABLED` still turns telemetry off, so an opt-out isn't lost (patch `0030`). |
| `DEFAULT_AGENT` | `claude` | `kas` | Harness used when `agent.acp_backend` is unset. An explicit choice is kept. |
| `URL_SCHEME` | `devteam` | `kirocrew` | Desktop deep links. |
| `SERVICE_NAME` | `devteam` | `kirocrew` | systemd unit, and the launchd label `dev.<name>.gateway`. |
| `DESKTOP_PACKAGE_NAME` | `devteam-desktop` | `kirocrew-desktop` | Desktop app data folder (`%APPDATA%\devteam-desktop`, `~/.config/devteam-desktop`) and Linux executable. |
| `TELEMETRY_ENDPOINT` | placeholder | Kiro's collector | Anonymous usage beacon, and App install receipts, which reuse it (patch `0030`). |
| `FEEDBACK_ENDPOINT` | placeholder | AWS-hosted Kiro feedback | In-app feedback survey: `POST <endpoint>/form` and `<endpoint>/form/prompt`, in the AWS Aperture form API shape (patch `0030`). |
| `COMMUNITY_URL` | empty (hidden) | Kiro's Discord | Community button in the nav rail (patch `0030`). |

How it's applied: patch `0010` makes upstream read these values from `src/kiro_crew/_distribution.py`, `website/electron/distribution.js` and `website/src/distribution.ts`, which hold upstream's values. `scripts/distribution.py` regenerates all three from `devteam.conf` during `prepare.sh`, and updates the packaging metadata to match.

How `DEVTEAM_HOME` / `DEVTEAM_PORT` work: internally the code still reads `KIROCREW_*`. The first DevTeam process started from a plain shell (CLI, desktop app or service) drops any `KIROCREW_HOME` / `KIROCREW_PORT`, copies the `DEVTEAM_*` values into them, and sets `DEVTEAM_ENV_MAPPED=1`. Processes DevTeam starts inherit that mark and keep the values their parent gave them. `devteam service install` saves the port as `DEVTEAM_PORT` in the unit.

DevTeam never reads or imports stock Kiro Crew's data: it starts with an empty `~/.devteam`.

Still shared with stock Kiro Crew: kiro-cli's own `~/.kiro` (agents, settings). It belongs to kiro-cli, and only the Kiro or KAS backends use it.

## User-visible text

`scripts/rewrite_strings.py` runs at the end of `prepare.sh`. It rewrites only text people read: string literals (never comments, docstrings or identifiers), dashboard catalog values in all 12 languages, HTML pages, the installer and the install scripts.

| What | Becomes | Where it's defined |
|---|---|---|
| "Kiro Crew" / "KiroCrew" in prose | `PRODUCT_NAME` | `rebrand/strings-rules.json` |
| `kirocrew <command>` hints | `CLI_NAME <command>` | `rebrand/strings-rules.json` |
| Kiro Crew's GitHub repo, issues, discussions | `REPO_URL` (source and doc links go to `SOURCE_REPO_URL`) | `rebrand/strings-rules.json` |
| Kiro's Discord links in text | `REPO_URL/discussions` (DevTeam has no Discord) | `rebrand/strings-rules.json` |
| "Kiro" as the agent's name ("Things Kiro made for you") | `ASSISTANT_NAME` ("Things DevOps made for you"), in every language, starting from upstream's own translation | `rebrand/i18n-assistant-name.json` |
| "Kiro's Chromium" and Kiro-branded art names | Neutral wording ("built-in Chromium") | `rebrand/i18n-overrides.json`, per key and per language |
| `KIROCREW_HOME` / `KIROCREW_PORT` in CLI help and error text | `DEVTEAM_HOME` / `DEVTEAM_PORT` | `ENV_TEXT_*` in `rewrite_strings.py` |
| The feedback survey's "sent to the Kiro Crew team" | `PRODUCT_NAME`: answers now go to our endpoint | `recipient_keys` in `rebrand/i18n-keep.json` |
| The installer's "default agent requires Kiro CLI" page and the install scripts | A check for Claude Code. If it's found, the standard "installed" text; if not, a pointer to its setup guide. Only when `DEFAULT_AGENT=claude` | `rewrite_agent_prerequisite()` |
| Kiro's ghost in the app icon, installer, avatars, onboarding and loading screen | The striped "D" and DevTeam's agent character, in ScienceSoft colours | `scripts/brand_assets.py` → `overlay/`; inline drawings (loading screen, onboarding panel, welcome view): `rewrite_loading_character()`, `rewrite_kiro_ghost_component()` |
| Kiro purple: the default theme (`kiro`, labelled "ScienceSoft"), the default avatar tile, the share card, the loading screen's first colour | ScienceSoft blues: accent `#005EB8` (light) / `#1A8FFF` (dark), Crew mode in navy / teal | `rebrand/brand-colors.json`, `rewrite_brand_colors()` |
| The import panel headline "Bring your crew with you." | "Build your team with setup you already use.", in all 12 languages | `rebrand/i18n-overrides.json` |

Some text is deliberately left alone:

- **Kiro service text** (Kiro CLI, Kiro sign-in, Kiro credits, KAS). It's accurate for anyone who picks the Kiro backend.
- **Working service URLs** (the App catalog, Kiro sign-in endpoints, kiro-cli downloads, speech model downloads, the cloud bootstrap's git clone). Changing them would break features.
- **Links to specific upstream issues and PRs.**
- **Security and sandbox modules.** Their strings include patterns the checks match on, so rewriting them could weaken a rule.
- **Log messages and `src/kiro_crew/docs/`.** Planned for a later PR.
- **"Kiro Crew's official catalog"** in the install-receipt disclosure. Receipts are sent when you install from that catalog, which DevTeam still uses.

The overrides and the agent-name keys record the English text they were written against. If upstream rewords one of those strings, `prepare.sh` fails and names the key, so the translation can be reviewed rather than silently replacing the new text.

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

Versions are labelled `<upstream version>-<DEVTEAM_RELEASE>`, for example `0.12.2-1`. CI artifacts are named `DevTeam-<version>` (wheel) and `DevTeam-<version>-windows-x64` (installer). The installer file inside keeps electron-builder's name, `DevTeam Setup 0.12.2.exe`, because `latest.yml` points the updater at it. Bump `DEVTEAM_RELEASE` for each DevTeam-only release on the same upstream tag.

## Before the first public release

- [ ] Real update and download hosts in `devteam.conf`. The placeholders end in `.invalid` on purpose, so that auto-update fails closed instead of installing stock KiroCrew.
- [ ] Host the update feed. electron-updater reads `<UPDATE_FEED_BASE>/feed/<channel>/latest-*.yml`, and the Python updater uses the same two bases. See upstream `docs/build/release.md`.
- [x] Windows signing: self-signed `CN=ScienceSoft AI DevTeam`, expires 2027-11-15. See `certs/README.md`, including how to trust it on user machines.
- [ ] macOS signing and notarization (Apple Developer ID), wheel signing keys, and a release workflow that publishes to the update feed.
- [x] DevTeam artwork in `overlay/`, generated by `scripts/brand_assets.py`. A designer should still refine the drawings, especially the small icon sizes.
- [ ] `PACKAGE_MAINTAINER` in `devteam.conf`.
- [x] URL scheme: `devteam://` (`URL_SCHEME`).
- [ ] Our own telemetry and feedback collectors in `devteam.conf` (`TELEMETRY_ENDPOINT`, `FEEDBACK_ENDPOINT`). The `.invalid` placeholders send nothing anywhere. The feedback collector must accept the AWS Aperture form API shape that `dashboard/handlers/feedback.py` posts.
- [ ] About 13 upstream test files pin Kiro's update hosts and appId. `scripts/build.sh test` fails on those until they are patched or skipped.
- [ ] Apache-2.0: keep upstream `LICENSE`, `NOTICE` and `THIRD-PARTY-NOTICES` in what we ship. `patches/` documents our modifications. Don't ship Kiro or AWS names or logos as our branding.

## Ownership

The maintainer owns:

- reviewing and merging PRs;
- the translation review when an upstream sync fails on a reworded override or agent-name key;
- the manual check before a release that DevTeam and stock Kiro Crew run side by side on one machine (ports, data folders, deep links, CLI).

## CI secrets

| Secret | Used by | Purpose |
|---|---|---|
| `FORK_PUSH_TOKEN` | upstream-sync | Fine-grained PAT with contents write on `sciencesoft-ai/KiroCrew`. Syncs the fork's main and creates release tags there. Optional. |
| `WIN_CSC_LINK` | build-windows | Base64 of the Windows code-signing `.pfx` (see `certs/README.md`). |
| `WIN_CSC_KEY_PASSWORD` | build-windows | Password for that `.pfx`. |
| `SYNC_PR_TOKEN` | upstream-sync | PAT used to open sync PRs, so that `build.yml` runs on them. Optional. |
