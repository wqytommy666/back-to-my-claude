# Back to My Claude 🔥

Recover **Claude Desktop → Code** conversation history that vanished after you
switched Claude accounts (or lost access to the old one).

When you log in with a different account, the **Code → Recents** list goes
(nearly) empty. The old conversations aren't deleted — Claude Desktop just
renders Recents from the *current* account's active session-group folder, and
your old sessions live under a *different* account folder on disk. This tool
copies them back into the current account so they reappear.

It ships as a [Claude Code](https://claude.com/claude-code) **skill**, but the
script is plain Python and runs on its own too.

> **macOS · Windows · Linux** (Claude Desktop). Non-destructive: it only ever
> **copies** files, never deletes or moves your originals, and every run is
> logged so it can be undone.

## How it works

Claude Desktop stores each Code session as a small JSON index file under its
data directory (the script auto-detects this per OS):

```
<ClaudeDesktopDir>/claude-code-sessions/
    <accountId>/<groupId>/local_<sessionId>.json
```

| OS      | `<ClaudeDesktopDir>`                             |
|---------|-------------------------------------------------|
| macOS   | `~/Library/Application Support/Claude`           |
| Windows | `%APPDATA%\Claude` (`…\AppData\Roaming\Claude`)  |
| Linux   | `~/.config/Claude` (`$XDG_CONFIG_HOME/Claude`)   |

Set the `CLAUDE_DESKTOP_DIR` env var to override if your install differs.

- One `<accountId>` folder **per login**.
- `<groupId>` is a session-group (workspace instance).
- **Recents renders only from the current account's active group folder.**

So the fix is to copy the orphaned `local_*.json` files into the current group
folder. (Copying them into a *sibling* group folder does **not** work — the
running window only reads its own active group. That's the trap this tool avoids
by auto-detecting the correct target via newest file mtime.)

The full transcripts live separately in `~/.claude/projects/**.jsonl` and are
shared across accounts, so recovered sessions open with their real content.

## Install

### As a Claude Code skill

**macOS / Linux:**

```bash
git clone https://github.com/wqytommy666/back-to-my-claude.git
mkdir -p ~/.claude/skills
cp -R back-to-my-claude ~/.claude/skills/back-to-my-claude
```

**Windows (PowerShell):**

```powershell
git clone https://github.com/wqytommy666/back-to-my-claude.git
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse -Force back-to-my-claude "$HOME\.claude\skills\back-to-my-claude"
```

Then just ask Claude Code: *"recover my Claude Code chats"* /
*"找回我的 claude code 对话记录"*, or run `/back-to-my-claude`.

### Standalone script

```bash
python3 scripts/recover.py            # survey only, no writes  (use `python` on Windows)
```

## Usage

> On Windows, use `python` instead of `python3`.

```bash
# 1. Survey every account folder on disk (read-only): counts, dates, titles.
python3 scripts/recover.py

# 2. Copy sessions from all other accounts into your current group.
python3 scripts/recover.py --recover

#    ...or only from one specific old account:
python3 scripts/recover.py --recover --from <accountId>

# 3. FULLY quit Claude Desktop, then reopen it and open the Code tab.
#      macOS   : Cmd+Q
#      Windows : right-click the tray icon -> Quit (the X only minimizes)
#      Linux   : close all windows + quit from tray/menu (Ctrl+Q in most builds)
#    Your old sessions are back in Recents. (The script prints the right hint too.)

# 4. Undo if needed:
python3 scripts/recover.py --undo       # revert the last recover
python3 scripts/recover.py --undo-all   # revert every recover this tool did
```

## Safety

- **Copy only** — old account folders are never modified; nothing is lost.
- **Idempotent** — files already present in the destination are skipped.
- **Reversible** — each `--recover` writes a manifest to
  `~/.claude/back-to-my-claude/`; `--undo` removes exactly those files.
- **No credentials touched** — it reads session-index JSONs and transcript
  filenames only, never tokens or cookies.

## Notes

- This moves history between **local** accounts on the same computer. It can't
  pull sessions that only ever existed on another device/server — if you need the
  account itself back, reset the login at claude.ai.
- A session whose transcript is missing will still list but may open empty; the
  survey reports how many recovered sessions have a local transcript.

## License

MIT — see [LICENSE](LICENSE).

---

*Built with [Claude Code](https://claude.com/claude-code).*
