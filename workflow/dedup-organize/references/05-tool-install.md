# Reference: Tool Installation & Verification

## Prerequisites

- Ubuntu/Debian-based WSL
- `sudo` access
- Internet connection

## install.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

LOG="/tmp/dedup-organize-install.log"
log() { echo "[$(date +'%H:%M:%S')] $*" | tee -a "$LOG"; }

log "=== dedup-organize installer ==="

###############################################################################
# 1. ffmpeg (required by all video tools)
###############################################################################
if command -v ffmpeg &>/dev/null; then
    log "[1/6] ffmpeg: already installed ($(ffmpeg -version 2>&1 | head -1))"
else
    log "[1/6] Installing ffmpeg..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq ffmpeg
    log "  ✓ ffmpeg installed: $(ffmpeg -version 2>&1 | head -1)"
fi

###############################################################################
# 2. fclones
###############################################################################
if command -v fclones &>/dev/null; then
    log "[2/6] fclones: already installed ($(fclones --version 2>&1 | head -1))"
else
    log "[2/6] Installing fclones..."
    if command -v cargo &>/dev/null; then
        cargo install fclones 2>&1 | tee -a "$LOG"
    else
        log "  Cargo not found, downloading pre-built binary..."
        FCLONES_REL=$(curl -s https://api.github.com/repos/pkolaczk/fclones/releases/latest \
            | python3 -c "import sys,json; print(json.load(sys.stdin)['tag_name'])")
        wget -q "https://github.com/pkolaczk/fclones/releases/download/${FCLONES_REL}/fclones-linux-x64.tar.gz" \
            -O /tmp/fclones.tar.gz
        tar xzf /tmp/fclones.tar.gz -C /tmp/
        install -Dm755 /tmp/fclones "$HOME/.local/bin/fclones"
        # Ensure ~/.local/bin is in PATH
        if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
            export PATH="$HOME/.local/bin:$PATH"
            log "  ⚠ Added ~/.local/bin to PATH. Run: source ~/.bashrc"
        fi
    fi
    log "  ✓ fclones installed: $(fclones --version 2>&1 | head -1)"
fi

###############################################################################
# 3. rmlint
###############################################################################
if command -v rmlint &>/dev/null; then
    log "[3/6] rmlint: already installed"
else
    log "[3/6] Installing rmlint..."
    sudo apt-get install -y -qq rmlint
    log "  ✓ rmlint installed"
fi

###############################################################################
# 4. VDF CLI (Video Duplicate Finder)
###############################################################################
if command -v vdf-cli &>/dev/null; then
    log "[4/6] VDF CLI: already installed"
else
    log "[4/6] Installing Video Duplicate Finder CLI..."
    VDF_REL=$(curl -s https://api.github.com/repos/0x90d/videoduplicatefinder/releases/latest \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['tag_name'])")
    VDF_URL="https://github.com/0x90d/videoduplicatefinder/releases/download/${VDF_REL}/CLI-linux-x64-${VDF_REL}.tar.gz"
    wget -q "$VDF_URL" -O /tmp/vdf.tar.gz \
        || { log "  ✗ Failed to download VDF. Get it manually from https://github.com/0x90d/videoduplicatefinder/releases"; }
    if [ -f /tmp/vdf.tar.gz ]; then
        tar xzf /tmp/vdf.tar.gz -C /tmp/
        install -Dm755 /tmp/vdf-cli "$HOME/.local/bin/vdf-cli"
        log "  ✓ VDF CLI installed: $($HOME/.local/bin/vdf-cli --help 2>&1 | head -1 || echo 'installed')"
    fi
fi

###############################################################################
# 5. Python packages
###############################################################################
log "[5/6] Installing Python packages..."
python3 -m pip install --user --quiet videohash semhash 2>&1 | tee -a "$LOG"
log "  ✓ videohash: $(python3 -c 'import videohash; print(videohash.__version__)' 2>/dev/null || echo 'installed')"
log "  ✓ semhash: $(python3 -c 'import semhash; print(semhash.__version__)' 2>/dev/null || echo 'installed')"

###############################################################################
# 6. Verification
###############################################################################
log "[6/6] Verifying all tools..."
ERRORS=0

check() {
    local name="$1" cmd="${2:---help}"
    if command -v "$name" &>/dev/null; then
        log "  ✓ $name"
    else
        log "  ✗ $name NOT FOUND"
        ERRORS=$((ERRORS + 1))
    fi
}

check "ffmpeg"
check "fclones"
check "rmlint"
check "vdf-cli"

# Python packages
if python3 -c "import videohash" 2>/dev/null; then
    log "  ✓ videohash (Python)"
else
    log "  ✗ videohash (Python) NOT FOUND"
    ERRORS=$((ERRORS + 1))
fi

if python3 -c "import semhash" 2>/dev/null; then
    log "  ✓ semhash (Python)"
else
    log "  ✗ semhash (Python) NOT FOUND"
    ERRORS=$((ERRORS + 1))
fi

echo ""
if [ "$ERRORS" -eq 0 ]; then
    log "=== All tools installed and verified ==="
else
    log "=== $ERRORS tool(s) failed verification. Check $LOG ==="
    exit 1
fi
```

## Post-Install

Verify PATH includes `~/.local/bin`:
```bash
echo "$PATH" | tr ':' '\n' | grep -q ".local/bin" || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Docker Alternative (for VDF Web UI)

```bash
docker run -d \
  --name vdf \
  -p 8080:8080 \
  -v /mnt/c/Videos:/data:ro \
  ghcr.io/0x90d/videoduplicatefinder:latest
# Then open http://localhost:8080
```
