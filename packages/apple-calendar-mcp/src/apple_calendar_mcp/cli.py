"""Command-line interface for apple-calendar-mcp."""

import cyclopts

app = cyclopts.App(
    name="apple-calendar-mcp",
    help="Read-only MCP server for Apple Calendar with indexed search.",
)


def main() -> None:
    """Run the Apple Calendar MCP CLI."""
    app()
