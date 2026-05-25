# mcp-note-server

Give Claude a key to your notes.

## Why

I take notes in Obsidian. Claude is the best writing partner I've found. But the two don't talk to each other — I was constantly copy-pasting between them.

This fixes that. Notes live in a GitHub repo. Obsidian edits them locally and syncs via git. A small MCP server lets Claude read and write the same files. Now I can say "Claude, clean up my standup notes from this week" and it actually does — no copy, no paste, no upload.

It works on iPhone too, because Obsidian and claude.ai both do.

## How it works

```
       ┌──────────────┐         ┌──────────────┐
       │  Obsidian    │◄───────►│   GitHub     │
       │ (Mac + iOS)  │  git    │  your-notes  │
       └──────────────┘         └──────┬───────┘
                                       │ API
                                       ▼
                              ┌──────────────────┐
                              │  MCP server      │
                              │  (this repo)     │
                              │  on Fly.io       │
                              └────────┬─────────┘
                                       │ MCP
                                       ▼
                              ┌──────────────────┐
                              │   claude.ai      │
                              │  custom connector│
                              └──────────────────┘
```

Four tools Claude can call:

| Tool | What it does |
|------|-------------|
| `list_notes(folder?)` | List all markdown files, optionally filtered |
| `read_note(path)` | Read a note's content |
| `write_note(path, content, commit_message?)` | Create or update a note |
| `search_notes(query)` | Case-insensitive search across all notes |

Every write is a git commit, so you have full history and can roll anything back.

---

## Setup

You'll need: a GitHub account, [flyctl](https://fly.io/docs/hands-on/install-flyctl/), and Obsidian.

### 1. Make a notes repo

Create an empty private repo on GitHub — e.g. `youruser/notes`. This is where your notes will live.

### 2. Make a GitHub PAT

github.com/settings/tokens → **Generate new token (classic)** → check **`repo`** → generate and copy the token. You'll use it twice: once for the server, once for Obsidian.

### 3. Deploy the server

```bash
git clone https://github.com/markmace/mcp-note-server
cd mcp-note-server
fly launch                       # accept defaults, but don't deploy yet

fly secrets set \
  MCP_TOKEN=$(openssl rand -hex 32) \
  GITHUB_TOKEN=ghp_your_pat_here \
  GITHUB_REPO=youruser/notes

fly deploy
```

Grab the URL it prints. Then:

```bash
fly secrets list  # MCP_TOKEN is hidden, but you can read it once after setting:
# (or just remember the value you set above)
```

### 4. Connect Claude

In claude.ai: **Settings → Connectors → Add custom connector**

URL: `https://<your-app>.fly.dev/mcp/<your-MCP_TOKEN>`

Save. Now ask Claude "list my notes" — should come back empty since you haven't made any yet.

### 5. Obsidian on Mac

```bash
git clone https://github.com/youruser/notes ~/notes
gh auth setup-git   # tells git to use the gh CLI for HTTPS auth
```

Then in Obsidian:
1. **Open folder as vault** → pick `~/notes`
2. **Settings → Community plugins → Turn on**
3. Browse → install **Git** by Vinzent03 → Enable
4. **Settings → Git** — these are the settings worth changing:

   | Setting | Value |
   |---|---|
   | Auto commit-and-sync interval | `5` minutes |
   | Auto commit-and-sync after stopping file edits | ✅ on |
   | Pull on startup | ✅ on (default) |
   | Auto pull interval | leave at `0` |

5. Add a `.gitignore` to the vault root:
   ```
   .obsidian/workspace.json
   .obsidian/workspace-mobile.json
   .obsidian/plugins/obsidian-git/data.json
   .trash/
   ```
   That last line matters — it's where the iOS plugin stores your PAT.

6. Commit your `.obsidian/` config so iOS picks up the plugin automatically:
   ```bash
   git -C ~/notes add .obsidian/ .gitignore
   git -C ~/notes commit -m "Obsidian config"
   git -C ~/notes push
   ```

7. (Optional) Move any README in your notes repo into `.github/README.md` — GitHub still renders it on the repo page, but Obsidian hides dot-folders by default, so it won't clutter your vault.

### 6. Obsidian on iOS

This one has more sharp edges. Read the whole step before tapping anything.

1. Install Obsidian on iPhone, create a new **empty** vault
2. **Settings → Community plugins → Turn on**, then install **Git** by Vinzent03 and enable it
3. **Settings → Git → Authentication/Commit Author** — enter your GitHub username and the PAT from step 2. **This must happen before the clone, not during.** The iOS plugin won't prompt mid-clone.
4. Open the command palette (swipe down on the note area) → **"Clone an existing remote repo"**
5. URL: `https://github.com/youruser/notes` (double-check for typos — most failures are this)
6. Vault root: leave blank
7. "Does your remote contain a .obsidian folder?" → **Yes**
8. "To avoid conflicts..." → **Delete all your local config and plugins** (your iOS vault is empty anyway)
9. After the clone finishes, **close and reopen Obsidian** — the plugin reload during a clone can show a spurious error that goes away after a restart

iOS doesn't background-sync. Before you put your phone down, swipe down → **"Git: Commit all changes and sync"** to push.

---

## Daily use

Edit notes in Obsidian like normal. Ask Claude things like:

- "Clean up my standup notes from this week"
- "Search my notes for anything I wrote about the migration"
- "Add today's meeting notes to `work/standup.md`"
- "What's in my ideas folder?"

Claude's edits show up in Obsidian on next pull (5 min by default, or pull manually).

## Local development

```bash
uv sync
export MCP_TOKEN=dev GITHUB_TOKEN=ghp_... GITHUB_REPO=youruser/notes
uv run uvicorn main:app --reload
```

## File layout

```
main.py        — FastAPI + ASGI middleware (token auth, CORS, path rewriting)
mcp_server.py  — the 4 MCP tools
github_api.py  — thin GitHub Contents API client
auth.py        — constant-time token comparison
Dockerfile
fly.toml
```

## A note on cost

Fly.io's free tier covers this comfortably — 256MB RAM, one shared CPU, auto-stops when idle. GitHub API calls are well under the 5000/hour rate limit unless you're really hammering it. The whole thing runs for $0/month for personal use.

## License

MIT — do whatever you want with it.
