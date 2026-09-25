---
name: github-agent-auth
description: "Use when an agent needs GitHub API/git access — mint a short-lived, repo-scoped token via the timfoo-agents GitHub App instead of using TimFooLabs' personal gh token. Covers the minter script, setup state, and the security model."
---

# GitHub Agent Auth (GitHub App installation tokens)

## Why this exists

TimFooLabs' ambient `gh` credential carries `repo, workflow, read:org, gist,
admin:public_key` — an agent using it inherits all of it. GitHub also does NOT
support creating PATs via API (confirmed by GitHub staff, community discussion
#148626), so per-task scoped PATs can't be automated. A GitHub App is the only
fully automatable path: its private key signs a JWT, exchanged for an
installation token that is repo-scoped, read-only by default, and expires in
≤1 hour. Agents act as `timfoo-agents[bot]`, not as Tim.

## Mint a token (the normal case)

```bash
# read-only, 1 hour, exactly this repo
export GH_TOKEN="$(github-agent-token --repo TimFooLabs/<repo>)"

# write access (contents + issues + PRs)
export GH_TOKEN="$(github-agent-token --repo TimFooLabs/<repo> --write)"

# multiple repos, one owner per mint
github-agent-token --repo TimFooLabs/a --repo TimFooLabs/b
```

- `--repo` is REQUIRED — never mint installation-wide tokens.
- Token prints on stdout; progress/verification goes to stderr. The script
  self-verifies: it lists the repos the token can see and refuses to print
  the token unless they match exactly what was requested.
- Default key path `~/.hermes/secrets/github-app.pem`, App ID from
  `$GITHUB_APP_ID` or `~/.hermes/.env` (`GITHUB_APP_ID=5072487`).
- `--list` shows installations; `--expire-min N` shortens lifetime (max 60).

## Environment (verified working 2026-09-25)

- App: `timfoo-agents`, App ID `5072487`, installation `164772300` on
  `@TimFooLabs` (all repos — 44 at setup time).
- App permissions: Contents/Issues/Pull requests R&W + forced Metadata read.
  No org/account/enterprise perms, no webhooks, no user authorization.
- Private key: `~/.hermes/secrets/github-app.pem` (0600, dir 0700).
- Script: `~/.hermes/bin/github-agent-token` (stdlib + openssl only).
- TODO: `echo 'GITHUB_APP_ID=5072487' >> ~/.hermes/.env` (pending user consent).

## Rules

- **Read-only unless the task truly writes.** Default to no `--write`.
- **One task, one mint.** Don't hold tokens longer than the operation;
  they die in ≤1h anyway — that's the design.
- **Never** fall back to Tim's personal token when this works. If the App
  can't see a repo, the fix is adding it to the installation (settings →
  Repository access), not widening credentials.
- Git push with an installation token uses username `x-access-token`:
  `git push https://x-access-token:$GH_TOKEN@github.com/OWNER/REPO.git`
- `GET /user` 403s for installation tokens — that's correct, they're not
  user tokens. Use `/installation/repositories` to probe scope.

## Failure modes (all live-tested)

| Symptom | Cause / fix |
|---|---|
| 422 "does not exist or is not accessible" | repo not in installation → add it in app settings, or typo |
| 422 permissions error | flag exceeds app permissions (e.g. `--workflow` needs Workflows perm added to the App) |
| 401 "JSON web token could not be decoded" | wrong/expired key — regenerate .pem, update `~/.hermes/secrets/github-app.pem` |
| `github-agent-token: command not found` | `~/.hermes/bin` must be on PATH (it is, by default) |

## Escalation path

Solo personal repos: this setup. Unattended multi-repo fleet or org work:
narrow the installation's repo list first; multiple installations of the same
App (per-project) give per-project blast radius. Never a shared classic PAT.
