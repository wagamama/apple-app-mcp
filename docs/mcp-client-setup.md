# MCP Client Setup

Use this guide after installing the packages:

```bash
pipx install mac-mail-mcp
pipx install mac-calendar-mcp
```

Build the local indexes before first use:

```bash
mac-mail-mcp index --verbose
mac-calendar-mcp index
```

## Codex CLI

Register both servers with Codex:

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

Remove and re-add a server if you need to change its command:

```bash
codex mcp remove mail
codex mcp add mail -- mac-mail-mcp --watch serve
```

## Claude Code

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

For a global Claude Code setup, put the same `mcpServers` object in
`~/.claude/mcp.json`.

## Permissions

Mail indexing reads local `.emlx` files. Grant Full Disk Access to the terminal
or MCP client that runs `mac-mail-mcp index`.

Calendar indexing uses Calendar automation. Approve the macOS automation prompt
the first time `mac-calendar-mcp index` talks to Calendar.app.

## Watch Mode

Use watch mode after the first index build. Mail watches local `.emlx` files for
changes; Calendar polls Calendar.app and refreshes the index periodically.

```bash
mac-mail-mcp --watch serve
mac-calendar-mcp --watch serve
```

Calendar defaults to a 300-second refresh interval. Override it when needed:

```bash
mac-calendar-mcp --watch --watch-interval 60 serve
```
