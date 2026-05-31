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
mac-calendar-mcp index
```

### Codex CLI

Register one or both servers:

```bash
codex mcp add mail -- mac-mail-mcp --watch serve
codex mcp add calendar -- mac-calendar-mcp --watch serve
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
      "args": ["--watch", "serve"]
    },
    "calendar": {
      "command": "mac-calendar-mcp",
      "args": ["--watch", "serve"]
    }
  }
}
```

Watch mode keeps the indexes current while the MCP servers are running. Mail
uses file watching; Calendar polls Calendar.app periodically.

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

## License

GPL-3.0-or-later
