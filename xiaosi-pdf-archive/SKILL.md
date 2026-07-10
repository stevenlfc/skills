---
name: xiaosi-pdf-archive
description: Archive newly downloaded Xiaosi PDF files from C:\Users\User\Downloads into the correct folders under D:\obsidianNotes\小司\xiaosi and then commit and push the resulting git changes to GitHub. Use when the user asks to move or归档小司 PDF, mentions C:\Users\User\Downloads, says 新下载的小司 PDF, or wants the PDFs both filed into the vault and uploaded to GitHub.
---

# Xiaosi PDF Archive

Use this skill to process newly downloaded Xiaosi PDFs end to end: detect candidate PDFs in `C:\Users\User\Downloads`, route each file into the correct folder inside `D:\obsidianNotes\小司\xiaosi`, deduplicate when the same document is already archived, and push any new archive result to the repo's GitHub remote.

## Workflow

1. Run `scripts/archive_xiaosi_pdfs.py`.
Default command:

```powershell
python C:\Users\User\.codex\skills\xiaosi-pdf-archive\scripts\archive_xiaosi_pdfs.py
```

2. Read the script output and report:
- moved files
- duplicates that were removed from `Downloads`
- files that could not be classified
- git commit and push status

3. If the script reports unclassified files, read `references/routing-rules.md`, inspect the current vault structure, and finish the remaining routing manually.

## Defaults

- Downloads directory: `C:\Users\User\Downloads`
- Xiaosi vault repo: `D:\obsidianNotes\小司\xiaosi`
- Git behavior: commit and push automatically when the script creates repo changes

## Useful Commands

Dry run without changing files:

```powershell
python C:\Users\User\.codex\skills\xiaosi-pdf-archive\scripts\archive_xiaosi_pdfs.py --dry-run
```

Skip git push and only archive files:

```powershell
python C:\Users\User\.codex\skills\xiaosi-pdf-archive\scripts\archive_xiaosi_pdfs.py --git-mode never
```

## Resources

- `scripts/archive_xiaosi_pdfs.py`: deterministic archiving and git automation
- `references/routing-rules.md`: current filename-to-folder routing rules and known assumptions
