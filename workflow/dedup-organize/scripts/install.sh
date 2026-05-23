#!/usr/bin/env bash
# install.sh — Install all dependencies for dedup-organize skill
# Usage: bash install.sh [--verify-only]

set -euo pipefail

LOG="/tmp/dedup-organize-install.log"
VERIFY_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --verify-only) VERIFY_ONLY=true ;;
    esac
done

log() { echo "[$(date +'%H:%M:%S')] $*" | tee -a "$LOG"; }
ok()  { echo "  ✓ $1"; }
fail(){ echo "  ✗ $1"; }

if $VERIFY_ONLY; then
    log "=== Verification mode ==="
else
    log "=== dedup-organize installer ==="
fi

ERRORS=0

###############################################################################
# Helper: verify a CLI tool exists
###############################################################################
verify_cli() {
    local name="$1"
    if command -v "$name" &>/dev/null; then
        ok "$name ($(command -v "$name"))"
    else
        fail "$name NOT FOUND"
        ERRORS=$((ERRORS + 1))
    fi
}

verify_python() {
    local name="$1"
    if python3 -c "import $name" 2>/dev/null; then
        ok "$name (Python)"
    else
        fail "$name (Python) NOT FOUND"
        ERRORS=$((ERRORS + 1))
    fi
}

###############################################################################
# 1. ffmpeg (required by all video tools)
###############################################################################
if ! $VERIFY_ONLY; then
    if command -v ffmpeg &>/dev/null; then
        log "[1/6] ffmpeg: already installed ($(ffmpeg -version 2>&1 | head -1))"
    else
        log "[1/6] Installing ffmpeg..."
        sudo apt-get update -qq
        sudo apt-get install -y -qq ffmpeg
    fi
fi
verify_cli "ffmpeg"

###############################################################################
# 2. fclones
###############################################################################
if ! $VERIFY_ONLY; then
    if command -v fclones &>/dev/null; then
        log "[2/6] fclones: already installed ($(fclones --version 2>&1 | head -1))"
    else
        log "[2/6] Installing fclones..."
        if command -v cargo &>/dev/null; then
            cargo install fclones 2>&1 | tee -a "$LOG"
        else
            log "  Cargo not found, downloading pre-built binary..."
            FCLONES_REL=$(curl -s https://api.github.com/repos/pkolaczk/fclones/releases/latest \
                | python3 -c "import sys,json; print(json.load(sys.stdin)['tag_name'])" 2>/dev/null)
            if [[ -n "$FCLONES_REL" ]]; then
                wget -q "https://github.com/pkolaczk/fclones/releases/download/${FCLONES_REL}/fclones-amd64-linux.tar.gz" \
                    -O /tmp/fclones.tar.gz 2>&1 | tee -a "$LOG" || true
                if [[ -f /tmp/fclones.tar.gz ]]; then
                    tar xzf /tmp/fclones.tar.gz -C /tmp/
                    install -Dm755 /tmp/fclones "$HOME/.local/bin/fclones"
                else
                    fail "  Could not download fclones. Install manually from https://github.com/pkolaczk/fclones"
                fi
            else
                fail "  Could not determine latest fclones release"
            fi
        fi
        # Ensure ~/.local/bin is in PATH for this session
        if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            export PATH="$HOME/.local/bin:$PATH"
            # Also add to shell profile if not already there
            if ! grep -q '.local/bin' "$HOME/.bashrc" 2>/dev/null; then
                echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
                log "  ⚠ Added ~/.local/bin to PATH in ~/.bashrc"
            fi
        fi
    fi
fi
verify_cli "fclones"

###############################################################################
# 3. rmlint
###############################################################################
if ! $VERIFY_ONLY; then
    if command -v rmlint &>/dev/null; then
        log "[3/6] rmlint: already installed"
    else
        log "[3/6] Installing rmlint..."
        sudo apt-get install -y -qq rmlint
    fi
fi
verify_cli "rmlint"

###############################################################################
# 4. VDF CLI (Video Duplicate Finder)
###############################################################################
if ! $VERIFY_ONLY; then
    if command -v vdf-cli &>/dev/null; then
        log "[4/6] VDF CLI: already installed"
    else
        log "[4/6] Installing Video Duplicate Finder CLI..."
        VDF_REL=$(curl -s https://api.github.com/repos/0x90d/videoduplicatefinder/releases/latest \
            | python3 -c "import sys,json; print(json.load(sys.stdin)['tag_name'])" 2>/dev/null)
        if [[ -n "$VDF_REL" ]]; then
            VDF_URL="https://github.com/0x90d/videoduplicatefinder/releases/download/${VDF_REL}/CLI-linux-x64-${VDF_REL}.tar.gz"
            wget -q "$VDF_URL" -O /tmp/vdf.tar.gz 2>&1 | tee -a "$LOG" || true
            if [[ -f /tmp/vdf.tar.gz ]]; then
                tar xzf /tmp/vdf.tar.gz -C /tmp/
                install -Dm755 /tmp/vdf-cli "$HOME/.local/bin/vdf-cli"
                ok "VDF CLI installed"
            else
                fail "Could not download VDF. Get manually from https://github.com/0x90d/videoduplicatefinder/releases"
            fi
        else
            fail "Could not determine latest VDF release"
        fi
    fi
fi
verify_cli "vdf-cli"

###############################################################################
# 5. Python packages
###############################################################################
if ! $VERIFY_ONLY; then
    log "[5/6] Installing Python packages..."
    python3 -m pip install --user --quiet videohash semhash 2>&1 | tee -a "$LOG" || {
        log "  ⚠ pip install failed. Trying with --break-system-packages..."
        python3 -m pip install --user --quiet --break-system-packages videohash semhash 2>&1 | tee -a "$LOG"
    }
fi
verify_python "videohash"
verify_python "semhash"

###############################################################################
# 6. Summary
###############################################################################
log "[6/6] Verification complete."
echo ""
if [ "$ERRORS" -eq 0 ]; then
    ok "All tools installed and verified."
    ok "Log: $LOG"
else
    fail "$ERRORS tool(s) failed verification."
    fail "Check log: $LOG"
    exit 1
fi
