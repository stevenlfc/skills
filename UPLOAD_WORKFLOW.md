# Skill Upload Workflow

This repository is the default upload target for future skill publishing work.

## Default rule

When the user says "help me upload", use this repository directly:

- Local repo: `C:\Users\A\.codex\skills\stevenlfc-skills`
- Remote repo: `https://github.com/stevenlfc/skills`

## Standard steps

1. Copy the target skill folder(s) into `C:\Users\A\.codex\skills\stevenlfc-skills`.
2. Check the diff with `git status`.
3. Commit in this repo with a clear message.
4. Push to `origin main`.

## Notes

- Do not use the old temporary repo copies unless the user explicitly asks.
- Prefer updating this repo in place instead of creating a new clone every time.
- If upload fails, debug from this repo first.
