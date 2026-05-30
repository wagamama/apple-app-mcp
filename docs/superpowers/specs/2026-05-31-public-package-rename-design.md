# Public Package Rename Design

## Goal

Rename the public Python package distributions so other users can install this
workspace's Mail and Calendar MCP servers from PyPI with `pipx`.

## Package Names

Use the first available naming priority from the user request:

| Server | PyPI distribution | Preferred command | Compatibility command |
|--------|-------------------|-------------------|-----------------------|
| Mail | `mac-mail-mcp` | `mac-mail-mcp` | `apple-mail-mcp` |
| Calendar | `mac-calendar-mcp` | `mac-calendar-mcp` | `apple-calendar-mcp` |

PyPI JSON availability was checked on 2026-05-31. `mac-mail-mcp`,
`mac-calendar-mcp`, `macos-mail-mcp`, and `macos-calendar-mcp` all returned
404 at that time. The implementation should still fail safely if publishing
later discovers that a name was claimed meanwhile.

## Compatibility

Keep internal Python import packages unchanged:

- `apple_mail_mcp`
- `apple_calendar_mcp`

This avoids unnecessary source churn and preserves existing code, tests, and
user integrations that import modules directly.

Keep the old console script names as aliases. Existing MCP client configs that
run `apple-mail-mcp` or `apple-calendar-mcp` should continue to work after a
user installs the renamed distributions.

## Publishing

The release workflow must build and publish both distributions. A tag push
should produce artifacts for:

- `mac-mail-mcp`
- `mac-calendar-mcp`

Both packages should be suitable for:

```bash
pipx install mac-mail-mcp
pipx install mac-calendar-mcp
```

The workflow should keep the existing PyPI trusted publishing model. The user
or repository owner still needs to configure PyPI trusted publishers for the
new project names before the first release can publish successfully.

## Documentation

Docs and README examples should prefer the new `mac-*` package and command
names while mentioning the old `apple-*` command names as compatibility aliases
where useful.

Do not add personal or machine-specific values to docs. Use public repository
URLs or placeholders only.

## MCP Registry

The existing `server.json` manifest is Mail-specific and uses the old package
name. Rename it to a Mail-specific manifest and add a Calendar-specific
manifest so each server can be published independently. The release workflow
should publish both manifests if registry publishing is enabled.

## Verification

Before completion, verify:

- Metadata names and console scripts are updated.
- Lockfile reflects renamed workspace packages.
- Both distributions build locally.
- Built wheels expose the preferred commands and compatibility aliases.
- Tests pass.
- README and package docs show the new install commands.
- Release workflow builds both packages.

