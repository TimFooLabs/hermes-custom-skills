# Hermes Custom Skills

Custom skills for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

## Skills

| Skill | Description |
|-------|-------------|
| `double-check` | Forces the agent to verify work before declaring completion — completeness, angles, definition of done |
| `handoff` | Generates a structured handoff prompt for transitioning to a new subagent session |

## Install

```bash
# Clone
git clone https://github.com/TimFooLabs/hermes-custom-skills.git /tmp/hcs

# Copy skills to Hermes
cp -r /tmp/hcs/software-development/* ~/.hermes/skills/software-development/
```

Then add quick command shorthands to `~/.hermes/config.yaml` under `quick_commands:`:

```yaml
  dc:
    type: exec
    command: cat ~/.hermes/skills/software-development/double-check/SKILL.md
  handoff:
    type: exec
    command: cat ~/.hermes/skills/software-development/handoff/SKILL.md
```

Start a new session (`/reset` in CLI, or new chat in gateway/WebUI) to activate.

## Usage

| Command | Description |
|---------|-------------|
| `/skill double-check` | Verify work before marking done |
| `/dc` | Shorthand |
| `/skill handoff [summary]` | Generate handoff prompt |
| `/handoff [summary]` | Shorthand |

## Uninstall

```bash
rm -rf ~/.hermes/skills/software-development/double-check
rm -rf ~/.hermes/skills/software-development/handoff
```

Remove the `dc:` and `handoff:` entries from `quick_commands:` in `config.yaml`.
