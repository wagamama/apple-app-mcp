# Public Package Rename Implementation Plan

> **For agentic workers:** This plan records the current public package rename
> direction. The old `apple-*` public commands are intentionally not kept as
> aliases.

## Goal

Rename the public package distributions and user-facing commands to:

- `mac-mail-mcp`
- `mac-calendar-mcp`

Keep internal Python import packages unchanged:

- `apple_mail_mcp`
- `apple_calendar_mcp`

## Scope

- Move package directories to `packages/mac-mail-mcp/` and
  `packages/mac-calendar-mcp/`.
- Update workspace metadata, CI paths, lockfile source paths, package READMEs,
  documentation, and MCP registry manifests.
- Remove the old hyphenated `apple-*` console script aliases.
- Add MCP client setup documentation for Codex CLI and Claude Code.
- Preserve third-party benchmark repository names exactly as upstream names.

## Expected Package Metadata

`packages/mac-mail-mcp/pyproject.toml`:

```toml
[project]
name = "mac-mail-mcp"

[project.scripts]
mac-mail-mcp = "apple_mail_mcp:main"
```

`packages/mac-calendar-mcp/pyproject.toml`:

```toml
[project]
name = "mac-calendar-mcp"

[project.scripts]
mac-calendar-mcp = "apple_calendar_mcp:main"
```

## Documentation Updates

- `README.md`: repository overview uses `mac-*` package names.
- `docs/installation.md`: install and verify both packages with `pipx`.
- `docs/mcp-client-setup.md`: Codex CLI and Claude Code examples for both
  MCP servers.
- `MAIL.md` and `CALENDAR.md`: domain docs use the new package paths and
  public commands.
- `AGENTS.md`: project area references point to the new package names while
  continuing to route domain details through `MAIL.md` and `CALENDAR.md`.

## Verification

Before completion, verify:

```bash
uv lock --check
uv run ruff format --check packages/mac-mail-mcp/src packages/mac-calendar-mcp/src
uv run ruff check packages/mac-mail-mcp/src packages/mac-calendar-mcp/src
uv run pytest
uv build --package mac-mail-mcp
uv build --package mac-calendar-mcp
uv run --group docs zensical build --clean
git diff --check
```

Inspect built wheel entry points and confirm only these console scripts exist:

```ini
mac-mail-mcp = apple_mail_mcp:main
mac-calendar-mcp = apple_calendar_mcp:main
```

Search maintained files for stale aliases:

```bash
rg -n "apple-(mail|calendar)-mcp" \
  AGENTS.md CALENDAR.md MAIL.md README.md CONTRIBUTING.md mkdocs.yml docs \
  packages/mac-mail-mcp packages/mac-calendar-mcp pyproject.toml \
  server.mail.json server.calendar.json .github uv.lock
```

Any remaining `apple_mail_mcp` or `apple_calendar_mcp` identifiers are Python
module names, not public package or command aliases.
