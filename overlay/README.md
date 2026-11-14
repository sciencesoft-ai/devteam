# overlay/

Files here are copied over the upstream tree at the same relative path, after
patches are applied. Use this for whole-file replacements: icons, banner,
default configs. (This README itself is not copied.)

Branding files to provide (upstream paths at v0.12.2 — re-check after syncs):

| Upstream path | What |
|---|---|
| `website/electron/icon.png`, `icon-nightly.png` | desktop app / Windows installer icon |
| `website/electron/build/icons/`, `build/icons-nightly/` | per-size app icons (macOS / Linux) |
| `website/electron/trayTemplate.png`, `trayTemplate@2x.png` | menu-bar / tray icon |
| `assets/banner.svg` | README / docs banner |

Example: a DevTeam icon goes to `overlay/website/electron/icon.png`.
