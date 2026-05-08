---
name: handoff
description: "Generates a structured handoff prompt for transitioning to a new subagent session. Use when you need to package context for a fresh agent to continue work."
argument-hint: "[optional: task summary]"
---

Generate a concise handoff prompt for transitioning to a new subagent session.

## Step 1: Gather Environment Context

Run these commands to collect the current state:

```bash
pwd                          # working directory
git branch --show-current 2>/dev/null || echo "not a git repo"
git status --short 2>/dev/null || echo "n/a"
```

If not in a git repo, skip the git lines — just note the directory.

## Step 2: Collect Session Context

From the conversation history, identify:
- What was accomplished in this session
- What files were created or modified
- What the user's original goal was
- Any errors or pitfalls encountered

## Step 3: Ask for Task Summary (if no argument provided)

If the user did not provide a task summary argument, ask:
> "What's the current state of the task and what should happen next?"

## Step 4: Generate the Handoff Prompt

Fill in the template below with collected data. Be specific — a good handoff lets a fresh agent start working immediately.

```markdown
# Handoff: [brief task title]

## What was done
[Bullet list of key actions completed this session]

## Immediate next step
[The single most important thing to do next]

## Gotchas
- [Any pitfalls, conventions, or context discovered]
- [Non-obvious things the new agent should know]

## Environment
- **Working Directory:** [pwd result]
- **Branch:** [git branch result, or "not a git repo"]
- **Modified Files:** [git status result, or files from session context]

## Key files to read
- [file 1] — [why it matters]
- [file 2] — [why it matters]

## Original goal
[The user's actual request / what "done" looks like]
```

## Step 5: Present to User

Output the filled-in template as a copyable Markdown code block. Keep it concise — aim for under 20 lines total.
