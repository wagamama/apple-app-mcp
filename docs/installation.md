# Installation

## With pipx (Recommended)

```bash
pipx install mac-mail-mcp
pipx install mac-calendar-mcp
```

A persistent install is recommended because each search index is built once and
reused across sessions. Ephemeral runners like `pipx run` or `uvx` work but
won't benefit from cached indexes.

## With uv

```bash
uv tool install mac-mail-mcp
uv tool install mac-calendar-mcp
```

## With pip

```bash
pip install mac-mail-mcp
pip install mac-calendar-mcp
```

## From Source

For development or to run the latest unreleased version:

```bash
git clone https://github.com/wagamama/apple-app-mcp
cd apple-app-mcp
uv sync
```

Run with:

```bash
uv run --package mac-mail-mcp mac-mail-mcp
uv run --package mac-calendar-mcp mac-calendar-mcp
```

## Prerelease Versions

To install a prerelease (e.g., `v0.2.0a1`):

```bash
pipx install mac-mail-mcp --pip-args='--pre'
pipx install mac-calendar-mcp --pip-args='--pre'
# or
uv tool install mac-mail-mcp --prerelease=allow
uv tool install mac-calendar-mcp --prerelease=allow
```

## Verify Installation

```bash
mac-mail-mcp status
mac-calendar-mcp status
```

This prints the index status. If you see output (even "no index found"), the installation is working.

## Requirements

| Requirement | Version |
|-------------|---------|
| **macOS** | Ventura or later |
| **Python** | 3.11+ |
| **Apple Mail** | Configured with ≥1 account |

!!! note
    Mac Mail MCP is macOS-only. It requires Apple Mail and the `osascript` runtime for JXA execution.
