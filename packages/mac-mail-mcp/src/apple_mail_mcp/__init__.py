"""Mac Mail MCP — full-coverage FTS5 body search for Apple Mail.

Features:
- Disk-first email reading (~3ms via .emlx parsing, no JXA needed)
- Full-text body search via FTS5 index (~2ms with BM25 ranking)
- Reliable on large mailboxes (tested at ~72K messages) where
  AppleScript-based servers time out

Usage:
    mac-mail-mcp            # Run MCP server (default)
    mac-mail-mcp serve -r   # Run in read-only mode
    mac-mail-mcp serve --watch # Run with real-time index updates
    mac-mail-mcp init       # Write a config.toml template
    mac-mail-mcp index      # Build search index from disk
    mac-mail-mcp status     # Show index statistics
    mac-mail-mcp rebuild    # Force rebuild index
"""

from .cli import main
from .server import mcp

__all__ = ["main", "mcp"]
