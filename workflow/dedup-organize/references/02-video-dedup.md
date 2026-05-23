# Reference: Video Duplicate Detection

## VDF CLI (primary)

Cross-platform C#. Finds videos with different resolution, frame rate, watermarks. Also detects partial clips via audio fingerprinting.

### Install

Download latest CLI-linux-x64 release from https://github.com/0x90d/videoduplicatefinder/releases

```bash
# Auto-install script
VDF_REL=$(curl -s https://api.github.com/repos/0x90d/videoduplicatefinder/releases/latest | python3 -c "import sys,json; print(json.load(sys.stdin)['tag_name'])")
wget "https://github.com/0x90d/videoduplicatefinder/releases/download/${VDF_REL}/CLI-linux-x64-${VDF_REL}.tar.gz" -O /tmp/vdf.tar.gz
tar xzf /tmp/vdf.tar.gz -C /tmp/
install -Dm755 /tmp/vdf-cli "$HOME/.local/bin/vdf-cli"
```

Requires: `ffmpeg` + `ffprobe` on PATH.

### Phase 1: Visual Similarity Scan

```bash
vdf-cli scan-and-compare \
  --include /target/videos \
  --threshold 5 \
  --percent 90 \
  --format json \
  --output /tmp/vdf-report.json
```

Flags:
- `--threshold N` — hash difference (0=identical, higher=more lenient). Default 5.
- `--percent N` — minimum similarity % to report. Default 90.
- `--parallelism N` — threads. Default 1.
- `--include-images` — also scan images.

### Phase 2: Partial Clip Detection

```bash
vdf-cli scan-and-compare \
  --include /target/videos \
  --partial-clip-detection \
  --partial-clip-min-ratio 0.10 \
  --partial-clip-min-ratio 0.80
```

**What it finds:** Shorter clips extracted from longer videos (e.g., ripped scenes, saved clips). Uses audio fingerprinting (Chromaprint-style), NOT visual comparison. Works even if the clip has no visual overlap with the original.

**Settings:**
- `--partial-clip-min-ratio 0.10` — clip must be ≥ 10% of source duration
- `--partial-clip-similarity 0.80` — minimum audio similarity (80%)

**Note:** Videos without audio tracks are skipped in this phase.

### Review

Parse `/tmp/vdf-report.json`:
- `duplicateGroups[].duplicates[].filePath` — file path
- `duplicateGroups[].duplicates[].similarity` — similarity score
- `duplicateGroups[].duplicates[].isClip` — true if partial clip
- `duplicateGroups[].duplicates[].clipOffset` — start time in source

### Apply (after confirmation)

```bash
# Always dry-run first
vdf-cli scan-and-compare \
  --include /target/videos \
  --action lowest-quality \
  --dry-run

# Move to trash
vdf-cli scan-and-compare \
  --include /target/videos \
  --action lowest-quality \
  --delete

# Permanent delete (use with care)
vdf-cli scan-and-compare \
  --include /target/videos \
  --action lowest-quality \
  --delete-permanent
```

**Deletion strategies:**
| Strategy | What it keeps |
|----------|--------------|
| `lowest-quality` | Highest bitrate/resolution |
| `smallest-file` | Largest file |
| `shortest-duration` | Longest duration |
| `worst-resolution` | Highest resolution |
| `100-percent-only` | Only acts on 100% identical groups |

**Recommend `lowest-quality`** — it uses ffprobe internally to select the best version.

## videohash (lightweight fallback)

Python library. Perceptual video hashing. Good for scripted pipelines.

### Install

```bash
python3 -m pip install --user videohash
```

Requires: `ffmpeg` installed.

### Usage

```python
from videohash import VideoHash
import os

def scan_video_duplicates(directory: str, threshold: int = 5) -> dict:
    """Scan directory for near-duplicate videos.
    Returns {hash: [paths]} for files within Hamming distance threshold.
    """
    hashes = {}
    video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'}

    for root, _, files in os.walk(directory):
        for f in files:
            if os.path.splitext(f)[1].lower() not in video_exts:
                continue
            path = os.path.join(root, f)
            try:
                vh = VideoHash(path=path)
                hashes.setdefault(vh.hash, []).append(path)
            except Exception as e:
                print(f"Error: {path}: {e}")

    # Find exact perceptual matches
    return {k: v for k, v in hashes.items() if len(v) > 1}

# Example
dups = scan_video_duplicates("/mnt/c/Videos")
for hash_val, paths in dups.items():
    print(f"Match group (confidence: perceptual):")
    for p in paths:
        print(f"  {p}")
```

**Resilient to:** resizing, transcoding, watermarks, color changes, frame rate changes, cropping, black bars.

**Limitations:**
- Cannot detect clips within longer videos
- Fails on reversed videos or rotation > 10°
- 64-bit hash → possible (rare) false positives at low thresholds

### Hamming Distance Interpretation

| Distance | Confidence |
|----------|-----------|
| 0 | Identical (perceptual) |
| 1–5 | Near-duplicate (high confidence) |
| 6–15 | Similar (review needed) |
| > 15 | Probably different |

## Presentation Format

```
Video Duplicate Group 1 of 8  (confidence: 0.95, visual similarity)
  ✓ KEEP  /mnt/c/Videos/movie_1080p.mkv    (1920x1080, 8000 kbps, H.265)
  ✕ RM    /mnt/c/Videos/movie_720p.mkv      (1280x720, 2000 kbps, H.264)
  Similarity: 95% | Duration match: 2:01:33

Video Duplicate Group 2 of 8  (confidence: 0.88, partial clip detected!)
  SOURCE  /mnt/c/Videos/full_movie.mkv       (2:30:00)
  CLIP    /mnt/c/Videos/favorite_scene.mkv   (0:05:12, starts at 1:15:30)
  Audio similarity: 88%

Options: [k]eep shown / [s]elect manually / [a]pply all / [s]kip group
```
