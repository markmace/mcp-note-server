"""Thin wrapper around the GitHub Contents API for reading/writing notes."""

import base64
import os

import httpx

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = os.environ.get("GITHUB_REPO", "markmace/notes")

_BASE = "https://api.github.com"
_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


async def list_notes(folder: str = "") -> list[dict]:
    """Return all .md files in the repo (recursively), optionally under folder."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_BASE}/repos/{GITHUB_REPO}/git/trees/HEAD",
            params={"recursive": "1"},
            headers=_HEADERS,
            timeout=15,
        )
        r.raise_for_status()

    prefix = folder.strip("/") + "/" if folder.strip("/") else ""
    return [
        {"path": item["path"], "size": item.get("size", 0)}
        for item in r.json().get("tree", [])
        if item["type"] == "blob"
        and item["path"].endswith(".md")
        and item["path"].startswith(prefix)
    ]


async def read_note(path: str) -> tuple[str, str]:
    """Return (content, sha). sha is needed to update the file later."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_BASE}/repos/{GITHUB_REPO}/contents/{path}",
            headers=_HEADERS,
            timeout=15,
        )
        r.raise_for_status()

    data = r.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]


async def write_note(path: str, content: str, message: str) -> str:
    """Create or update a file. Fetches current SHA automatically if file exists."""
    sha: str | None = None
    try:
        _, sha = await read_note(path)
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 404:
            raise

    body: dict = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
    }
    if sha:
        body["sha"] = sha

    async with httpx.AsyncClient() as client:
        r = await client.put(
            f"{_BASE}/repos/{GITHUB_REPO}/contents/{path}",
            headers=_HEADERS,
            json=body,
            timeout=15,
        )
        r.raise_for_status()

    return r.json()["commit"]["sha"]


async def delete_note(path: str, message: str) -> str:
    """Delete a file. Returns the commit SHA."""
    _, sha = await read_note(path)
    async with httpx.AsyncClient() as client:
        r = await client.request(
            "DELETE",
            f"{_BASE}/repos/{GITHUB_REPO}/contents/{path}",
            headers=_HEADERS,
            json={"message": message, "sha": sha},
            timeout=15,
        )
        r.raise_for_status()
    return r.json()["commit"]["sha"]


async def search_notes(query: str) -> list[dict]:
    """Search all markdown files for query (case-insensitive). Returns matching files + snippets."""
    files = await list_notes()
    results = []
    q = query.lower()

    async with httpx.AsyncClient() as client:
        for f in files:
            r = await client.get(
                f"{_BASE}/repos/{GITHUB_REPO}/contents/{f['path']}",
                headers=_HEADERS,
                timeout=15,
            )
            if not r.is_success:
                continue
            content = base64.b64decode(r.json()["content"]).decode("utf-8")
            if q in content.lower():
                snippets = [line.strip() for line in content.splitlines() if q in line.lower()]
                results.append({"path": f["path"], "snippets": snippets[:3]})

    return results
