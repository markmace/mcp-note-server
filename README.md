# mcp-note-server

A Python MCP server that gives Claude read/write access to your notes stored in a GitHub repo. Edit in Obsidian, let Claude help clean things up.

## How it works

- Notes live in a GitHub repo as plain markdown files
- This server wraps the GitHub API and exposes 4 MCP tools
- Connect it to claude.ai as a custom connector
- Edit notes however you want (Obsidian, VS Code, etc.) — Claude can read and update them too

## MCP tools

| Tool | What it does |
|------|-------------|
| `list_notes(folder?)` | Lists all `.md` files, optionally filtered by folder |
| `read_note(path)` | Returns the full content of a note |
| `write_note(path, content, commit_message?)` | Creates or updates a note |
| `search_notes(query)` | Case-insensitive search across all notes, returns snippets |

## Deploy to Fly.io

### Prerequisites

- [flyctl](https://fly.io/docs/hands-on/install-flyctl/)
- A GitHub repo for your notes
- A GitHub Personal Access Token with `repo` scope

### 1. Create the GitHub PAT

Go to github.com/settings/tokens → Generate new token (classic) → check **repo** → copy the token.

### 2. Launch the app

```bash
fly launch   # first time only — creates fly.toml and provisions the app
```

### 3. Set secrets

```bash
# Random token that goes in your claude.ai connector URL
fly secrets set MCP_TOKEN=$(openssl rand -hex 32)

fly secrets set GITHUB_TOKEN=ghp_your_pat_here
fly secrets set GITHUB_REPO=youruser/your-notes-repo
```

### 4. Deploy

```bash
fly deploy
```

### 5. Add to claude.ai

1. **Settings → Connectors → Add custom connector**
2. URL: `https://<app-name>.fly.dev/mcp/<MCP_TOKEN>`
3. Save. No OAuth needed. Works on web and mobile.

## Local dev

```bash
uv sync

export MCP_TOKEN=dev GITHUB_TOKEN=ghp_... GITHUB_REPO=youruser/notes
uv run uvicorn main:app --reload
```

## File layout

```
main.py        — FastAPI app + token auth middleware + CORS
mcp_server.py  — 4 MCP tools
github_api.py  — GitHub Contents API client
auth.py        — constant-time token comparison
Dockerfile
fly.toml
```
