# Apple App MCP

Workspace for MCP servers that expose local Apple app data to assistants.

## Packages

| Package | Status | Purpose |
|---------|--------|---------|
| [`apple-mail-mcp`](packages/apple-mail-mcp/) | Beta | Apple Mail MCP server with disk-first reads and full-coverage FTS5 body search. |
| [`apple-calendar-mcp`](packages/apple-calendar-mcp/) | Alpha | Read-only Apple Calendar MCP server with indexed archive search. |

## Quick Start

Install the package you want:

```bash
pipx install apple-mail-mcp
pipx install apple-calendar-mcp
```

Add one or both servers to your MCP client:

```json
{
  "mcpServers": {
    "mail": {
      "command": "apple-mail-mcp"
    },
    "calendar": {
      "command": "apple-calendar-mcp"
    }
  }
}
```

Build local indexes for fast search:

```bash
apple-mail-mcp index --verbose
apple-calendar-mcp index
```

## Development

This repository is organized as a `uv` workspace. Each MCP server lives under
`packages/` with its own package metadata, source, tests, and README.

```bash
git clone https://github.com/wagamama/apple-app-mcp
cd apple-app-mcp
uv sync

# All packages
uv run ruff check packages/apple-mail-mcp/src packages/apple-calendar-mcp/src
uv run pytest

# Individual packages
uv run --package apple-mail-mcp pytest packages/apple-mail-mcp/tests
uv run --package apple-calendar-mcp pytest packages/apple-calendar-mcp/tests
```

Build distributions:

```bash
uv build --package apple-mail-mcp
uv build --package apple-calendar-mcp
```

## Documentation

- Shared agent instructions: [`AGENTS.md`](AGENTS.md)
- Mail domain notes: [`MAIL.md`](MAIL.md)
- Calendar domain notes: [`CALENDAR.md`](CALENDAR.md)
- Calendar implementation plan: [`docs/superpowers/plans/2026-05-30-apple-calendar-mcp-implementation.md`](docs/superpowers/plans/2026-05-30-apple-calendar-mcp-implementation.md)

## License

GPL-3.0-or-later
