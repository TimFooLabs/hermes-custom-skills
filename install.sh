#!/usr/bin/env bash
# Hermes Custom Skills — Bootstrap Installer
# Usage:
#   bash install.sh              # install skills + quick commands
#   bash install.sh --skills-only   # install skills only
#   bash install.sh --config-only   # install quick commands config only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$HOME/.hermes/skills/software-development"
CONFIG_FILE="$HOME/.hermes/config.yaml"
MODE="${1:-all}"

echo "╭────────────────────────────────────────────╮"
echo "│ Hermes Custom Skills — installer           │"
echo "╰────────────────────────────────────────────╯"

install_skills() {
    echo ""
    echo "▶ Installing skills..."
    mkdir -p "$SKILLS_DIR"

    for skill in double-check handoff; do
        src="$SCRIPT_DIR/software-development/$skill"
        dest="$SKILLS_DIR/$skill"

        if [ -d "$dest" ]; then
            echo "  ✓ $skill already exists — updating"
            rm -rf "$dest"
        fi

        cp -r "$src" "$dest"
        echo "  ✓ Installed $skill → $dest"
    done
}

install_config() {
    echo ""
    echo "▶ Registering quick commands in config.yaml..."

    if [ ! -f "$CONFIG_FILE" ]; then
        echo "  ✗ config.yaml not found at $CONFIG_FILE"
        exit 1
    fi

    # Check if already registered
    if grep -q "^  dc:" "$CONFIG_FILE" 2>/dev/null; then
        echo "  ✓ Quick commands already registered — skipping"
        return
    fi

    # Check if quick_commands key exists
    if grep -q "^quick_commands:" "$CONFIG_FILE"; then
        # Append to existing block
        # Find the line number of quick_commands
        line=$(grep -n "^quick_commands:" "$CONFIG_FILE" | head -1 | cut -d: -f1)
        # Check if it's empty: quick_commands: {}
        next_line=$((line + 1))
        if sed -n "${line}p" "$CONFIG_FILE" | grep -q 'quick_commands: {}'; then
            # Replace the empty block
            sed -i 's/^quick_commands: {}/quick_commands:\n  dc:\n    type: exec\n    command: cat ~\/.hermes\/skills\/software-development\/double-check\/SKILL.md\n  handoff:\n    type: exec\n    command: cat ~\/.hermes\/skills\/software-development\/handoff\/SKILL.md/' "$CONFIG_FILE"
        else
            # Append after the quick_commands: line
            sed -i "${line}a\\  dc:\\n    type: exec\\n    command: cat ~/.hermes/skills/software-development/double-check/SKILL.md\\n  handoff:\\n    type: exec\\n    command: cat ~/.hermes/skills/software-development/handoff/SKILL.md" "$CONFIG_FILE"
        fi
    else
        # Add quick_commands block at end of file
        cat >> "$CONFIG_FILE" << 'EOF'

quick_commands:
  dc:
    type: exec
    command: cat ~/.hermes/skills/software-development/double-check/SKILL.md
  handoff:
    type: exec
    command: cat ~/.hermes/skills/software-development/handoff/SKILL.md
EOF
    fi

    echo "  ✓ Registered /dc and /handoff quick commands"
}

# Main
case "$MODE" in
    --skills-only)
        install_skills
        ;;
    --config-only)
        install_config
        ;;
    all)
        install_skills
        install_config
        ;;
    *)
        echo "Usage: bash install.sh [--skills-only|--config-only]"
        exit 1
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Install complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Start a new session (/reset) to activate."
echo ""
echo "Usage:"
echo "  /skill double-check    — verify work before marking done"
echo "  /dc                    — shorthand"
echo "  /skill handoff [msg]   — generate handoff prompt"
echo "  /handoff [msg]         — shorthand"
