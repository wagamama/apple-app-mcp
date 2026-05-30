# Apple App MCP

Workspace for MCP servers that expose local Apple app data to assistants.

## Packages

| Package | Status | Purpose |
|---------|--------|---------|
| [`mac-mail-mcp`](packages/apple-mail-mcp/) | Beta | Apple Mail MCP server with disk-first reads and full-coverage FTS5 body search. |
| [`mac-calendar-mcp`](packages/apple-calendar-mcp/) | Alpha | Read-only Apple Calendar MCP server with indexed archive search. |

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

The older `apple-mail-mcp` and `apple-calendar-mcp` commands remain available
as compatibility aliases.

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
uv run ruff check packages/apple-mail-mcp/src packages/apple-calendar-mcp/src
uv run pytest

# Individual packages
uv run --package mac-mail-mcp pytest packages/apple-mail-mcp/tests
uv run --package mac-calendar-mcp pytest packages/apple-calendar-mcp/tests
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
- Calendar implementation plan: [`docs/superpowers/plans/2026-05-30-apple-calendar-mcp-implementation.md`](docs/superpowers/plans/2026-05-30-apple-calendar-mcp-implementation.md)

## License

GPL-3.0-or-later
