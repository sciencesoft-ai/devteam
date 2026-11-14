# patches/

Our code changes to upstream, as a `git format-patch` series applied in file-name order by
`scripts/prepare.sh`. Don't edit these by hand. Use `scripts/patch-dev.sh` and
`scripts/export-patches.sh` (see the top-level README).

Each patch covers one concern, and its commit message says what it changes and why.

| Patch | Purpose |
|---|---|
| `0010-cli-add-devteam-console-script-alias.patch` | Installs a `devteam` command alongside `kirocrew` |
