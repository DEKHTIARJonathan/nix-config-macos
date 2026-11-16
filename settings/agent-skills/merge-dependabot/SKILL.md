---
name: merge-dependabot
description: >-
  Fetch and locally merge all dependabot/* branches into the current branch,
  resolving Git conflicts only. Works with any repository or package manager. No
  tests, hooks, relocking, installations, builds, or dependency validation.
---

# Merge Dependabot

Merge the branches and resolve Git conflicts. Keep the work strictly within Git;
do not turn it into a dependency upgrade or verification project. If the project
include a prek or pre-commit config file, run `prek autoupdate` or
`pre-commit autoupdate` (preferably use `prek` if available).

## Scope

- Use the user's requested repository and currently checked out branch. Ask for
  a target only when none can be determined.
- Read applicable repository instructions. The user's explicit merge-only scope
  takes precedence over broader dependency-update workflows.
- Require a clean index and worktree before merging. If user changes are
  present, report that blocker without stashing, committing, or overwriting
  them.
- Do not run tests, prek, pre-commit, linters, formatters, builds, installs,
  relocking, upgrades, dependency audits, or compatibility checks. Do not start
  containers or inspect whether the resulting dependencies can install together.
- Disable Git hooks for merge and commit commands with command-scoped
  `core.hooksPath` pointing to an empty temporary directory, or equivalent
  process-scoped Git configuration. Do not change persistent Git configuration.
- Keep ordinary merge commits. Do not squash, rebase, push, or delete branches
  unless the user explicitly requests it.

## Fetch and merge

1. Switch to the requested target if necessary and record its starting SHA.
2. Fetch `dependabot/*` branches from the requested remote, or all configured
   remotes when none is specified. For each remote, use the quoted refspec:

   ```sh
   git fetch --prune --no-tags <remote> '+refs/heads/dependabot/*:refs/remotes/<remote>/dependabot/*'
   ```

3. List matching local and fetched remote branches in stable refname order and
   record their head SHAs. Use literal namespace prefixes, so nested branch
   names are included:

   ```sh
   git for-each-ref --sort=refname --format='%(refname) %(objectname)' refs/heads/dependabot refs/remotes/<remote>/dependabot
   ```

   Include every matching branch, regardless of ecosystem or file type. Do not
   filter by pull-request state, CI status, package manager, or compatibility.
   If none exist, report that there is nothing to merge.

4. Merge each branch sequentially with `git merge --no-ff --no-edit <ref>`,
   applying the hook configuration above. Skip heads already reachable from the
   target; this also handles duplicate heads across remotes.
5. Resolve any conflicts before proceeding to the next branch:
   - **Manifests, source, workflows, and configuration:** preserve the intended
     updates from both sides. Adjacent version bumps must not undo earlier
     merges. Resolve the text without investigating dependency compatibility.
   - **Lockfiles and generated dependency-resolution files:** keep the current
     side with `git checkout --ours -- <file>`, then stage that file. Apply this
     to any ecosystem; identify these files by purpose, not just a `.lock`
     suffix. Keep cleanly merged lockfile changes. Do not regenerate or
     reconcile lockfiles afterward.
   - Stage only the resolved files and finish the merge with a descriptive
     `git commit -m '...'`, with hooks disabled as above.

   If a non-lockfile conflict cannot be resolved without guessing the intended
   change, abort only that in-progress merge and report the blocker. Preserve
   earlier successful merges and name the remaining branches.

## Finish

Use Git metadata only to confirm that every recorded head is reachable from the
target and no merge remains unresolved. Report the merged/already-included
count, target branch, final SHA, and worktree state. Mention any lockfiles kept
from the current side; their consistency has not been checked. State that no
tests, relocking, installations, or dependency checks ran. Keep the report
short.
