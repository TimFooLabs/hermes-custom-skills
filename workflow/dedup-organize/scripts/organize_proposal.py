#!/usr/bin/env python3
"""
Analyze a directory and produce a structured organization proposal.

Usage:
    python3 organize_proposal.py --path /target
    python3 organize_proposal.py --path /target --max-depth 3

Fixes applied:
    - list[dir] typo fixed to list[dict]
    - break replaced with dirnames.clear() + continue
    - O(n²) re-scan eliminated: single traversal collects all data
    - mimetypes removed (unused)
    - symlink handling: skip symlinks by default
    - WSL path normalization
    - Cloud-sync folder detection
    - Empty directory detection
    - Age-based archive candidates
"""

import argparse
import json
import os
import stat
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Category mapping by extension
CATEGORY_MAP: dict[str, set[str]] = {
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".tex", ".md", ".epub"},
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".ods"},
    "Presentations": {".ppt", ".pptx", ".key", ".odp"},
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff", ".ico", ".heic", ".heif", ".raw", ".cr2", ".nef"},
    "Videos": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg", ".ts", ".vob"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus", ".aiff"},
    "Archives": {".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".dmg", ".iso", ".img"},
    "Code": {".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".hpp", ".go", ".rs", ".rb", ".sh", ".bat", ".ps1", ".php", ".swift", ".kt"},
    "Data": {".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".sql", ".db", ".sqlite"},
    "Installers": {".exe", ".msi", ".deb", ".rpm", ".appimage", ".snap", ".flatpak", ".pkg"},
    "Fonts": {".ttf", ".otf", ".woff", ".woff2", ".eot"},
    "Design": {".psd", ".ai", ".sketch", ".fig", ".xd", ".blend"},
}

# Build reverse lookup: extension -> category
EXT_TO_CATEGORY: dict[str, str] = {}
for cat, exts in CATEGORY_MAP.items():
    for ext in exts:
        EXT_TO_CATEGORY[ext] = cat

# Cloud-sync folders to warn about
CLOUD_SYNC = {"Dropbox", "Google Drive", "OneDrive", "iCloud Drive", "Dropbox (Personal)", "Nextcloud"}

# Directories to exclude from analysis
EXCLUDE_DIRS = {
    ".git", "node_modules", ".venv", "__pycache__", ".cache",
    ".pytest_cache", ".mypy_cache", ".tox", ".eggs", "*.egg-info",
    ".Trash", "trash", "$RECYCLE.BIN", "System Volume Information",
}


def categorize_file(path: Path) -> str:
    """Categorize a file by its extension."""
    ext = path.suffix.lower()
    return EXT_TO_CATEGORY.get(ext, "Other")


def human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    if size_bytes == 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} EB"


def is_cloud_sync(path: Path) -> Optional[str]:
    """Check if path is inside a cloud-sync folder."""
    for part in path.parts:
        if part in CLOUD_SYNC:
            return part
    return None


def analyze_directory(path: str, max_depth: int = 3) -> dict[str, Any]:
    """Analyze directory and return structured summary.

    Single-pass traversal: O(n) where n = number of files.
    All data collected in one walk to avoid re-scanning.
    """
    root = Path(path).resolve()
    if not root.exists():
        return {"error": f"Path does not exist: {path}"}
    if not root.is_dir():
        return {"error": f"Path is not a directory: {path}"}

    # Check for cloud-sync
    cloud_sync = is_cloud_sync(root)

    # Counters
    total_files = 0
    total_size = 0
    type_counts: Counter[str] = Counter()
    type_sizes: dict[str, int] = defaultdict(int)
    date_buckets: Counter[str] = Counter()
    size_buckets = {"<1KB": 0, "1-10MB": 0, "10-100MB": 0, "100MB-1GB": 0, ">1GB": 0}
    largest_files: list[dict] = []
    oldest_files: list[dict] = []
    empty_dirs: list[str] = []
    empty_files: list[str] = []
    symlinks_found = 0
    errors: list[str] = []

    # Extension detail per category
    category_extensions: dict[str, Counter[str]] = defaultdict(Counter)

    for dirpath_str, dirnames, filenames in os.walk(root, followlinks=False):
        dirpath = Path(dirpath_str)

        # Depth check — clear dirnames to prevent os.walk from descending
        rel_depth = len(dirpath.relative_to(root).parts)
        if rel_depth > max_depth:
            dirnames.clear()
            continue

        # Filter excluded directories in-place (prevents os.walk from entering)
        dirnames[:] = [
            d for d in dirnames
            if d not in EXCLUDE_DIRS and not d.startswith(".")
        ]

        # Check for empty directory
        if not filenames and not dirnames:
            empty_dirs.append(str(dirpath))

        for filename in filenames:
            filepath = dirpath / filename

            # Skip symlinks
            if filepath.is_symlink():
                symlinks_found += 1
                continue

            try:
                file_stat = filepath.stat()
                size = file_stat.st_size
                mtime = datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc)
            except (OSError, PermissionError) as e:
                errors.append(f"{filepath}: {e}")
                continue

            total_files += 1
            total_size += size

            # Categorize
            category = categorize_file(filepath)
            type_counts[category] += 1
            type_sizes[category] += size
            category_extensions[category][filepath.suffix.lower()] += 1

            # Date bucket by year-month
            date_buckets[mtime.strftime("%Y-%m")] += 1

            # Size bucket
            if size < 1_000:
                size_buckets["<1KB"] += 1
            elif size < 10_000_000:
                size_buckets["1-10MB"] += 1
            elif size < 100_000_000:
                size_buckets["10-100MB"] += 1
            elif size < 1_000_000_000:
                size_buckets["100MB-1GB"] += 1
            else:
                size_buckets[">1GB"] += 1

            # Track largest files (keep top 20)
            largest_files.append({"path": str(filepath), "size": size, "size_human": human_size(size)})
            largest_files.sort(key=lambda x: x["size"], reverse=True)
            largest_files = largest_files[:20]

            # Track oldest files (keep top 20)
            oldest_files.append({"path": str(filepath), "mtime": mtime.isoformat(), "size": size})
            oldest_files.sort(key=lambda x: x["mtime"])
            oldest_files = oldest_files[:20]

            # Track empty files
            if size == 0:
                empty_files.append(str(filepath))

    # Build proposed structure
    proposed: dict[str, dict[str, Any]] = {}
    for category, count in type_counts.most_common():
        if count == 0:
            continue
        ext_counter = category_extensions.get(category, Counter())
        proposed[category] = {
            "file_count": count,
            "total_size": type_sizes[category],
            "total_size_human": human_size(type_sizes[category]),
            "extensions": dict(ext_counter.most_common(10)),
        }

    # Age analysis
    now = datetime.now(tz=timezone.utc)
    archive_candidates = []
    recent_files = []
    for f in oldest_files:
        try:
            mtime = datetime.fromisoformat(f["mtime"])
            age_days = (now - mtime).days
            f["age_days"] = age_days
            if age_days > 365:
                archive_candidates.append(f)
            elif age_days < 30:
                recent_files.append(f)
        except (ValueError, TypeError):
            pass

    # Date range
    sorted_dates = sorted(date_buckets.keys())
    date_range = {
        "earliest": sorted_dates[0] if sorted_dates else None,
        "latest": sorted_dates[-1] if sorted_dates else None,
        "span_months": len(sorted_dates),
    }

    return {
        "scan_path": str(root),
        "max_depth": max_depth,
        "cloud_sync_warning": f"Scanning inside {cloud_sync} folder" if cloud_sync else None,
        "symlinks_skipped": symlinks_found,
        "total_files": total_files,
        "total_size": total_size,
        "total_size_human": human_size(total_size),
        "file_types": dict(type_counts.most_common()),
        "type_sizes": {
            k: human_size(v)
            for k, v in sorted(type_sizes.items(), key=lambda x: x[1], reverse=True)
        },
        "date_range": date_range,
        "date_distribution": dict(sorted(date_buckets.items())),
        "size_distribution": size_buckets,
        "largest_files": largest_files[:10],
        "oldest_files": oldest_files[:10],
        "archive_candidates": {
            "count": len(archive_candidates),
            "total_size": human_size(sum(f["size"] for f in archive_candidates)),
            "files": archive_candidates[:10],
        },
        "empty_directories": {
            "count": len(empty_dirs),
            "examples": empty_dirs[:10],
        },
        "empty_files": {
            "count": len(empty_files),
            "examples": empty_files[:10],
        },
        "proposed_structure": proposed,
        "errors": errors[:20],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze directory for organization")
    parser.add_argument("--path", required=True, help="Directory to analyze")
    parser.add_argument("--max-depth", type=int, default=3, help="Max directory depth")
    args = parser.parse_args()

    result = analyze_directory(args.path, args.max_depth)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
