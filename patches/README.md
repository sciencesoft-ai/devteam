# patches/

Our code changes to upstream, as a `git format-patch` series applied in file-name order by
`scripts/prepare.sh`. Don't edit these by hand. Use `scripts/patch-dev.sh` and
`scripts/export-patches.sh` (see the top-level README).

Each patch covers one concern, and its commit message says what it changes and why.

| Patch | Purpose |
|---|---|
| `0010-distribution-read-identity-values-…` | Upstream reads its identity values (data home, port, CLI name, default agent, scheme, service names) from three modules that `scripts/distribution.py` regenerates |
| `0020-distribution-map-a-downstream-env-prefix-…` | `DEVTEAM_HOME` / `DEVTEAM_PORT` replace a `KIROCREW_HOME` / `KIROCREW_PORT` exported for another install |
| `0030-distribution-read-telemetry-feedback-and-community-…` | Telemetry beacon, install receipts, feedback survey and the nav rail's community link come from the distribution modules |
| `0040-test-i18n-read-the-product-name-from-the-distributio…` | The dashboard i18n tests read the product name from the distribution module instead of pinning "Kiro Crew" |
