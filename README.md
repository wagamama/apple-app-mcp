# Apple App MCP

Workspace for MCP servers that expose local Apple app data to assistants.

## Packages

| Package | Status | Purpose |
|---------|--------|---------|
| [`mac-mail-mcp`](packages/mac-mail-mcp/) | Beta | Mac Mail MCP server with disk-first reads and full-coverage FTS5 body search. |
| [`mac-calendar-mcp`](packages/mac-calendar-mcp/) | Alpha | Read-only Mac Calendar MCP server with indexed archive search. |

## Quick Start

Install the package you want:

```bash
pipx install mac-mail-mcp
pipx install mac-calendar-mcp
```

Build local indexes for fast search:

```bash
mac-mail-mcp index --verbose
mac-calendar-mcp authorize
mac-calendar-mcp index
```

Calendar authorization installs a small helper app with a stable macOS privacy
identity. Approve its Full Calendar Access prompt once so terminal, MCP, and
scheduled launchd rebuilds can use EventKit consistently. EventKit runs inside
that signed app identity; the Calendar MCP does not execute the helper's script
through an anonymous `osascript` process.

Generate optional config files:

```bash
mac-mail-mcp init
mac-calendar-mcp init
```

Index scope is configured separately from tool defaults. Use `[index]`
settings such as Mail `accounts` or Calendar `calendars` to control what is
stored locally; use `[defaults]` settings to control what MCP tools use when
the caller omits a scope.

### Codex CLI

Register one or both servers:

```bash
codex mcp add mail -- mac-mail-mcp serve --watch
codex mcp add calendar -- mac-calendar-mcp serve --watch
```

Confirm the registrations:

```bash
codex mcp list
codex mcp get mail
codex mcp get calendar
```

### Claude Code

Create or edit `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "mail": {
      "command": "mac-mail-mcp",
      "args": ["serve", "--watch"]
    },
    "calendar": {
      "command": "mac-calendar-mcp",
      "args": ["serve", "--watch"]
    }
  }
}
```

Watch mode keeps the indexes current while the MCP servers are running. Mail
uses file watching; Calendar performs a startup sync and then refreshes when
Calendar's local SQLite database files change.

For global Claude Code configuration, put the same `mcpServers` object in
`~/.claude/mcp.json`.

## Development

This repository is organized as a `uv` workspace. Each MCP server lives under
`packages/` with its own package metadata, source, tests, and README.

```bash
git clone https://github.com/wagamama/apple-app-mcp
cd apple-app-mcp
uv sync

# All packages
uv run ruff check packages/mac-mail-mcp/src packages/mac-calendar-mcp/src
uv run pytest

# Individual packages
uv run --package mac-mail-mcp pytest packages/mac-mail-mcp/tests
uv run --package mac-calendar-mcp pytest packages/mac-calendar-mcp/tests
```

Build distributions:

```bash
uv build --package mac-mail-mcp
uv build --package mac-calendar-mcp
```

## Documentation

- Shared agent instructions: [`AGENTS.md`](AGENTS.md)
- Mail domain notes: [`MAIL.md`](MAIL.md)
- Calendar domain notes: [`CALENDAR.md`](CALENDAR.md)
- MCP client setup guide: [`docs/mcp-client-setup.md`](docs/mcp-client-setup.md)
- Calendar implementation plan: [`docs/superpowers/plans/2026-05-30-mac-calendar-mcp-implementation.md`](docs/superpowers/plans/2026-05-30-mac-calendar-mcp-implementation.md)

Docs are deployed with GitHub Pages from `.github/workflows/docs.yml`. The
repository must have Pages configured once in **Settings -> Pages -> Build and
deployment -> Source: GitHub Actions**. The workflow deploys the built artifact;
it does not try to create or enable the Pages site because GitHub rejects that
operation from the default workflow token in some repositories.

## Acknowledgements

This codebase is derived from
[`imdinu/apple-mail-mcp`](https://github.com/imdinu/apple-mail-mcp). Credit and
thanks go to the original authors and contributors for the Apple Mail MCP
foundation this repository builds on.

## License

GPL-3.0-or-later
