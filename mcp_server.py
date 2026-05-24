"""MCP tools for reading and writing notes in the GitHub repo."""

import json
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
import github_api

mcp = FastMCP(
    "notes",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@mcp.tool()
async def list_notes(folder: str = "") -> str:
    """
    List all markdown notes in the repo.
    Pass a folder name to list only notes inside it (e.g. folder="work").
    Returns file paths and sizes.
    """
    files = await github_api.list_notes(folder)
    if not files:
        return json.dumps({"notes": [], "count": 0})
    return json.dumps({"notes": files, "count": len(files)})


@mcp.tool()
async def read_note(path: str) -> str:
    """
    Read the full content of a note by its path (e.g. "ideas.md" or "work/standup.md").
    """
    content, sha = await github_api.read_note(path)
    return json.dumps({"path": path, "content": content, "sha": sha})


@mcp.tool()
async def write_note(path: str, content: str, commit_message: str = "") -> str:
    """
    Create or update a note. Creates the file if it doesn't exist.

    path: file path like "ideas.md" or "work/standup.md" — must end in .md
    content: the full markdown content to write
    commit_message: optional short description of what changed
    """
    if not path.endswith(".md"):
        path = path + ".md"

    message = commit_message or f"Update {path}"
    commit_sha = await github_api.write_note(path, content, message)
    return json.dumps({"ok": True, "path": path, "commit": commit_sha[:8]})


@mcp.tool()
async def search_notes(query: str) -> str:
    """
    Search all notes for a keyword or phrase (case-insensitive).
    Returns matching file paths and up to 3 snippet lines per file.
    """
    results = await github_api.search_notes(query)
    if not results:
        return json.dumps({"results": [], "message": f"No notes found containing '{query}'"})
    return json.dumps({"results": results, "count": len(results)})
