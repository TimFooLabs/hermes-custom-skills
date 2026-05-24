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

**Critical ordering:** Deduplicate BEFORE organizing. Otherwise duplicates get scattered into different folders and become harder to find.

## Safety Rules

0. **Quarantine-first.** Never delete directly from NAS. All candidates move to `/target/_quarantine/` with 30+ day hold.
1. **Never auto-delete.** Always present findings and get confirmation.
2. **Undo manifest first.** Generate `manifest.json` + `rollback.sh` before any destructive action.
3. **Filesystem checks before linking:**
   - Detect filesystem type: `stat -f -c %T /target`
   - Check reflink support before using `--link-type reflink`
   - Check mount points: `df /path1 /path2` — never hardlink across devices
   - Never link inside cloud-sync folders (Dropbox, OneDrive, etc.)
   - CIFS/NAS: hardlinks likely unsupported; plan for move-to-quarantine instead
4. **Symlink policy:** `follow_symlinks: false` by default. Never follow symlinks during scan.
5. **Quality over recency:** Don't just keep "newest" or "best-named." Use ffprobe for media quality ranking. Prefer editable originals over exports for documents.
6. **Timeout protection:** All subprocess calls must have timeouts (3600s default).
7. **WSL path handling:** Normalize `/mnt/c/` etc. Warn about slower cross-filesystem hashing. NTFS is case-insensitive.
8. **Canonical source priority:** Define before dedup. Device backups > Google Photos > Drive > messaging > downloads.
9. **Separate exact from perceptual:** Run fclones/rmlint (exact hash) BEFORE Czkawka/VDF (perceptual). Stabilize before fuzzy matching.

## Quarantine Structure

Before any destructive action, create:

```
/target/_quarantine/
  duplicates-candidate/    # Files confirmed as duplicates (held 30+ days)
  empty-dirs/             # Empty directories (not deleted, just moved)
  archive-review/         # Old files for manual review
  safe-to-delete/         # After 30+ day hold, manual review passed
```

**Rules:**
- Move (never copy+delete on NAS)
- Preserve original relative path inside quarantine
- Log every move to manifest.json
- 30-day minimum hold before any deletion
- Deletion only from `safe-to-delete/` after manual review

## Execution Flow

```
Phase 0:  Pre-flight
          ├── NAS snapshot / backup verification
          ├── Create _quarantine/ structure
          ├── Verify filesystem type & capabilities
          ├── Check for cloud-sync folders → warn
          └── Confirm scope with user

Phase 1:  Define Canonical Source Rules
          ├── Document priority hierarchy for photos, videos, documents
          └── Get user approval on rules

Phase 2:  Full Inventory (read-only)
          ├── Directory overview (file count, size, types)
          ├── Date/size distribution
          ├── Identify empty dirs, loose files, junk
          └── Present summary. No changes.

Phase 3:  Exact Duplicate Audit (read-only)
          ├── fclones group scan → JSON report
          ├── rmlint scan → JSON report (also: empty files, broken symlinks)
          ├── Parse & normalize results
          └── Present duplicate groups with recommendations + confidence scores

Phase 4:  Exact Duplicate Quarantine
          ├── User reviews Phase 3 report
          ├── Move non-canonical copies to _quarantine/duplicates-candidate/
          ├── Apply canonical source rules from Phase 1
          ├── Generate undo manifest
          └── HOLD 30+ days

Phase 5:  Integrity Verification
          ├── Re-scan and compare with Phase 2 baseline
          ├── Verify media server paths still work
          ├── Spot-check quarantined files against originals (hash compare)
          └── Confirm no files were accidentally moved

Phase 6:  Perceptual Photo Dedup (Czkawka) — targeted
          ├── Scope: photo directories only (not videos)
          ├── Czkawka in audit mode → review matches
          ├── Move duplicates to quarantine
          └── HOLD 30+ days

Phase 7:  Perceptual Video Dedup (VDF) — targeted folders only
          ├── Scope: known overlap areas only (not entire drive)
          ├── VDF audit mode → review matches
          ├── Use ffprobe quality ranking
          └── Move duplicates to quarantine, HOLD 30+ days

Phase 8:  Organization (only after all dedup complete and verified)
          ├── Proposed folder structure for surviving files
          ├── Move into canonical structure
          ├── Cleanup empty directories (move to quarantine first)
          ├── Update media server library paths if needed
          └── Final report + manifest path

Phase 9:  30-Day Hold & Final Cleanup
          ├── Wait 30 days after last quarantine action
          ├── Manual review of _quarantine/ contents
          ├── Delete from safe-to-delete/ only after manual review
          └── Final verification: re-scan, compare with baseline
```

**Critical ordering:**
- Deduplicate BEFORE organizing — otherwise duplicates get scattered
- Exact dedup BEFORE perceptual dedup — stabilize with hash-based first
- Quarantine BEFORE deletion — always move first, delete after hold
- Folder reorganization LAST — only after all dedup is verified

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
