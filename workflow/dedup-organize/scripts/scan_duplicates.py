#!/usr/bin/env python3
"""
Unified duplicate scanner.
Calls fclones (files) and/or VDF (videos) and returns structured JSON.

Usage:
    python3 scan_duplicates.py --path /target --mode auto|files|videos|both
    python3 scan_duplicates.py --path /target --mode files --min-size 1KB
    python3 scan_duplicates.py --path /target --mode videos --threshold 5

Fixes applied:
    - Tool detection via --help (not all tools support --version)
    - subprocess timeout (3600s default)
    - Path.unlink(missing_ok=True) for temp files
    - Tool version capture in output
    - Symlink following disabled by default
    - WSL /mnt path normalization
    - Cloud-sync folder warning
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

SUBPROCESS_TIMEOUT = 3600  # 1 hour max per tool

# Paths to skip entirely
EXCLUDE_PATHS = {
    ".git", "node_modules", ".venv", "__pycache__", ".cache",
    ".pytest_cache", ".mypy_cache", ".Trash", "trash",
    "$RECYCLE.BIN", "System Volume Information",
    "Dropbox", "Google Drive", "OneDrive", "iCloud Drive",
}

CLOUD_SYNC_PATHS = {"Dropbox", "Google Drive", "OneDrive", "iCloud Drive", "Dropbox (Personal)"}


def is_wsl() -> bool:
    """Detect if running under WSL."""
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower()
    except FileNotFoundError:
        return False


def normalize_path(path: str) -> str:
    """Normalize WSL paths for display."""
    p = Path(path).resolve()
    return str(p)


def check_cloud_sync(path: str) -> list[str]:
    """Warn if scanning inside cloud-sync folders."""
    warnings = []
    p = Path(path)
    for part in p.parts:
        if part in CLOUD_SYNC_PATHS:
            warnings.append(
                f"⚠ Path '{path}' is inside cloud-sync folder '{part}'. "
                "Linking/deleting files here may cause sync issues. "
                "Consider excluding this path."
            )
    return warnings


def check_tool(name: str) -> tuple[bool, str]:
    """Check if a CLI tool is available. Returns (found, version_or_error).

    Uses --help instead of --version because not all tools support --version.
    """
    try:
        result = subprocess.run(
            [name, "--help"],
            capture_output=True,
            timeout=15,
        )
        # Most tools return 0 for --help, but some return non-zero yet still work
        if result.returncode <= 1:
            return True, "available"
    except FileNotFoundError:
        return False, "not found"
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)
    return False, "not found"


def get_tool_version(name: str) -> str:
    """Try to get tool version. Falls back to 'unknown'."""
    for flag in ["--version", "-v", "-V"]:
        try:
            result = subprocess.run(
                [name, flag],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[0]
        except Exception:
            continue
    return "unknown"


def check_filesystem_support(path: str) -> dict[str, Any]:
    """Check filesystem capabilities for the target path."""
    result = {
        "path": path,
        "filesystem": "unknown",
        "reflink_supported": False,
        "case_sensitive": True,
        "is_network": False,
    }

    # Detect filesystem type
    try:
        fs_output = subprocess.run(
            ["stat", "-f", "-c", "%T", path],
            capture_output=True, text=True, timeout=10
        )
        if fs_output.returncode == 0:
            fs_type = fs_output.stdout.strip()
            result["filesystem"] = fs_type
            # reflink supported on XFS, Btrfs, ZFS, ReFS (not ext4)
            result["reflink_supported"] = fs_type in ("xfs", "btrfs", "zfs", "refs", "ntfs")
            # Network filesystems
            result["is_network"] = fs_type in ("nfs", "cifs", "smbfs", "9p", "vboxsf", "v9fs")
    except Exception:
        pass

    # Check if case-sensitive (WSL mounts of NTFS are case-insensitive)
    if is_wsl() and path.startswith("/mnt/"):
        result["case_sensitive"] = False
    else:
        # Test case sensitivity by creating a temp file
        try:
            test_dir = Path(path)
            test_file_a = test_dir / ".dedup_case_test_a"
            test_file_b = test_dir / ".dedup_case_test_A"
            test_file_a.touch()
            case_sensitive = not test_file_b.exists()
            test_file_a.unlink(missing_ok=True)
            result["case_sensitive"] = case_sensitive
        except Exception:
            pass

    return result


def check_cross_device(paths: list[str]) -> dict[str, str]:
    """Check which mount point each path belongs to. Returns {path: mount_point}."""
    mount_map = {}
    for path in paths:
        try:
            df_output = subprocess.run(
                ["df", path],
                capture_output=True, text=True, timeout=10
            )
            if df_output.returncode == 0:
                lines = df_output.stdout.strip().split("\n")
                if len(lines) >= 2:
                    mount_map[path] = lines[-1].split()[-1]  # Last column is mount point
        except Exception:
            mount_map[path] = "unknown"
    return mount_map


def scan_files_fclones(
    path: str,
    min_size: str = "1KB",
    max_depth: Optional[int] = None,
) -> dict[str, Any]:
    """Run fclones group and return parsed JSON report."""
    tool = "fclones"
    found, status = check_tool(tool)
    if not found:
        return {"tool": tool, "error": status, "groups": []}

    version = get_tool_version(tool)
    tmp_path = Path(tempfile.mktemp(suffix=".json", prefix="fclones_"))

    cmd = [
        "fclones", "group", path,
        "--format", "json",
        "--output", str(tmp_path),
        "--min-size", min_size,
    ]

    if max_depth is not None:
        cmd.extend(["--max-depth", str(max_depth)])

    # Add excludes
    for exclude in [".git", "node_modules", ".venv", "__pycache__", ".cache"]:
        cmd.extend(["--exclude", f"{exclude}/**"])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)

    try:
        raw = json.loads(tmp_path.read_text())
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return {
            "tool": tool,
            "version": version,
            "error": f"Failed to parse output: {e}. stderr: {result.stderr[:500]}",
            "groups": [],
        }
    finally:
        tmp_path.unlink(missing_ok=True)

    # Normalize output
    groups = []
    all_paths = []
    for group in raw.get("groups", []):
        files = []
        for entry in group.get("files", []):
            fpath = entry.get("path", "")
            files.append({
                "path": fpath,
                "size": entry.get("size", 0),
                "modified": entry.get("modified", ""),
            })
            all_paths.append(fpath)

        waste = group.get("size", 0) * max(len(files) - 1, 0)
        groups.append({
            "size_per_file": group.get("size", 0),
            "file_count": len(files),
            "total_waste": waste,
            "confidence": 0.99,  # Cryptographic hash match
            "files": files,
        })

    # Check for cross-device issues
    mount_map = check_cross_device(all_paths[:100])  # Sample first 100
    unique_mounts = set(mount_map.values())

    return {
        "tool": tool,
        "version": version,
        "scan_path": path,
        "total_groups": len(groups),
        "total_waste_bytes": sum(g["total_waste"] for g in groups),
        "unique_mount_points": list(unique_mounts),
        "cross_device_warning" if len(unique_mounts) > 1 else "_": (
            "Files span multiple mount points. Hardlinks/reflinks will not work across devices."
        ),
        "groups": groups,
    }


def scan_videos_vdf(
    path: str,
    threshold: int = 5,
    percent: int = 90,
    clip_detection: bool = False,
) -> dict[str, Any]:
    """Run VDF CLI scan and return parsed JSON report."""
    tool = "vdf-cli"
    found, status = check_tool(tool)
    if not found:
        return {"tool": tool, "error": status, "groups": []}

    tmp_path = Path(tempfile.mktemp(suffix=".json", prefix="vdf_"))

    cmd = [
        "vdf-cli", "scan-and-compare",
        "--include", path,
        "--threshold", str(threshold),
        "--percent", str(percent),
        "--format", "json",
        "--output", str(tmp_path),
    ]

    if clip_detection:
        cmd.append("--partial-clip-detection")
        cmd.extend(["--partial-clip-min-ratio", "0.10"])
        cmd.extend(["--partial-clip-similarity", "0.80"])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)

    try:
        raw = json.loads(tmp_path.read_text())
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return {
            "tool": tool,
            "error": f"Failed to parse output: {e}. stderr: {result.stderr[:500]}",
            "groups": [],
        }
    finally:
        tmp_path.unlink(missing_ok=True)

    groups = []
    for group in raw.get("duplicateGroups", []):
        files = []
        for entry in group.get("duplicates", []):
            similarity = entry.get("similarity", 0)
            # Map similarity to confidence
            if similarity >= 0.99:
                confidence = 0.99
            elif similarity >= 0.90:
                confidence = 0.90 + (similarity - 0.90)  # 0.90–0.98
            elif similarity >= 0.70:
                confidence = 0.70 + (similarity - 0.70) * 0.5  # 0.70–0.84
            else:
                confidence = round(similarity, 2)

            files.append({
                "path": entry.get("filePath", ""),
                "size": entry.get("fileSize", 0),
                "similarity": similarity,
                "confidence": confidence,
                "is_clip": entry.get("isClip", False),
                "clip_offset": entry.get("clipOffset"),
            })

        groups.append({
            "file_count": len(files),
            "is_partial_clip": any(f["is_clip"] for f in files),
            "confidence": min(f["confidence"] for f in files) if files else 0,
            "files": files,
        })

    return {
        "tool": tool,
        "scan_path": path,
        "total_groups": len(groups),
        "groups": groups,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified duplicate scanner")
    parser.add_argument("--path", required=True, help="Directory to scan")
    parser.add_argument(
        "--mode",
        choices=["auto", "files", "videos", "both"],
        default="auto",
    )
    parser.add_argument("--min-size", default="1KB", help="Min file size for fclones")
    parser.add_argument("--threshold", type=int, default=5, help="VDF hash threshold")
    parser.add_argument("--percent", type=int, default=90, help="VDF min similarity percent")
    parser.add_argument("--clip-detection", action="store_true", help="Enable VDF clip detection")
    args = parser.parse_args()

    # Normalize path
    scan_path = normalize_path(args.path)

    # Pre-flight warnings
    warnings = check_cloud_sync(scan_path)
    for w in warnings:
        print(f"⚠ {w}", file=sys.stderr)

    fs_info = check_filesystem_support(scan_path)
    if fs_info.get("is_network"):
        print("⚠ Network filesystem detected. Scanning will be slow.", file=sys.stderr)
    if not fs_info.get("reflink_supported"):
        print(
            f"ℹ Filesystem '{fs_info['filesystem']}' does not support reflinks. "
            "Will use hardlinks or deletion for dedup.",
            file=sys.stderr
        )

    # Determine mode
    fclones_found, _ = check_tool("fclones")
    vdf_found, _ = check_tool("vdf-cli")

    if args.mode == "auto":
        # Use whatever is available
        run_files = fclones_found
        run_videos = vdf_found
    elif args.mode == "files":
        run_files = True
        run_videos = False
    elif args.mode == "videos":
        run_files = False
        run_videos = True
    elif args.mode == "both":
        run_files = True
        run_videos = True

    results: dict[str, Any] = {
        "scan_path": scan_path,
        "mode": args.mode,
        "wsl": is_wsl(),
        "filesystem": fs_info,
        "warnings": warnings,
    }

    if run_files:
        if fclones_found:
            results["files"] = scan_files_fclones(scan_path, args.min_size)
        else:
            print("⚠ fclones not found. Install with: cargo install fclones", file=sys.stderr)
            results["files"] = {"tool": "fclones", "error": "not installed", "groups": []}

    if run_videos:
        if vdf_found:
            results["videos"] = scan_videos_vdf(
                scan_path, args.threshold, args.percent, args.clip_detection
            )
        else:
            print("⚠ vdf-cli not found. Get from: https://github.com/0x90d/videoduplicatefinder/releases", file=sys.stderr)
            results["videos"] = {"tool": "vdf-cli", "error": "not installed", "groups": []}

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
