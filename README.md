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

Add one or both servers to your MCP client:

```json
{
  "mcpServers": {
    "mail": {
      "command": "mac-mail-mcp"
    },
    "calendar": {
      "command": "mac-calendar-mcp"
    }
  }
}
```

Build local indexes for fast search:

```bash
mac-mail-mcp index --verbose
mac-calendar-mcp index
```

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

## License

GPL-3.0-or-later
