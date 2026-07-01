#!/usr/bin/env python3
"""back-to-my-claude — bring Claude Desktop "Code" sessions from another
(locked-out / switched) account into the account you're logged into NOW.

How Claude Desktop stores Code sessions
---------------------------------------
Every Code session is a small JSON *index* file:

    ~/Library/Application Support/Claude/claude-code-sessions/
        <accountId>/<groupId>/local_<sessionId>.json

* <accountId>  : one folder per login/account.
* <groupId>    : a "session group" (workspace instance) under that account.
* local_*.json : per-session metadata (title, cwd, timestamps, cliSessionId).

The Code **Recents** list is rendered from the *current* account's *active
group* folder ONLY. When you log in with a different account, Claude reads a
different <accountId> folder, so every conversation from the old login vanishes
from Recents — even though the index files (and the full transcripts under
~/.claude/projects/**.jsonl) are all still on disk.

What this tool does
-------------------
Copies the orphaned local_*.json files into your CURRENT group folder so they
reappear in Recents after you restart the app. It is non-destructive:

* originals are never moved or deleted (copy only, preserves mtime);
* files already present in the destination are skipped;
* every copy is logged to a manifest so `--undo` can revert it exactly.

Detection of the "current" account/group is by newest file mtime — the running
app touches the active session's json constantly, and because copies preserve
the source mtime, imported old sessions never win that race.

Usage
-----
    python3 recover.py                 # summary of accounts (dry run, no writes)
    python3 recover.py --recover       # copy ALL other sessions into current group
    python3 recover.py --recover --from <accountId>   # only from one account
    python3 recover.py --undo          # revert the most recent recover
    python3 recover.py --undo-all      # revert every recover this tool did

After --recover: fully quit Claude Desktop (Cmd+Q, not just close window) and
reopen it, then open the Code tab.
"""
import argparse
import datetime
import glob
import json
import os
import shutil
import time

BASE = os.path.expanduser(
    "~/Library/Application Support/Claude/claude-code-sessions"
)
PROJECTS = os.path.expanduser("~/.claude/projects")
STATE_DIR = os.path.expanduser("~/.claude/back-to-my-claude")


def fmt(ms):
    try:
        return datetime.datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d")
    except Exception:
        return "?"


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def scan():
    """account_id -> {group_id: [filepath, ...]} (only groups with sessions)."""
    accounts = {}
    if not os.path.isdir(BASE):
        return accounts
    for acct in sorted(os.listdir(BASE)):
        ap = os.path.join(BASE, acct)
        if not os.path.isdir(ap):
            continue
        groups = {}
        for grp in sorted(os.listdir(ap)):
            gp = os.path.join(ap, grp)
            if not os.path.isdir(gp):
                continue
            files = sorted(glob.glob(os.path.join(gp, "local_*.json")))
            if files:
                groups[grp] = files
        if groups:
            accounts[acct] = groups
    return accounts


def newest(accounts):
    """Return (account_id, group_id) holding the most recently modified json."""
    best, best_m = None, -1.0
    for acct, groups in accounts.items():
        for grp, files in groups.items():
            for fp in files:
                m = os.path.getmtime(fp)
                if m > best_m:
                    best_m, best = m, (acct, grp)
    return best


def transcript_ids():
    """Set of cliSessionIds that have a real transcript on disk."""
    have = set()
    if not os.path.isdir(PROJECTS):
        return have
    for root, _dirs, files in os.walk(PROJECTS):
        for fn in files:
            if fn.endswith(".jsonl"):
                have.add(fn[:-6])
    return have


def summarize(files):
    titles, times, cwds = [], [], {}
    for fp in files:
        d = load(fp)
        la = d.get("lastActivityAt") or d.get("createdAt") or 0
        titles.append((la, d.get("title") or "(untitled)"))
        ca = d.get("createdAt")
        if ca:
            times.append(ca)
        c = d.get("cwd") or "?"
        cwds[c] = cwds.get(c, 0) + 1
    titles.sort(reverse=True)
    times.sort()
    return titles, times, cwds


def cmd_list(accounts, current):
    cur_acct, cur_grp = current
    print(f"Base: {BASE}\n")
    for acct, groups in accounts.items():
        allf = [f for fs in groups.values() for f in fs]
        titles, times, cwds = summarize(allf)
        tag = "   <== CURRENT (logged-in) account" if acct == cur_acct else ""
        print(f"Account {acct}  ({len(allf)} sessions, {len(groups)} group[s]){tag}")
        if times:
            print(f"    dates : {fmt(times[0])} .. {fmt(times[-1])}")
        for c, n in sorted(cwds.items(), key=lambda x: -x[1])[:4]:
            print(f"    [{n:4}] {c}")
        for _, t in titles[:4]:
            print(f"      - {t}")
        print()
    print("Current group folder (Recents render from here):")
    print(f"  {os.path.join(BASE, cur_acct, cur_grp)}")


def gather(accounts, current, from_acct=None):
    """Basename -> source path for every session not already in current group."""
    cur_acct, cur_grp = current
    cur_files = {os.path.basename(f) for f in accounts[cur_acct][cur_grp]}
    picked = {}
    for acct, groups in accounts.items():
        if from_acct and acct != from_acct:
            continue
        for grp, files in groups.items():
            if acct == cur_acct and grp == cur_grp:
                continue  # never copy the destination onto itself
            for fp in files:
                b = os.path.basename(fp)
                if b in cur_files or b in picked:
                    continue
                picked[b] = fp
    return picked


def cmd_recover(accounts, current, from_acct, do_write):
    cur_acct, cur_grp = current
    dest = os.path.join(BASE, cur_acct, cur_grp)
    picked = gather(accounts, current, from_acct)
    if not picked:
        print("Nothing to recover — no sessions found outside the current group.")
        return
    have = transcript_ids()
    with_tx = sum(1 for p in picked.values() if load(p).get("cliSessionId") in have)
    print(f"Destination (current group): {dest}")
    print(f"Sessions to import         : {len(picked)}")
    print(f"  of which have a local transcript in ~/.claude/projects: {with_tx}")
    if not do_write:
        print("\nDRY RUN — pass --recover to actually copy. Preview:")
        for b, p in list(sorted(picked.items()))[:10]:
            print(f"    {load(p).get('title') or '(untitled)'}")
        if len(picked) > 10:
            print(f"    ... and {len(picked) - 10} more")
        return
    copied = []
    for b, p in picked.items():
        target = os.path.join(dest, b)
        if os.path.exists(target):
            continue
        shutil.copy2(p, target)  # preserve mtime -> current-group detection stays robust
        copied.append(b)
    os.makedirs(STATE_DIR, exist_ok=True)
    manifest = os.path.join(STATE_DIR, f"manifest-{int(time.time())}.json")
    with open(manifest, "w") as f:
        json.dump({"dest": dest, "copied": copied, "ts": time.time()}, f, indent=2)
    print(f"\nCopied {len(copied)} session(s) into the current group.")
    print(f"Manifest: {manifest}")
    print("\nNEXT: fully quit Claude Desktop with Cmd+Q (not just the window),")
    print("      reopen it, and open the Code tab. Your sessions should be in Recents.")
    print("If they do not appear, run:  python3 recover.py --undo")


def cmd_undo(all_manifests):
    if not os.path.isdir(STATE_DIR):
        print("No manifests found — nothing to undo.")
        return
    mans = sorted(glob.glob(os.path.join(STATE_DIR, "manifest-*.json")))
    if not mans:
        print("No manifests found — nothing to undo.")
        return
    targets = mans if all_manifests else [mans[-1]]
    removed = 0
    for mp in targets:
        m = load(mp)
        dest = m.get("dest", "")
        for b in m.get("copied", []):
            fp = os.path.join(dest, b)
            if os.path.basename(fp).startswith("local_") and os.path.exists(fp):
                os.remove(fp)
                removed += 1
        os.rename(mp, mp + ".done")
    print(f"Removed {removed} imported file(s). Originals were never touched.")
    print("Fully quit (Cmd+Q) and reopen Claude Desktop to refresh the list.")


def main():
    ap = argparse.ArgumentParser(
        description="Recover Claude Desktop Code sessions across accounts."
    )
    ap.add_argument("--recover", action="store_true",
                    help="copy other accounts' sessions into current group")
    ap.add_argument("--from", dest="from_acct", metavar="ACCOUNT_ID",
                    help="only import from this account folder")
    ap.add_argument("--undo", action="store_true",
                    help="revert the most recent recover")
    ap.add_argument("--undo-all", action="store_true",
                    help="revert every recover this tool performed")
    args = ap.parse_args()

    if args.undo or args.undo_all:
        cmd_undo(args.undo_all)
        return

    accounts = scan()
    if not accounts:
        print(f"No Claude Desktop Code sessions found under:\n  {BASE}")
        print("Is Claude Desktop installed and have you opened the Code tab at least once?")
        return
    current = newest(accounts)
    if current is None:
        print("Could not determine the current session group.")
        return

    if args.recover:
        cmd_recover(accounts, current, args.from_acct, do_write=True)
    elif args.from_acct:
        cmd_recover(accounts, current, args.from_acct, do_write=False)
    else:
        cmd_list(accounts, current)


if __name__ == "__main__":
    main()
