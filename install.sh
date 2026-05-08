#!/usr/bin/env bash
# Hermes Custom Skills — Bootstrap Installer
# Usage:
#   bash install.sh                # install skills + quick commands
#   bash install.sh --skills-only  # install skills only
#   bash install.sh --config-only  # install quick commands config only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$HOME/.hermes/skills/software-development"
CONFIG_FILE="$HOME/.hermes/config.yaml"
TMP_DIR=""

cleanup() {
    if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
        rm -rf "$TMP_DIR"
    fi
}
trap cleanup EXIT

echo "╭────────────────────────────────────────────╮"
echo "│ Hermes Custom Skills — installer           │"
echo "╰────────────────────────────────────────────╯"

# ── Preflight ─────────────────────────────────

install_skills() {
    echo ""
    echo "▶ Installing skills..."
    mkdir -p "$SKILLS_DIR"

    for skill in double-check handoff; do
        src="$SCRIPT_DIR/software-development/$skill/SKILL.md"
        dest="$SKILLS_DIR/$skill"

        if [ ! -f "$src" ]; then
            echo "  ✗ Source not found: $src"
            exit 1
        fi

        if [ -d "$dest" ]; then
            echo "  ✓ $skill already exists — updating"
            rm -rf "$dest"
        fi

        mkdir -p "$dest"
        cp "$src" "$dest/SKILL.md"
        echo "  ✓ Installed $skill → $dest"
    done

    # Verify
    for skill in double-check handoff; do
        if [ -f "$SKILLS_DIR/$skill/SKILL.md" ]; then
            echo "  ✓ Verified: $skill/SKILL.md"
        else
            echo "  ✗ Verification failed: $skill/SKILL.md not found"
            exit 1
        fi
    done
}

install_config() {
    echo ""
    echo "▶ Registering quick commands in config.yaml..."

    if [ ! -f "$CONFIG_FILE" ]; then
        echo "  ✗ config.yaml not found at $CONFIG_FILE"
        exit 1
    fi

    # Check if already registered (handles any indentation)
    if grep -qE "^\s+dc:" "$CONFIG_FILE" 2>/dev/null; then
        echo "  ✓ Quick commands already registered — skipping"
        return
    fi

    # Backup config before modifying
    cp "$CONFIG_FILE" "$CONFIG_FILE.bak"
    echo "  ✓ Backed up config.yaml → config.yaml.bak"

    # Build the YAML block via a temp file (no sed escaping nightmares)
    TMP_DIR=$(mktemp -d)
    cat > "$TMP_DIR/quick_commands_block.yaml" << 'YAMLEOF'

quick_commands:
  dc:
    type: exec
    command: cat ~/.hermes/skills/software-development/double-check/SKILL.md
  handoff:
    type: exec
    command: cat ~/.hermes/skills/software-development/handoff/SKILL.md
YAMLEOF

    # Check if quick_commands key already exists (empty or with other entries)
    if grep -q "^quick_commands:" "$CONFIG_FILE"; then
        # Append entries after the quick_commands: line
        line=$(grep -n "^quick_commands:" "$CONFIG_FILE" | head -1 | cut -d: -f1)
        # Check if it's an empty block: quick_commands: {}
        if sed -n "${line}p" "$CONFIG_FILE" | grep -q 'quick_commands: {}'; then
            # Replace the empty block cleanly using the temp file
            head -n "$((line - 1))" "$CONFIG_FILE" > "$TMP_DIR/config_new.yaml"
            echo "" >> "$TMP_DIR/config_new.yaml"
            cat "$TMP_DIR/quick_commands_block.yaml" >> "$TMP_DIR/config_new.yaml"
            tail -n "+$((line + 1))" "$CONFIG_FILE" >> "$TMP_DIR/config_new.yaml"
            mv "$TMP_DIR/config_new.yaml" "$CONFIG_FILE"
        else
            # Insert after the existing quick_commands block
            # Find the end of the block (next line that's not indented, or EOF)
            tail -n "+$((line + 1))" "$CONFIG_FILE" >> "$TMP_DIR/quick_commands_block.yaml"
            head -n "$line" "$CONFIG_FILE" > "$TMP_DIR/config_new.yaml"
            cat "$TMP_DIR/quick_commands_block.yaml" >> "$TMP_DIR/config_new.yaml"
            mv "$TMP_DIR/config_new.yaml" "$CONFIG_FILE"
        fi
    else
        # Append to end of file
        cat "$TMP_DIR/quick_commands_block.yaml" >> "$CONFIG_FILE"
    fi

    # Validate YAML is still parseable (basic check: no Python needed)
    if python3 -c "import yaml; yaml.safe_load(open('$CONFIG_FILE'))" 2>/dev/null; then
        echo "  ✓ Registered /dc and /handoff (YAML validated)"
    else
        echo "  ✗ YAML validation failed — restoring backup"
        mv "$CONFIG_FILE.bak" "$CONFIG_FILE"
        exit 1
    fi
}

# ── Main ──────────────────────────────────────

case "${1:-all}" in
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
echo "Start a new session (/reset in CLI, or new chat in gateway/WebUI) to activate."
echo ""
echo "  /skill double-check       — verify work before marking done"
echo "  /dc                       — shorthand"
echo "  /skill handoff [summary]  — generate handoff prompt"
echo "  /handoff [summary]        — shorthand"
echo ""
echo "To uninstall, remove the skill dirs and delete the quick_commands:"
echo "  rm -rf $SKILLS_DIR/double-check $SKILLS_DIR/handoff"
echo "  (restore config.yaml.bak if needed)"
