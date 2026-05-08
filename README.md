# Hermes Custom Skills

Skills and quick commands I've built for Hermes Agent. Install on any Hermes instance to get the same tooling.

## What's included

| Skill | Description | Slash command |
|-------|-------------|---------------|
| `double-check` | Forces the agent to verify work before declaring completion — completeness, angles, definition of done | `/skill double-check` or `/dc` |
| `handoff` | Generates a structured handoff prompt for transitioning to a new subagent session | `/skill handoff` or `/handoff` |

## Quick install

```bash
# Clone the repo
git clone https://github.com/timfoo/hermes-custom-skills.git /tmp/hermes-custom-skills

# Run the bootstrap script
bash /tmp/hermes-custom-skills/install.sh
```

## Manual install

### 1. Copy skills

```bash
cp -r software-development/double-check ~/.hermes/skills/
cp -r software-development/handoff ~/.hermes/skills/
```

Or if the skills dir uses category subdirectories:

```bash
cp -r software-development/double-check ~/.hermes/skills/software-development/
cp -r software-development/handoff ~/.hermes/skills/software-development/
```

### 2. Register quick commands

Add to `~/.hermes/config.yaml` under `quick_commands:`:

```yaml
quick_commands:
  dc:
    type: exec
    command: cat ~/.hermes/skills/software-development/double-check/SKILL.md
  handoff:
    type: exec
    command: cat ~/.hermes/skills/software-development/handoff/SKILL.md
```

Or run the bootstrap script which does this automatically:

```bash
bash install.sh --config-only
```

### 3. Reset session

Start a new session (`/reset` in CLI, or new chat in gateway/WebUI) for changes to take effect.

## Usage

### double-check

```
/skill double-check
```

Or with a shorthand:
```
/dc
```

Triggers the agent to rigorously verify its work — questions completeness, considers alternative angles, and defines what "done" means before committing.

### handoff

```
/skill handoff [optional task summary]
```

Or with a shorthand:
```
/handoff [optional task summary]
```

Generates a structured handoff prompt as a copyable markdown block. Collects git context (branch, modified files), asks for a task summary if not provided, and formats everything for a fresh agent to pick up seamlessly.

## Gotchas

- `/dc` and `/handoff` are `type: exec` quick commands — they dump the skill content to stdout only. The actual behavior is triggered by `/skill double-check` and `/skill handoff`.
- Skills directory structure matters: Hermes expects `SKILL.md` at the root of each skill directory.
- If `~/.hermes/skills/` is organized by category (e.g., `software-development/double-check/`), adjust paths in `install.sh` and `config.yaml` accordingly.

## Publishing to the skills hub

To share publicly:

```bash
hermes skills publish ~/.hermes/skills/software-development/double-check
hermes skills publish ~/.hermes/skills/software-development/handoff
```

Anyone can then install with:

```bash
hermes skills install double-check
hermes skills install handoff
```
