# Apple App MCP - Agent Entry Point

Start here for shared repository instructions. This file is derived from the
former project instructions, but it is the agent-facing entry point going
forward.

This repository currently contains the Apple Mail MCP server and is expected to
host additional Apple app MCP servers, such as Apple Calendar MCP, over time.
Keep shared workflow here and put app-specific architecture in the matching
domain file.

## Project Areas

- Read `MAIL.md` before changing Apple Mail MCP behavior, tests, docs, CLI,
  indexing, JXA, benchmarks, or packaging.
- Read `CALENDAR.md` before changing Apple Calendar MCP behavior, tests, docs,
  CLI, indexing, JXA, benchmarks, or packaging.
- Keep domain-specific details out of this file unless they apply across all
  Apple app MCP servers in the repository.

## Documentation Privacy

- Do not include personal or machine-specific data in README files,
  documentation, install commands, examples, or generated project files unless
  the user explicitly requests it.
- This includes local usernames, absolute home-directory paths, private
  repository aliases, hostnames, email addresses, tokens, account IDs, and other
  identifying local details.
- Use placeholders or portable commands such as `$(pwd)` instead.

## Coding Standards

- Python 3.11+.
- Use type hints for new and changed Python code.
- Keep lines at 80 characters where practical.
- Format with `uv run ruff format src/`.
- Lint with `uv run ruff check src/`.
- Prefer existing module boundaries and helper APIs over new abstractions.

## Testing

```bash
uv run pytest
uv run pytest -v
uv run pytest tests/test_search.py
```

## Git Workflow and CI/CD

### Branching: Trunk-Based

- Commit directly to `main` for small changes such as bug fixes,
  housekeeping, and single-file edits.
- Use short-lived feature branches for multi-commit work.
- Merge back to `main` via fast-forward or squash merge.
- Do not create long-lived `dev` branches. Tags mark releases.

### CI Workflows

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `lint.yml` | Push/PR to `main` | `ruff check src/` + `ruff format --check src/` |
| `release.yml` | Tag push (`v*`) | `uv build` -> PyPI publish -> GitHub Release |

### Releasing

A single tag push triggers the full pipeline: build, PyPI publish, and GitHub
Release.

Pre-release checklist:

1. `pyproject.toml` -> `version = "0.X.Y"`
2. `server.json` -> `"version"` and `packages[0].version`
3. Run lint, format, and tests.
4. Commit, tag, and push:

```bash
git add pyproject.toml server.json
git commit -m "Bump version to 0.X.Y"
git tag v0.X.Y
git push origin main v0.X.Y
```

PyPI is configured to trust `release.yml` in the `pypi` GitHub environment via
OIDC trusted publishing. If publishing breaks, check the PyPI trusted publisher
settings and the GitHub `pypi` environment.

### Pre-Push Checklist

```bash
uv run ruff check src/
uv run ruff format --check src/
uv run pytest
```

## Completion, Review, and Commit Workflow

- When a task is complete, verify the result with the relevant checks, tests,
  inspections, or review steps before calling the work done.
- If review feedback exists, address it first. Continue to the commit decision
  only after the review result is positive.
- Before the final change summary and commit decision for non-trivial work,
  perform a cross-reference review.
- Prefer using Codex with an available review skill or review subagent when one
  exists, such as `superpowers:requesting-code-review` or a Codex subagent.
- If no review skill or subagent is available, perform the cross-reference
  review locally.
- Cross-reference the user's request, the implementation diff, verification
  results, and applicable project instructions such as `AGENTS.md`.
- Address any review findings before reporting a positive review result.
- After a positive review result, summarize all changes made in the task so the
  user can make an informed version-control decision.
- After the change summary, ask the user how to proceed with version control and
  offer exactly these options:
  1. `Do not commit` - Leave all changes uncommitted.
  2. `Commit only` - Create one or more commits, grouped by task category when
     appropriate, but do not push.
  3. `Commit and push` - Create one or more commits, grouped by task category
     when appropriate, then push to the configured remote.
- Treat the user's choice as applying only to the task just completed. Do not
  reuse or carry forward a previous commit decision for later tasks.
- When committing, split commits by task category if the work naturally spans
  multiple categories. Keep each commit focused and independently
  understandable.
- Do not mix unrelated changes in the same commit.
- Use clear commit messages that describe the intent of each task category.
- Never push unless the user explicitly chooses `Commit and push`.
- If no remote or upstream branch is configured, explain the situation and ask
  before changing git remote or branch configuration.
