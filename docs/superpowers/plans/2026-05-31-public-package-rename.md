# Public Package Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the public package distributions to `mac-mail-mcp` and
`mac-calendar-mcp`, keep old command aliases working, and prepare both packages
for PyPI publishing and `pipx install`.

**Architecture:** Keep Python import packages unchanged and change only public
distribution metadata, console scripts, manifests, docs, and release plumbing.
Use regression tests to prove the distribution names and command aliases stay
intentional.

**Tech Stack:** Python 3.11+, `uv` workspace, Hatchling builds, GitHub Actions
trusted publishing, MCP registry manifests.

---

## File Map

- `packages/apple-mail-mcp/pyproject.toml`: rename Mail distribution to
  `mac-mail-mcp`, add preferred `mac-mail-mcp` script, keep
  `apple-mail-mcp` alias, update package URLs.
- `packages/apple-calendar-mcp/pyproject.toml`: rename Calendar distribution to
  `mac-calendar-mcp`, add preferred `mac-calendar-mcp` script, keep
  `apple-calendar-mcp` alias, add package URLs.
- `packages/apple-mail-mcp/tests/test_import.py`: add or update metadata and
  console script assertions for Mail.
- `packages/apple-calendar-mcp/tests/test_import.py`: update metadata and
  console script assertions for Calendar.
- `pyproject.toml`: update workspace commands and pytest metadata assumptions if
  needed after package rename.
- `uv.lock`: refresh lockfile after package rename.
- `.github/workflows/release.yml`: build both renamed distributions, upload both
  package artifacts, publish both through the existing trusted publishing job.
- `server.json`: replace with package-specific manifests or convert to
  `server.mail.json`.
- `server.calendar.json`: add Calendar MCP registry manifest.
- `README.md`, `packages/apple-mail-mcp/README.md`,
  `packages/apple-calendar-mcp/README.md`: prefer new install and command names,
  mention old aliases where helpful.
- `AGENTS.md`: update release instructions to mention both packages and the new
  package names.

---

### Task 1: Rename Package Metadata and Console Scripts

**Files:**
- Modify: `packages/apple-mail-mcp/pyproject.toml`
- Modify: `packages/apple-calendar-mcp/pyproject.toml`
- Modify: `packages/apple-calendar-mcp/tests/test_import.py`
- Create or modify: `packages/apple-mail-mcp/tests/test_import.py`

- [ ] **Step 1: Write failing import metadata tests**

Create `packages/apple-mail-mcp/tests/test_import.py` if it does not exist:

```python
from __future__ import annotations

import importlib.metadata


def test_distribution_metadata_name() -> None:
    dist = importlib.metadata.distribution("mac-mail-mcp")

    assert dist.metadata["Name"] == "mac-mail-mcp"


def test_console_scripts_include_preferred_and_compat_aliases() -> None:
    scripts = {
        entry.name: entry.value
        for entry in importlib.metadata.entry_points(group="console_scripts")
        if entry.name in {"mac-mail-mcp", "apple-mail-mcp"}
    }

    assert scripts["mac-mail-mcp"] == "apple_mail_mcp:main"
    assert scripts["apple-mail-mcp"] == "apple_mail_mcp:main"
```

Update `packages/apple-calendar-mcp/tests/test_import.py` to assert:

```python
from __future__ import annotations

import importlib.metadata


def test_distribution_metadata_name() -> None:
    dist = importlib.metadata.distribution("mac-calendar-mcp")

    assert dist.metadata["Name"] == "mac-calendar-mcp"


def test_console_scripts_include_preferred_and_compat_aliases() -> None:
    scripts = {
        entry.name: entry.value
        for entry in importlib.metadata.entry_points(group="console_scripts")
        if entry.name in {"mac-calendar-mcp", "apple-calendar-mcp"}
    }

    assert scripts["mac-calendar-mcp"] == "apple_calendar_mcp:main"
    assert scripts["apple-calendar-mcp"] == "apple_calendar_mcp:main"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest packages/apple-mail-mcp/tests/test_import.py \
  packages/apple-calendar-mcp/tests/test_import.py -v
```

Expected before implementation: metadata lookup fails for `mac-mail-mcp` and
`mac-calendar-mcp`, or script assertions miss the preferred commands.

- [ ] **Step 3: Update package metadata**

In `packages/apple-mail-mcp/pyproject.toml`:

```toml
[project]
name = "mac-mail-mcp"
```

Add or keep keywords that include both old and new names:

```toml
keywords = [
    "anthropic",
    "apple-mail",
    "apple-mail-mcp",
    "mac-mail-mcp",
    "claude",
    "claude-code",
    "claude-desktop",
    "email",
    "emlx",
    "fts5",
    "full-text-search",
    "llm",
    "macos",
    "mcp",
    "model-context-protocol",
    "search",
]
```

Set URLs to this repository:

```toml
[project.urls]
Homepage = "https://github.com/wagamama/apple-app-mcp"
Documentation = "https://wagamama.github.io/apple-app-mcp/"
Repository = "https://github.com/wagamama/apple-app-mcp"
Issues = "https://github.com/wagamama/apple-app-mcp/issues"
Changelog = "https://github.com/wagamama/apple-app-mcp/blob/main/CHANGELOG.md"
```

Set scripts:

```toml
[project.scripts]
mac-mail-mcp = "apple_mail_mcp:main"
apple-mail-mcp = "apple_mail_mcp:main"
```

In `packages/apple-calendar-mcp/pyproject.toml`:

```toml
[project]
name = "mac-calendar-mcp"
```

Add keywords:

```toml
keywords = [
    "apple-calendar",
    "apple-calendar-mcp",
    "calendar",
    "jxa",
    "mac-calendar-mcp",
    "macos",
    "mcp",
    "model-context-protocol",
    "search",
]
```

Add URLs:

```toml
[project.urls]
Homepage = "https://github.com/wagamama/apple-app-mcp"
Documentation = "https://wagamama.github.io/apple-app-mcp/"
Repository = "https://github.com/wagamama/apple-app-mcp"
Issues = "https://github.com/wagamama/apple-app-mcp/issues"
Changelog = "https://github.com/wagamama/apple-app-mcp/blob/main/CHANGELOG.md"
```

Set scripts:

```toml
[project.scripts]
mac-calendar-mcp = "apple_calendar_mcp:main"
apple-calendar-mcp = "apple_calendar_mcp:main"
```

- [ ] **Step 4: Refresh lockfile**

Run:

```bash
uv lock
```

Expected: `uv.lock` records workspace packages as `mac-mail-mcp` and
`mac-calendar-mcp`.

- [ ] **Step 5: Run metadata tests**

Run:

```bash
uv run pytest packages/apple-mail-mcp/tests/test_import.py \
  packages/apple-calendar-mcp/tests/test_import.py -v
```

Expected: tests pass.

- [ ] **Step 6: Commit Task 1**

```bash
git add packages/apple-mail-mcp/pyproject.toml \
  packages/apple-calendar-mcp/pyproject.toml \
  packages/apple-mail-mcp/tests/test_import.py \
  packages/apple-calendar-mcp/tests/test_import.py \
  uv.lock
git commit -m "Rename public package distributions"
```

---

### Task 2: Update Release Workflow for Both Packages

**Files:**
- Modify: `.github/workflows/release.yml`

- [ ] **Step 1: Update build matrix**

Replace the single package build job with a matrix:

```yaml
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package:
          - mac-mail-mcp
          - mac-calendar-mcp
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
      - uses: astral-sh/setup-uv@0c5e2b8115b80b4c7c5ddf6ffdd634974642d182 # v5.4.1
      - run: uv build --package ${{ matrix.package }}
      - uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2
        with:
          name: dist-${{ matrix.package }}
          path: dist/
```

- [ ] **Step 2: Download all package artifacts before publishing**

Update the publish job:

```yaml
  publish:
    needs: build
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093 # v4.3.0
        with:
          pattern: dist-*
          path: dist/
          merge-multiple: true
      - uses: pypa/gh-action-pypi-publish@ec4db0b4ddc65acdf4bff5fa45ac92d78b56bdf0 # v1.9.0
```

- [ ] **Step 3: Update release title**

Use a repository-level title:

```yaml
      - name: Create GitHub Release
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh release create "$GITHUB_REF_NAME" \
            --title "$GITHUB_REF_NAME — Apple App MCP" \
            --generate-notes \
            --notes-start-tag "$(git tag --sort=-creatordate | sed -n '2p')" \
            || gh release create "$GITHUB_REF_NAME" \
              --title "$GITHUB_REF_NAME — Apple App MCP" \
              --generate-notes
```

- [ ] **Step 4: Run workflow syntax-oriented checks**

Run:

```bash
rg -n "uv build --package apple-mail-mcp|name: dist$|Apple Mail MCP" \
  .github/workflows/release.yml
```

Expected: no matches.

Run:

```bash
rg -n "mac-mail-mcp|mac-calendar-mcp|pattern: dist-\\*" \
  .github/workflows/release.yml
```

Expected: matches for both package names and artifact download pattern.

- [ ] **Step 5: Commit Task 2**

```bash
git add .github/workflows/release.yml
git commit -m "Publish both renamed packages"
```

---

### Task 3: Split MCP Registry Manifests

**Files:**
- Move: `server.json` to `server.mail.json`
- Create: `server.calendar.json`
- Modify: `.github/workflows/release.yml`
- Modify: `AGENTS.md`

- [ ] **Step 1: Rename Mail manifest**

Move `server.json` to `server.mail.json`.

Update its fields:

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-07-09/server.schema.json",
  "name": "io.github.wagamama/mac-mail-mcp",
  "description": "Apple Mail MCP server with full-coverage FTS5 body search. Reliable on large mailboxes where AppleScript-based servers timeout.",
  "status": "active",
  "repository": {
    "url": "https://github.com/wagamama/apple-app-mcp",
    "source": "github"
  },
  "version": "0.4.0",
  "packages": [
    {
      "registryType": "pypi",
      "identifier": "mac-mail-mcp",
      "version": "0.4.0",
      "runtimeHint": "uvx"
    }
  ]
}
```

- [ ] **Step 2: Add Calendar manifest**

Create `server.calendar.json`:

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-07-09/server.schema.json",
  "name": "io.github.wagamama/mac-calendar-mcp",
  "description": "Read-only Apple Calendar MCP server with indexed archive search.",
  "status": "active",
  "repository": {
    "url": "https://github.com/wagamama/apple-app-mcp",
    "source": "github"
  },
  "version": "0.1.0",
  "packages": [
    {
      "registryType": "pypi",
      "identifier": "mac-calendar-mcp",
      "version": "0.1.0",
      "runtimeHint": "uvx"
    }
  ]
}
```

- [ ] **Step 3: Publish both manifests**

In `.github/workflows/release.yml`, replace the single publish command with:

```yaml
      - name: Publish Mail to MCP Registry
        run: ./mcp-publisher publish server.mail.json
      - name: Publish Calendar to MCP Registry
        run: ./mcp-publisher publish server.calendar.json
```

- [ ] **Step 4: Update release instructions**

In `AGENTS.md`, update release checklist references from `server.json` to
`server.mail.json` and `server.calendar.json`, and mention both package names.

- [ ] **Step 5: Validate manifests are JSON**

Run:

```bash
python -m json.tool server.mail.json >/dev/null
python -m json.tool server.calendar.json >/dev/null
```

Expected: both commands exit 0.

- [ ] **Step 6: Commit Task 3**

```bash
git add server.mail.json server.calendar.json .github/workflows/release.yml \
  AGENTS.md
git add -u server.json
git commit -m "Add package-specific MCP manifests"
```

---

### Task 4: Update Documentation for Public Install Names

**Files:**
- Modify: `README.md`
- Modify: `packages/apple-mail-mcp/README.md`
- Modify: `packages/apple-calendar-mcp/README.md`
- Modify: `AGENTS.md`
- Optional modify: `mkdocs.yml`

- [ ] **Step 1: Update root README quick start**

Use:

```bash
pipx install mac-mail-mcp
pipx install mac-calendar-mcp
```

Use preferred commands:

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

Mention: `apple-mail-mcp` and `apple-calendar-mcp` remain command aliases for
existing configs.

- [ ] **Step 2: Update Mail README**

Change the install command to:

```bash
pipx install mac-mail-mcp
```

Change MCP and CLI examples to `mac-mail-mcp`. Add one compatibility sentence:

```markdown
`apple-mail-mcp` remains available as a compatibility command alias.
```

Update the MCP name comment:

```html
<!-- mcp-name: io.github.wagamama/mac-mail-mcp -->
```

Update badge and docs links to this repository where practical.

- [ ] **Step 3: Update Calendar README**

Change the install command to:

```bash
pipx install mac-calendar-mcp
```

Change MCP and CLI examples to `mac-calendar-mcp`. Add one compatibility
sentence:

```markdown
`apple-calendar-mcp` remains available as a compatibility command alias.
```

Update the MCP name comment:

```html
<!-- mcp-name: io.github.wagamama/mac-calendar-mcp -->
```

- [ ] **Step 4: Search for stale primary install docs**

Run:

```bash
rg -n "pipx install apple-mail-mcp|pipx install apple-calendar-mcp|command\": \"apple-mail-mcp|command\": \"apple-calendar-mcp" \
  README.md packages docs AGENTS.md
```

Expected: no matches except deliberate compatibility notes if the text makes
that clear.

- [ ] **Step 5: Commit Task 4**

```bash
git add README.md packages/apple-mail-mcp/README.md \
  packages/apple-calendar-mcp/README.md AGENTS.md mkdocs.yml
git commit -m "Document renamed public packages"
```

---

### Task 5: Verify Build, Wheel Contents, and Local Installability

**Files:**
- No source changes expected unless verification finds a defect.

- [ ] **Step 1: Run formatting and lint checks**

Run:

```bash
uv run ruff format --check packages/apple-mail-mcp/src packages/apple-calendar-mcp/src
uv run ruff check packages/apple-mail-mcp/src packages/apple-calendar-mcp/src
```

Expected: both pass.

- [ ] **Step 2: Run test suite**

Run:

```bash
uv run pytest
```

Expected: all tests pass.

- [ ] **Step 3: Build both renamed packages**

Run:

```bash
uv build --package mac-mail-mcp
uv build --package mac-calendar-mcp
```

Expected artifacts include:

- `dist/mac_mail_mcp-0.4.0-py3-none-any.whl`
- `dist/mac_calendar_mcp-0.1.0-py3-none-any.whl`

- [ ] **Step 4: Inspect wheel entry points**

Run:

```bash
python - <<'PY'
from pathlib import Path
from zipfile import ZipFile

for wheel in sorted(Path("dist").glob("mac_*_mcp-*.whl")):
    with ZipFile(wheel) as zf:
        entry = next(
            name for name in zf.namelist()
            if name.endswith(".dist-info/entry_points.txt")
        )
        text = zf.read(entry).decode()
    print(f"## {wheel.name}")
    print(text)
PY
```

Expected output includes:

```ini
mac-mail-mcp = apple_mail_mcp:main
apple-mail-mcp = apple_mail_mcp:main
mac-calendar-mcp = apple_calendar_mcp:main
apple-calendar-mcp = apple_calendar_mcp:main
```

- [ ] **Step 5: Test pipx-style local installs if pipx is available**

Run:

```bash
command -v pipx
```

If it exits 0, run:

```bash
pipx install --force dist/mac_mail_mcp-0.4.0-py3-none-any.whl
pipx runpip mac-mail-mcp list
pipx uninstall mac-mail-mcp
pipx install --force dist/mac_calendar_mcp-0.1.0-py3-none-any.whl
pipx runpip mac-calendar-mcp list
pipx uninstall mac-calendar-mcp
```

Expected: installs and uninstalls succeed. If `pipx` is unavailable, record that
the wheel build and entry point inspection covered local installability.

- [ ] **Step 6: Verify release workflow references renamed packages**

Run:

```bash
rg -n "apple-mail-mcp|apple-calendar-mcp" .github/workflows/release.yml
```

Expected: no matches unless comments explicitly refer to compatibility.

- [ ] **Step 7: Final status check**

Run:

```bash
git status --short --branch
```

Expected: clean branch after the verification commits.

