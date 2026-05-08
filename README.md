# Hermes Custom Skills

Custom skills for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

## Skills

| Skill | Description |
|-------|-------------|
| `double-check` | Forces the agent to verify work before declaring completion — completeness, angles, definition of done |
| `handoff` | Generates a structured handoff prompt for transitioning to a new subagent session |

## Install

**Fresh install:**

```bash
git clone https://github.com/TimFooLabs/hermes-custom-skills.git /tmp/hcs
mkdir -p ~/.hermes/skills/workflow
cp -r /tmp/hcs/workflow/double-check ~/.hermes/skills/workflow/
cp -r /tmp/hcs/workflow/handoff ~/.hermes/skills/workflow/
```

**Update existing install:**

```bash
rm -rf ~/.hermes/skills/workflow/double-check
rm -rf ~/.hermes/skills/workflow/handoff
git clone https://github.com/TimFooLabs/hermes-custom-skills.git /tmp/hcs
mkdir -p ~/.hermes/skills/workflow
cp -r /tmp/hcs/workflow/double-check ~/.hermes/skills/workflow/
cp -r /tmp/hcs/workflow/handoff ~/.hermes/skills/workflow/
```

**Register quick commands** — add to `~/.hermes/config.yaml` under `quick_commands:` (skip if already present):

```yaml
  dc:
    type: exec
    command: cat ~/.hermes/skills/workflow/double-check/SKILL.md
  handoff:
    type: exec
    command: cat ~/.hermes/skills/workflow/handoff/SKILL.md
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
rm -rf ~/.hermes/skills/workflow/double-check
rm -rf ~/.hermes/skills/workflow/handoff
```

Remove the `dc:` and `handoff:` entries from `quick_commands:` in `config.yaml`.
