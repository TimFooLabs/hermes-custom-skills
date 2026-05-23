---
name: dedup-organize
description: >
  Find and remove duplicate files and videos, and organize messy directories.
  Covers exact duplicates (fclones/rmlint), video duplicates (VDF/videohash),
  near-duplicate documents (semhash), and folder reorganization.
  Trigger words: duplicate, dedup, deduplicate, organize files, clean up,
  find similar videos, remove duplicates, file cleanup.
version: 1.1.0
author: timfoo
tags: [dedup, duplicate, organize, files, video, cleanup, fclones, vdf]
---

# Dedup & Organize

## Operating Modes

**Three modes, strictly separated:**

| Mode | What it does | Filesystem changes? |
|------|-------------|-------------------|
| **Audit** (default) | Scan, analyze, propose | None |
| **Apply** | Execute approved actions | Yes, with undo manifest |
| **Rollback** | Revert a prior apply run | Yes, from manifest |

```yaml
default_mode: audit
destructive_actions_require_confirmation: true
rollback_supported: true
follow_symlinks: false
```

**Rules:**
- Always start in **Audit** mode. Never modify files without explicit user confirmation.
- **Apply** mode requires: (a) audit report reviewed by user, (b) explicit "yes/proceed/apply" confirmation, (c) undo manifest generated before any changes.
- **Rollback** mode requires an existing undo manifest from a prior apply run.
- If user says "just show me" or "what would you do" → Audit only.
- If user says "go ahead" or "do it" → Apply with manifest.

## Default Exclude Rules

**Never scan or modify these directories:**

```
.git/
node_modules/
.venv/
__pycache__/
.cache/
.pytest_cache/
.mypy_cache/
.Trash/
.trash/
$RECYCLE.BIN/
System Volume Information/
Dropbox/
Google Drive/
OneDrive/
iCloud Drive/
```

Also exclude: files < 1KB (configurable), broken symlinks.

## Execution Flow

```
Phase 0:  Pre-flight checks
          ├── Verify tools installed (§5)
          ├── Detect filesystem type & capabilities
          ├── Check for cloud-sync folders → warn
          └── Confirm scope with user

Phase 1:  Inventory & Analysis
          ├── Directory overview (file count, size, types)
          ├── Date distribution
          ├── Size distribution
          └── Present summary to user

Phase 2:  Exact Duplicate Detection → references/01-exact-dedup.md
          ├── fclones group scan
          ├── Parse & normalize results
          ├── Quality heuristic ranking (§6)
          └── Present duplicate groups with recommendations

Phase 3:  Video Duplicate Detection → references/02-video-dedup.md
          ├── VDF visual similarity scan
          ├── Optional: partial clip detection
          ├── Optional: videohash for lightweight checks
          └── Present similar video groups

Phase 4:  Semantic Duplicate Detection → references/03-semantic-dedup.md
          └── semhash for document collections (optional, power-user)

Phase 5:  Organization Proposal → references/04-organization.md
          ├── Proposed folder structure
          ├── Batch move/rename plan
          └── Archive candidates

Phase 6:  User Review
          └── Present full plan. Wait for confirmation.

Phase 7:  Apply (if confirmed)
          ├── Generate undo manifest
          ├── Execute dedup actions first (before organizing)
          ├── Execute organization moves
          ├── Cleanup empty directories
          └── Final report + manifest path

Phase 8:  Rollback (if needed)
          └── Restore from undo manifest
```

**Critical ordering:** Deduplicate BEFORE organizing. Otherwise duplicates get scattered into different folders and become harder to find.

## Safety Rules

1. **Never auto-delete.** Always present findings and get confirmation.
2. **Undo manifest first.** Generate `manifest.json` + `rollback.sh` before any destructive action.
3. **Filesystem checks before linking:**
   - Detect filesystem type: `stat -f -c %T /target`
   - Check reflink support before using `--link-type reflink`
   - Check mount points: `df /path1 /path2` — never hardlink across devices
   - Never link inside cloud-sync folders (Dropbox, OneDrive, etc.)
4. **Symlink policy:** `follow_symlinks: false` by default. Never follow symlinks during scan. Warn if symlinks are detected in scan path.
5. **Quality over recency:** Don't just keep "newest" or "best-named." Use ffprobe for media quality ranking. Prefer editable originals over exports for documents.
6. **Timeout protection:** All subprocess calls must have timeouts (3600s default).
7. **WSL path handling:** Normalize `/mnt/c/` etc. Warn about slower cross-filesystem hashing. NTFS is case-insensitive — handle accordingly.

## Undo Manifest Schema

Every apply run creates:

```
~/.hermes/logs/dedup-organize/run-<ISO8601>/
  manifest.json          # Structured log of all actions
  pre-state.json         # Snapshot of affected files before changes
  commands.sh            # Exact commands that were run
  rollback.sh            # Generated rollback script
```

`manifest.json` structure:

```json
{
  "run_id": "2026-05-23T14-30-00",
  "mode": "apply",
  "scan_path": "/mnt/c/Users/User/Videos",
  "actions": [
    {
      "sequence": 1,
      "action": "delete|move|hardlink|reflink|rename",
      "tool": "fclones|vdf|manual",
      "original_path": "/full/path/to/file.mp4",
      "new_path": "/full/path/to/destination.mp4",
      "sha256": "abc123...",
      "size": 104857600,
      "mtime": "2025-03-15T10:30:00",
      "reason": "duplicate: lower bitrate (2000 vs 8000 kbps)",
      "confidence": 0.99
    }
  ],
  "stats": {
    "files_deleted": 12,
    "files_moved": 45,
    "space_reclaimed": 10737418240,
    "errors": 0
  }
}
```

## Confidence Scoring

Every action includes a confidence score:

| Score | Meaning | Action |
|-------|---------|--------|
| 0.99 | Cryptographic hash match | Auto-recommend, still confirm |
| 0.90–0.98 | Perceptual match (video/image) | Recommend, flag for review if borderline |
| 0.70–0.89 | Semantic similarity | Flag for manual review |
| < 0.70 | Weak match | Do not recommend, show as "maybe" |

## Quick Decision Tree

```
User says "find duplicates"          → Phase 1→2→6 (audit)
User says "find duplicate videos"     → Phase 1→3→6 (audit)
User says "organize my files"         → Phase 1→5→6 (audit)
User says "clean up old files"        → Phase 1→5→6 (audit, focus on age)
User says "go ahead" / "do it"        → Phase 7 (apply, after audit)
User says "undo that" / "rollback"    → Phase 8 (rollback from manifest)
User says "just show me"              → Phase 1 only (inventory)
```

## Tool Priority

**Exact duplicates:** fclint (primary) → rmlint (fallback + lint detection)
**Video duplicates:** VDF CLI (primary) → videohash (lightweight fallback)
**Semantic dedup:** semhash (optional, document collections only)
**Quality analysis:** ffprobe (media), file + metadata inspection (documents)

If a preferred tool is not installed, use the fallback. If no tool is available, ask user to install (provide commands from `references/05-tool-install.md`).
