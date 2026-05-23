# Hermes Custom Skills

Custom skills for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

## Skills

| Skill | Description |
|-------|-------------|
| `double-check` | Forces the agent to verify work before declaring completion — completeness, angles, definition of done |
| `handoff` | Generates a structured handoff prompt for transitioning to a new subagent session |
| `dedup-organize` | Find and remove duplicate files/videos, organize messy directories. Exact dedup (fclones/rmlint), video dedup (VDF/videohash), semantic dedup (semhash), folder reorganization. Supports audit/apply/rollback modes. |

## Install

**Fresh install:**

```bash
git clone https://github.com/TimFooLabs/hermes-custom-skills.git /tmp/hcs
cp -r /tmp/hcs/workflow/double-check ~/.hermes/skills/workflow/
cp -r /tmp/hcs/workflow/handoff ~/.hermes/skills/workflow/
cp -r /tmp/hcs/workflow/dedup-organize ~/.hermes/skills/
```

**Update existing install:**

```bash
rm -rf ~/.hermes/skills/workflow/double-check
rm -rf ~/.hermes/skills/workflow/handoff
rm -rf ~/.hermes/skills/dedup-organize
git clone https://github.com/TimFooLabs/hermes-custom-skills.git /tmp/hcs
cp -r /tmp/hcs/workflow/double-check ~/.hermes/skills/workflow/
cp -r /tmp/hcs/workflow/handoff ~/.hermes/skills/workflow/
cp -r /tmp/hcs/workflow/dedup-organize ~/.hermes/skills/
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
| `/skill dedup-organize` | Load dedup-organize skill |

**dedup-organize triggers:** "find duplicates", "dedup", "find similar videos", "organize files", "clean up", "remove duplicates"

**Install dedup-organize dependencies:**
```bash
bash ~/.hermes/skills/dedup-organize/scripts/install.sh
# Verify:
bash ~/.hermes/skills/dedup-organize/scripts/install.sh --verify-only
```

## Uninstall

```bash
rm -rf ~/.hermes/skills/workflow/double-check
rm -rf ~/.hermes/skills/workflow/handoff
rm -rf ~/.hermes/skills/dedup-organize
```

Remove the `dc:`, `handoff:`, and `dedup-organize:` entries from `quick_commands:` in `config.yaml`.
