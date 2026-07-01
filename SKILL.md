---
name: back-to-my-claude
description: >
  Recover Claude Desktop "Code" conversation history that disappeared after
  switching or losing access to a Claude account. When a user logs in with a
  different account, the Code > Recents list goes (nearly) empty because it only
  renders sessions from the CURRENT account's active group folder — the old
  sessions are still on disk under a different account folder. This skill finds
  those orphaned sessions and copies them into the current account so they show
  up in Recents again. Trigger on: "recover my Claude Code chats", "找回 claude
  code 对话记录", "another/old account I can't log into", "登录不上了 之前的对话",
  "Code Recents is empty after switching accounts", "bring back my old Claude
  Desktop conversations". macOS + Claude Desktop only.
compatibility: requires-macos, requires-claude-desktop
---

# Back to My Claude 🔥

Bring Claude Desktop **Code** sessions from another account (one you switched
away from or can no longer log into) back into the account you're logged into
**now**, so they reappear in the **Code → Recents** list.

## Why sessions "vanish"

Claude Desktop stores each Code session as a small JSON index file:

```
~/Library/Application Support/Claude/claude-code-sessions/
    <accountId>/<groupId>/local_<sessionId>.json
```

- One `<accountId>` folder **per login/account**.
- `<groupId>` = a session-group (workspace instance) under that account.
- The **Recents list renders only from the current account's active group
  folder.** Sessions created under a different login sit under a different
  `<accountId>` folder, so switching accounts makes them disappear from the UI —
  even though the index files, and the full transcripts under
  `~/.claude/projects/**.jsonl`, are all still on disk.

The fix is simply to copy the orphaned `local_*.json` files into the **current
group folder**. (Copying them into a *sibling* group folder does NOT work — the
running window only reads its own active group. This is the mistake to avoid.)

## How to run it

The bundled script auto-detects the current account/group by newest file mtime
(the running app constantly touches the active session), and copies preserving
mtime so imported old sessions never get mistaken for "current".

1. **Survey** what's on disk (no writes):

   ```bash
   python3 ~/.claude/skills/back-to-my-claude/scripts/recover.py
   ```

   Shows every account folder with session counts, date ranges, top project
   dirs and sample titles, and marks the CURRENT account. Use this to confirm
   which account is the old/locked-out one before importing.

2. **Recover** (copies every session from all other accounts into the current
   group; non-destructive, logged for undo):

   ```bash
   python3 ~/.claude/skills/back-to-my-claude/scripts/recover.py --recover
   ```

   To pull from just one old account, add `--from <accountId>` (copy the id from
   step 1). Preview a single account without writing: run with only `--from
   <accountId>`.

3. **Tell the user to fully restart the app** — this is required; the list is
   only re-read on a cold start:
   > Quit Claude Desktop with **Cmd+Q** (not just closing the window), reopen
   > it, then open the **Code** tab. The old sessions should be in Recents.

4. If they don't appear, or the user wants to back out:

   ```bash
   python3 ~/.claude/skills/back-to-my-claude/scripts/recover.py --undo      # last run
   python3 ~/.claude/skills/back-to-my-claude/scripts/recover.py --undo-all  # everything
   ```

## Safety

- **Never deletes or moves originals** — copy only. Old account folders are left
  untouched, so nothing is lost even if something goes wrong.
- Files already in the destination are skipped (idempotent; safe to re-run).
- Every `--recover` writes a manifest to `~/.claude/back-to-my-claude/` listing
  exactly what it copied, so `--undo` removes precisely those files and nothing
  else.
- Does **not** read tokens, cookies, or any auth/credential files — only the
  session index JSONs and transcript filenames.

## Good to know

- Opened conversations render from `~/.claude/projects/**.jsonl`. A session whose
  transcript is missing will still list but may open empty — the survey reports
  how many imported sessions have a local transcript.
- This only moves history between **local** accounts on the same Mac. It cannot
  pull sessions that only ever existed on another device/server. If the real
  goal is to get the account itself back, recovering that login (password reset
  at claude.ai) is the cleaner fix.
- The Recents list is **not** rebuilt from the account folder at large — only
  from the single active group folder — which is why this skill targets that
  folder specifically.
