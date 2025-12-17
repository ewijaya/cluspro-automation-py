---
description: Auto-stage, commit with generous message, and push to remote
argument-hint: "[optional custom message]"
allowed-tools: ["Bash"]
---

# Git Auto-Push Command

Automatically stage all changes, generate a descriptive commit message, commit, and push to remote.

## Step 1: Check Repository Status

First, let me see what's changed:

! git status --short
! git diff --cached --stat
! git diff --stat

## Step 2: Stage All Changes

Staging all changes (tracked and untracked):

! git add -A

## Step 3: Analyze the Changes

Let me examine the actual changes to write a meaningful commit message:

! git diff --cached --stat
! git log --oneline -5

Now analyzing the full diff to understand what changed:

! git diff --cached

## Step 4: Generate Commit Message

Based on the changes above, I'll create a descriptive commit message following these guidelines:

- **feat:** New features or functionality
- **fix:** Bug fixes
- **docs:** Documentation changes
- **refactor:** Code restructuring without behavior change
- **test:** Adding or updating tests
- **chore:** Maintenance, dependencies, configs
- **perf:** Performance improvements
- **style:** Code formatting, whitespace

**Message format:**
- Subject line: concise, imperative mood, under 72 characters
- Be specific about what changed (not generic like "update files")
- Include relevant details (file names, function names, key changes)
- **DO NOT** include Claude Code attribution or co-author lines

**If user provided custom message via `$ARGUMENTS`:**
I'll use that instead.

## Step 5: Commit and Push

Now I'll commit with the generated message and push to remote:

! git commit -m "<generated or custom message>"
! git remote | xargs -I {} git push {} main

Done! Your changes have been committed and pushed to all remote repositories.