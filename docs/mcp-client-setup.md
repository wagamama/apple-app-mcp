# MCP Client Setup

Use this guide after installing the packages:

```bash
pipx install mac-mail-mcp
pipx install mac-calendar-mcp
```

Build the local indexes before first use:

```bash
mac-mail-mcp index --verbose
mac-calendar-mcp authorize
mac-calendar-mcp index
```

## Codex CLI

Register both servers with Codex:

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

Remove and re-add a server if you need to change its command:

```bash
codex mcp remove mail
codex mcp add mail -- mac-mail-mcp serve --watch
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

Calendar indexing uses a helper app with a stable macOS privacy identity. Run
`mac-calendar-mcp authorize` interactively and approve Full Calendar Access
before the first index build. The authorization also applies when launchd or
another background process runs the Calendar MCP later because EventKit runs
inside that signed helper app identity.

## Watch Mode

Use watch mode after the first index build. Mail watches local `.emlx` files for
changes; Calendar polls Calendar.app and refreshes the index periodically.

```bash
mac-mail-mcp serve --watch
mac-calendar-mcp serve --watch
```

Calendar defaults to a 3600-second refresh interval. Override it when needed:

```bash
mac-calendar-mcp serve --watch --watch-interval 7200
```
