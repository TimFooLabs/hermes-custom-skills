# Reference: File Organization

## Analysis

### Directory Overview

```bash
# File count and size
find /target -type f | wc -l
du -sh /target

# File type breakdown
find /target -type f | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20

# Size distribution
find /target -type f -printf '%s\n' | sort -n | awk '
  BEGIN{bin[0]=0; bin[1]=0; bin[2]=0; bin[3]=0; bin[4]=0}
  {if($1<1000000) bin[0]++;
   else if($1<10000000) bin[1]++;
   else if($1<100000000) bin[2]++;
   else if($1<1000000000) bin[3]++;
   else bin[4]++}
  END{print "<1MB:", bin[0]; print "1-10MB:", bin[1]; print "10-100MB:", bin[2]; print "100MB-1GB:", bin[3]; print ">1GB:", bin[4]}'

# Age distribution
find /target -type f -mtime +365 | wc -l   # older than 1 year
find /target -type f -mtime +180 | wc -l   # older than 6 months
find /target -type f -mtime +90 | wc -l    # older than 3 months

# Largest files
find /target -type f -printf '%s %p\n' | sort -rn | head -20

# Empty directories
find /target -type d -empty

# Empty files
find /target -type f -empty
```

### WSL-Specific: Windows Host Paths

When scanning `/mnt/c/`:
```bash
# Warn user about performance
echo "Note: Scanning Windows filesystem from WSL. Hashing will be slower."

# Check for case-insensitive collisions
find /mnt/c/Users -type f -name "*.MP4" | head -5
# NTFS is case-insensitive — treat .MP4 and .mp4 as same extension
```

## Organization Patterns

### By File Type

```
target/
├── Documents/       (.pdf, .docx, .txt, .md, .rtf, .odt)
├── Spreadsheets/    (.xlsx, .csv, .ods)
├── Presentations/   (.pptx, .key, .odp)
├── Images/          (.jpg, .png, .gif, .svg, .webp, .tiff)
├── Videos/          (.mp4, .mkv, .avi, .mov, .wmv, .flv, .webm)
├── Audio/           (.mp3, .wav, .flac, .aac, .ogg, .m4a)
├── Archives/        (.zip, .tar, .gz, .bz2, .7z, .rar, .dmg)
├── Code/            (.py, .js, .ts, .java, .go, .rs, .rb, .sh)
├── Data/            (.json, .xml, .yaml, .toml, .sql, .db)
├── Installers/      (.exe, .msi, .deb, .rpm, .appimage)
└── Other/
```

### By Date

```
target/
├── 2026/
│   ├── 01-January/
│   ├── 02-February/
│   └── ...
├── 2025/
│   └── ...
├── 2024/
│   └── ...
└── Archive/         (everything older than 2 years)
```

### By Project/Purpose

```
target/
├── Work/
│   ├── Projects/
│   ├── Documents/
│   └── Archive/
├── Personal/
│   ├── Photos/
│   ├── Videos/
│   └── Documents/
└── Downloads/
    ├── To-Sort/
    └── Archive/
```

## Quality Heuristics for "Which to Keep"

### Media Files (video/audio)

Use ffprobe to extract quality metrics:

```bash
ffprobe -v quiet -print_format json -show_format -show_streams /path/to/file.mp4
```

Ranking criteria (higher is better):
1. **Resolution** (width × height)
2. **Bitrate** (format.bit_rate or stream.bit_rate)
3. **Codec modernity** (H.265 > H.264 > MPEG-4 > XviD)
4. **Duration** (longer = more complete)
5. **File size** (larger at same resolution = less compressed)

```python
def rank_video_quality(path: str) -> dict:
    """Extract quality metrics from a video file using ffprobe."""
    import subprocess, json
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", path],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(result.stdout)
    except Exception:
        return {"path": path, "score": 0, "error": True}

    video_stream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
        {}
    )
    fmt = data.get("format", {})

    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    bitrate = int(fmt.get("bit_rate", 0) or video_stream.get("bit_rate", 0))
    duration = float(fmt.get("duration", 0))
    codec = video_stream.get("codec_name", "")
    size = int(fmt.get("size", 0))

    # Codec score
    codec_scores = {"hevc": 100, "h265": 100, "h264": 80, "avc": 80,
                    "mpeg4": 50, "xvid": 40, "mpeg2": 30}
    codec_score = codec_scores.get(codec.lower(), 50)

    # Composite score (weighted)
    score = (
        (width * height) * 0.3 +           # Resolution
        (bitrate / 1_000_000) * 25 +        # Bitrate (Mbps)
        codec_score * 0.2 +                  # Codec
        (duration / 3600) * 10 +             # Duration (hours)
        (size / 1_000_000_000) * 5           # Size (GB)
    )

    return {
        "path": path,
        "score": round(score, 2),
        "width": width,
        "height": height,
        "bitrate_kbps": bitrate // 1000,
        "codec": codec,
        "duration_s": round(duration),
        "size_bytes": size,
    }
```

### Documents

Priority order (keep higher):
1. **Editable originals** (.docx, .xlsx, .pptx) over exports (.pdf)
2. **Richer metadata** (author, creation date, revision history)
3. **Larger file** (more content, embedded images)
4. **Newer modification date** (tiebreaker)

### General Files

1. **Shorter path** (closer to root = more "organized")
2. **Meaningful name** over `IMG_20250315_001.jpg`
3. **Newer mtime** (tiebreaker)

## Execution

### Step 1: Create directories

```bash
mkdir -p "/target/Documents" "/target/Videos" "/target/Images" "/target/Archives"
```

### Step 2: Move files (with logging)

```bash
# Log every move for undo
LOG="/tmp/dedup-organize-moves.log"
echo "# $(date -Iseconds)" > "$LOG"

# Move with conflict handling
safe_move() {
  local src="$1" dst="$2"
  if [ -e "$dst" ]; then
    base="${dst%.*}"
    ext="${dst##*.}"
    counter=1
    while [ -e "${base}_${counter}.${ext}" ]; do
      counter=$((counter + 1))
    done
    dst="${base}_${counter}.${ext}"
  fi
  mv "$src" "$dst"
  echo "mv '$src' '$dst'" >> "$LOG"
  echo "  Moved: $src → $dst"
}

# Example: move all PDFs
find /target -maxdepth 1 -type f -iname "*.pdf" | while read f; do
  safe_move "$f" "/target/Documents/$(basename "$f")"
done
```

### Step 3: Cleanup empty directories

```bash
# Remove empty directories (bottom-up)
find /target -type d -empty -delete
```

### Step 4: Generate summary

```
Organization Complete
  Created: 8 directories
  Moved: 347 files
  Archived: 89 files (12.3 GB)
  Removed: 156 empty directories
  Undo log: ~/.hermes/logs/dedup-organize/run-<timestamp>/manifest.json
```
