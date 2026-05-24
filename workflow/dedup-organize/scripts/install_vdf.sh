#!/usr/bin/env bash
# install_vdf.sh — Install VDF CLI
# Fixes: uses correct GitHub release tag format (3.0.x) and filename pattern

set -euo pipefail

echo "Fetching latest VDF release..."
VDF_REL=$(curl -s --connect-timeout 10 https://api.github.com/repos/0x90d/videoduplicatefinder/releases/latest | python3 -c "import sys,json; print(json.load(sys.stdin)['tag_name'])" 2>/dev/null)

if [[ -z "$VDF_REL" ]]; then
    echo "ERROR: Could not fetch latest release from GitHub API."
    echo "Download manually from: https://github.com/0x90d/videoduplicatefinder/releases"
    echo "Look for: CLI-linux-x64.tar.gz"
    exit 1
fi

echo "Latest release: $VDF_REL"
VDF_URL="https://github.com/0x90d/videoduplicatefinder/releases/download/${VDF_REL}/CLI-linux-x64.tar.gz"
echo "Downloading: $VDF_URL"

curl -L --connect-timeout 15 -o /tmp/vdf.tar.gz "$VDF_URL"

echo "Extracting..."
cd /tmp
tar xzf vdf.tar.gz

echo "Installing to ~/.local/lib/vdf-cli/..."
mkdir -p "$HOME/.local/lib/vdf-cli"
cp -r /tmp/outputCLI/* "$HOME/.local/lib/vdf-cli/"
ln -sf "$HOME/.local/lib/vdf-cli/vdf-cli" "$HOME/.local/bin/vdf-cli"

echo "VDF CLI installed: $HOME/.local/bin/vdf-cli"
"$HOME/.local/bin/vdf-cli" --help 2>&1 | head -3
echo "Done."
