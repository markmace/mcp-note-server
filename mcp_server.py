"""MCP tools for reading and writing notes in the GitHub repo."""

import json

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

import github_api

mcp = FastMCP(
    "Claude Meets Obsidian",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


def _ensure_md(path: str) -> str:
    return path if path.endswith(".md") else path + ".md"


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
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


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def read_note(path: str) -> str:
    """
    Read the full content of a note by its path (e.g. "ideas.md" or "work/standup.md").
    Always call this before editing a note so you can see exactly what's there.
    """
    content, sha = await github_api.read_note(path)
    return json.dumps({"path": path, "content": content, "sha": sha})


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def search_notes(query: str) -> str:
    """
    Search all notes for a keyword or phrase (case-insensitive).
    Returns matching file paths and up to 3 snippet lines per file.
    """
    results = await github_api.search_notes(query)
    if not results:
        return json.dumps({"results": [], "message": f"No notes found containing '{query}'"})
    return json.dumps({"results": results, "count": len(results)})


@mcp.tool()
async def edit_note(
    path: str,
    old_text: str,
    new_text: str,
    replace_all: bool = False,
    commit_message: str = "",
) -> str:
    """
    Surgically edit a note by replacing exact text. This is the PREFERRED way to modify
    existing notes — it only changes what you specify and leaves everything else alone.

    Always read_note() first to see the exact text you want to change.

    Rules:
    - `old_text` must appear EXACTLY in the file (including whitespace, punctuation, newlines)
    - `old_text` must be UNIQUE in the file. If it appears multiple times, either:
        1. Extend `old_text` with surrounding context to make it unique, OR
        2. Set replace_all=True to change every occurrence
    - This will error rather than silently do the wrong thing
    """
    content, _ = await github_api.read_note(path)

    count = content.count(old_text)
    if count == 0:
        return json.dumps({
            "ok": False,
            "error": "old_text not found in file. Read the note again — the text must match exactly.",
        })
    if count > 1 and not replace_all:
        return json.dumps({
            "ok": False,
            "error": f"old_text appears {count} times. Either add surrounding context to make it unique, or set replace_all=true.",
        })

    new_content = content.replace(old_text, new_text) if replace_all else content.replace(old_text, new_text, 1)
    message = commit_message or f"Edit {path}"
    commit_sha = await github_api.write_note(path, new_content, message)
    return json.dumps({"ok": True, "path": path, "commit": commit_sha[:8], "replacements": count if replace_all else 1})


@mcp.tool()
async def append_to_note(path: str, text: str, commit_message: str = "") -> str:
    """
    Append text to the end of a note. Adds a newline separator if needed.
    Use this for running lists, journals, log files, etc.
    """
    path = _ensure_md(path)
    try:
        content, _ = await github_api.read_note(path)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            content = ""
        else:
            raise

    separator = "" if content == "" or content.endswith("\n") else "\n"
    new_content = content + separator + text
    if not new_content.endswith("\n"):
        new_content += "\n"

    message = commit_message or f"Append to {path}"
    commit_sha = await github_api.write_note(path, new_content, message)
    return json.dumps({"ok": True, "path": path, "commit": commit_sha[:8]})


@mcp.tool()
async def write_note(path: str, content: str, commit_message: str = "") -> str:
    """
    Create a new note OR fully overwrite an existing one. Use sparingly:
    - For NEW notes — this is the right tool
    - For full rewrites of existing notes (rare)

    For any edit to an existing note, prefer edit_note() or append_to_note() —
    they're safer because they only change what you specify.

    path: file path like "ideas.md" or "work/standup.md" — must end in .md (auto-added if missing)
    """
    path = _ensure_md(path)
    message = commit_message or f"Update {path}"
    commit_sha = await github_api.write_note(path, content, message)
    return json.dumps({"ok": True, "path": path, "commit": commit_sha[:8]})


@mcp.tool()
async def rename_note(old_path: str, new_path: str, commit_message: str = "") -> str:
    """
    Rename or move a note. Use this rather than write+delete so the operation is
    atomic in intent (though it still produces 2 commits).

    Will refuse to overwrite an existing file at new_path.
    """
    new_path = _ensure_md(new_path)
    content, _ = await github_api.read_note(old_path)

    # Refuse to clobber an existing destination
    try:
        await github_api.read_note(new_path)
        return json.dumps({"ok": False, "error": f"{new_path} already exists. Delete it first or pick a different name."})
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 404:
            raise

    message = commit_message or f"Rename {old_path} → {new_path}"
    await github_api.write_note(new_path, content, message)
    await github_api.delete_note(old_path, message)
    return json.dumps({"ok": True, "from": old_path, "to": new_path})


@mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
async def delete_note(path: str, commit_message: str = "") -> str:
    """
    DESTRUCTIVE: Permanently delete a note from the repo.

    ALWAYS confirm with the user in plain language before calling this tool.
    Show them the exact path and wait for explicit confirmation ("yes", "delete it", etc.).
    Never delete based on inference — only on explicit instruction.

    Deleted notes can still be recovered from git history, but you shouldn't rely on that.
    """
    message = commit_message or f"Delete {path}"
    commit_sha = await github_api.delete_note(path, message)
    return json.dumps({"ok": True, "path": path, "commit": commit_sha[:8]})
