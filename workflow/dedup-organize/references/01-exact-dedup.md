# Reference: Exact Duplicate Detection

## fclones (primary)

Fast, parallel, Rust-based. Best for large directories.

### Scan

```bash
# JSON output (preferred for agent parsing)
fclones group /target \
  --format json \
  --output /tmp/fclones-report.json \
  --min-size 1KB

# Human-readable (for showing user)
fclones group /target \
  --format text \
  --min-size 1KB
```

Key flags:
- `--min-size 1KB` — skip tiny files
- `--max-depth N` — limit recursion
- "*.mp4" --include "*.pdf"` — filter by glob
- `--exclude ".git/**" "node_modules/**"` — exclude paths

### Review

Parse `/tmp/fclones-report.json`:
- `groups[].size` — size per file
- `groups[].files[].path` — file path
- `groups[].files[].size` — individual size (should match group)
- Calculate waste: `size * (file_count - 1)`

### Apply (after confirmation)

```bash
# Delete all duplicates (keeps first file in each group)
fclones remove /tmp/fclones-report.json

# Replace duplicates with hardlinks (saves space, files appear identical)
fclones link /tmp/fclones-report.json --link-type hardlink

# Replace duplicates with reflinks (CoW — safest, needs filesystem support)
fclones link /tmp/fclones-report.json --link-type reflink
```

**Reflink pre-check:**
```bash
FS=$(stat -f -c %T /target 2>/dev/null)
# ext4: reflink supported via --reflink=always in cp, but fclones needs XFS/Btrfs/ZFS
# For ext4, prefer hardlink or delete
# For XFS/Btrfs: reflink is safe
```

### Cross-device check

```bash
# Before linking, verify all files in a group are on the same device
df /path/to/file1 /path/to/file2
# Compare device mount points. If different → cannot hardlink/reflink, must delete/move.
```

## rmlint (fallback + lint)

C-based, also finds non-duplicate lint (empty files, broken symlinks, etc.).

### Scan

```bash
# Generate shell script + JSON
rmlint /target \
  -o sh:/tmp/rmlint.sh \
  -o json:/tmp/rmlint.json \
  -e "/.git" "/node_modules" "/.venv"

# Include empty files and broken symlinks
rmlint /target \
  --types=emptyfiles,brokensymlins,emptyduplicates \
  -o sh:/tmp/rmlint-lint.sh \
  -o json:/tmp/rmlint-lint.json
```

### Review

Parse `/tmp/rmlint.json`:
- Look for `"type": "duplicate"` entries
- `[]` file paths, `"size"` per group

### Apply

```bash
# Review the generated shell script first
cat /tmp/rmlint.sh  # User should review!

# Execute (after user confirmation)
bash /tmp/rmlint.sh
```

## Presentation Format

When showing duplicate groups to user:

```
Duplicate Group 1 of 23  (confidence: exact match)
  Size: 4.2 GB per file | Waste: 8.4 GB (1 extra copies)
  ✓ KEEP  /mnt/c/Videos/movie_1080p.mkv  (1920x1080, H.264, 8000 kbps)
  ✕ RM    /mnt/c/Downloads/movie_720p.mkv  (1280x720, H.264, 2000 kbps)
  ✕ RM    /mnt/c/Videos/backup/movie_copy.mkv  (same resolution, lower bitrate)

Duplicate Group 2 of 23  (confidence: exact match)
  Size: 250 MB per file | Waste: 250 MB (1 extra copy)
  ✓ KEEP  /mnt/c/Documents/report_final.docx  (modified: 2026-01-15)
  ? REV   /mnt/c/Documents/report_draft.docx  (modified: 2025-11-03)

Options: [k]eep shown / [s]elect manually / [a]pply all / [s]kip group
```

Use `✓ KEEP` for recommended, `✕ RM` for recommended removal, `? REV` for needs-review.
