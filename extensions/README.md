# extensions/

DevTeam additions that use KiroCrew's own extension points instead of code changes:

- `skills/`: markdown skills
- `mcp/`: MCP server definitions
- `hooks/`: hook scripts
- `apps/`: Apps built with App Kit
- `policy/`: security policy JSON, for capability ceilings such as disabling telemetry

Prefer this folder to `patches/` whenever an extension point can do the job.
Shipping these is still to be decided. There are two options:

- Bundle them with an overlay rule into the default config locations.
- Publish them separately for users to install with `kirocrew`/`devteam` commands.
