#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DOWNLOADS = Path(r"C:\Users\User\Downloads")
DEFAULT_VAULT = Path(r"D:\obsidianNotes\小司\xiaosi")

CANDIDATE_KEYWORDS = (
    "趋势知识圈",
    "行业知识圈",
    "买方知识圈",
    "特邀课程",
)

TREND_ISSUE_TO_FOLDER = {
    "3": "云南财经财务老师",
    "4": "新结构经济学老师",
    "5": "国际关系学院老师",
    "6": "陈鹏老师",
    "7": "记者",
    "8": "云南财经财务老师",
    "9": "新结构经济学老师",
    "10": "国际关系学院老师",
    "11": "陈鹏老师",
}

KEYWORDS = {
    "ai": ("ai", "大模型"),
    "medical": ("医药", "创新药", "小核酸", "脑机接口"),
    "market": ("牛市", "a股", "市场", "情绪", "持股", "持币", "博弈", "轮动", "调整", "修复", "缩圈", "贪婪", "恐惧", "风险", "靴子", "围城", "中报"),
    "semiconductor": ("半导体", "芯片", "存储", "算力芯片", "成熟制程", "先进工艺", "新兴产业"),
    "new_energy": ("新能源", "电新", "锂电", "光伏", "户储"),
    "consumer": ("消费", "轻工", "纺织", "服装"),
}


@dataclass
class PlannedMove:
    source: Path
    destination: Path
    duplicate_of: Path | None = None
    note: str = ""


def normalize_text(value: str) -> str:
    lowered = value.lower()
    lowered = lowered.replace("+", " ")
    lowered = lowered.replace("【", "").replace("】", "")
    lowered = lowered.replace("（", "").replace("）", "")
    lowered = lowered.replace("(", "").replace(")", "")
    lowered = lowered.replace("。", "").replace(".", "")
    lowered = lowered.replace("，", "").replace(",", "")
    lowered = lowered.replace("：", "").replace(":", "")
    lowered = lowered.replace("_", "")
    return re.sub(r"\s+", "", lowered)


def sanitize_filename(name: str) -> str:
    name = name.replace("+", " ")
    name = re.sub(r"\s+", " ", name).strip()
    return name


def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_candidate_pdf(path: Path) -> bool:
    if path.suffix.lower() != ".pdf":
        return False
    name = path.name
    return any(keyword in name for keyword in CANDIDATE_KEYWORDS)


def detect_destination(vault_root: Path, filename: str) -> Path | None:
    compact = normalize_text(filename)

    if "趋势知识圈" in filename:
        if "特邀课程" in filename:
            return vault_root / "2026" / "趋势知识圈" / "陈鹏老师" / sanitize_filename(filename)
        match = re.search(r"(?P<issue>\d+)\.", filename)
        if match:
            folder = TREND_ISSUE_TO_FOLDER.get(match.group("issue"))
            if folder:
                return vault_root / "2026" / "趋势知识圈" / folder / sanitize_filename(filename)
        if "ai进化" in compact or "半导体发展的确定性" in compact:
            return vault_root / "2026" / "趋势知识圈" / "记者" / sanitize_filename(filename)
        return None

    if "买方知识圈" in filename:
        return vault_root / "2026" / "2026首席" / "市场策略" / sanitize_filename(filename)

    if "宏观" in compact and "加餐" not in compact:
        return vault_root / "2026" / "宏观策略" / sanitize_filename(filename)

    if "加餐" in compact:
        if "刘涛" in compact:
            return vault_root / "2026" / "2026首席加餐" / "市场策略" / sanitize_filename(filename)
        if "岳" in compact:
            if contains_any(compact, KEYWORDS["ai"]):
                return vault_root / "2026" / "2026首席加餐" / "AI" / sanitize_filename(filename)
            if contains_any(compact, KEYWORDS["medical"]):
                return vault_root / "2026" / "2026首席加餐" / "医药" / sanitize_filename(filename)
            if contains_any(compact, KEYWORDS["market"]):
                return vault_root / "2026" / "2026首席加餐" / "市场策略" / sanitize_filename(filename)
        return None

    if contains_any(compact, KEYWORDS["semiconductor"]):
        return vault_root / "2026" / "2026首席" / "半导体" / sanitize_filename(filename)
    if contains_any(compact, KEYWORDS["new_energy"]):
        return vault_root / "2026" / "2026首席" / "新能源" / sanitize_filename(filename)
    if contains_any(compact, KEYWORDS["medical"]):
        return vault_root / "2026" / "2026首席" / "医药" / sanitize_filename(filename)
    if contains_any(compact, KEYWORDS["consumer"]):
        return vault_root / "2026" / "2026首席" / "消费" / sanitize_filename(filename)

    return None


def contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def find_duplicate(destination: Path) -> Path | None:
    folder = destination.parent
    if not folder.exists():
        return None
    target_sig = normalize_text(destination.stem)
    for existing in folder.glob("*.pdf"):
        if normalize_text(existing.stem) == target_sig:
            return existing
    return None


def build_plan(downloads_root: Path, vault_root: Path) -> tuple[list[PlannedMove], list[Path], list[Path]]:
    planned: list[PlannedMove] = []
    ignored: list[Path] = []
    unclassified: list[Path] = []

    for source in sorted(downloads_root.glob("*.pdf"), key=lambda item: item.stat().st_mtime, reverse=True):
        if not is_candidate_pdf(source):
            ignored.append(source)
            continue
        destination = detect_destination(vault_root, source.name)
        if destination is None:
            unclassified.append(source)
            continue
        duplicate = find_duplicate(destination)
        note = ""
        if duplicate is not None:
            note = "normalized-name match found"
        planned.append(PlannedMove(source=source, destination=destination, duplicate_of=duplicate, note=note))
    return planned, ignored, unclassified


def apply_plan(planned: list[PlannedMove], dry_run: bool) -> tuple[list[str], list[Path]]:
    results: list[str] = []
    changed_targets: list[Path] = []

    for item in planned:
        item.destination.parent.mkdir(parents=True, exist_ok=True)
        if item.duplicate_of is not None:
            src_hash = sha256(item.source)
            existing_hash = sha256(item.duplicate_of)
            if src_hash == existing_hash:
                results.append(f"DUPLICATE {item.source} -> keep existing {item.duplicate_of}")
                if not dry_run:
                    item.source.unlink()
                continue
            if item.duplicate_of.resolve() != item.destination.resolve():
                raise RuntimeError(
                    f"Signature conflict: {item.source} matches {item.duplicate_of} but file content differs."
                )

        results.append(f"MOVE {item.source} -> {item.destination}")
        changed_targets.append(item.destination)
        if not dry_run:
            item.source.replace(item.destination)

    return results, changed_targets


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=str(cwd), text=True, capture_output=True, check=False)


def maybe_commit_and_push(vault_root: Path, changed_targets: list[Path], git_mode: str, dry_run: bool) -> list[str]:
    messages: list[str] = []
    if dry_run or git_mode == "never" or not changed_targets:
        return messages

    rel_paths = [str(path.relative_to(vault_root)) for path in changed_targets if path.exists()]
    status = run(["git", "status", "--porcelain"], vault_root)
    if status.returncode != 0:
        raise RuntimeError(status.stderr.strip() or "git status failed")
    if not status.stdout.strip():
        return messages

    add_cmd = ["git", "add", "--", *rel_paths]
    add_result = run(add_cmd, vault_root)
    if add_result.returncode != 0:
        raise RuntimeError(add_result.stderr.strip() or "git add failed")

    commit_message = f"Archive Xiaosi PDFs ({len(rel_paths)} files)"
    commit_result = run(["git", "commit", "-m", commit_message], vault_root)
    if commit_result.returncode != 0:
        combined = (commit_result.stdout + "\n" + commit_result.stderr).strip()
        raise RuntimeError(combined or "git commit failed")
    messages.append(commit_result.stdout.strip())

    if git_mode == "auto":
        branch_result = run(["git", "branch", "--show-current"], vault_root)
        if branch_result.returncode != 0:
            raise RuntimeError(branch_result.stderr.strip() or "git branch failed")
        branch = branch_result.stdout.strip()
        push_result = run(["git", "push", "origin", branch], vault_root)
        if push_result.returncode != 0:
            combined = (push_result.stdout + "\n" + push_result.stderr).strip()
            raise RuntimeError(combined or "git push failed")
        messages.append(push_result.stdout.strip())

    return messages


def format_summary(planned: list[PlannedMove], ignored: list[Path], unclassified: list[Path], results: list[str], git_messages: list[str], dry_run: bool) -> str:
    lines = []
    lines.append(f"Mode: {'dry-run' if dry_run else 'apply'}")
    lines.append(f"Candidates: {len(planned)}")
    lines.append(f"Ignored PDFs: {len(ignored)}")
    lines.append(f"Unclassified: {len(unclassified)}")
    if results:
        lines.append("Actions:")
        lines.extend(f"  {line}" for line in results)
    if unclassified:
        lines.append("Needs manual classification:")
        lines.extend(f"  {path}" for path in unclassified)
    if git_messages:
        lines.append("Git:")
        for message in git_messages:
            for line in message.splitlines():
                if line.strip():
                    lines.append(f"  {line}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive Xiaosi PDFs and optionally push git changes.")
    parser.add_argument("--downloads-root", default=str(DEFAULT_DOWNLOADS))
    parser.add_argument("--vault-root", default=str(DEFAULT_VAULT))
    parser.add_argument("--git-mode", choices=("auto", "never"), default="auto")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    downloads_root = Path(args.downloads_root)
    vault_root = Path(args.vault_root)

    if not downloads_root.exists():
        print(f"Downloads path does not exist: {downloads_root}", file=sys.stderr)
        return 1
    if not vault_root.exists():
        print(f"Vault path does not exist: {vault_root}", file=sys.stderr)
        return 1

    planned, ignored, unclassified = build_plan(downloads_root, vault_root)
    if not planned and not unclassified:
        print("No Xiaosi PDF candidates found.")
        return 0

    try:
        results, changed_targets = apply_plan(planned, dry_run=args.dry_run)
        git_messages = maybe_commit_and_push(vault_root, changed_targets, args.git_mode, args.dry_run)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(format_summary(planned, ignored, unclassified, results, git_messages, args.dry_run))
    return 0 if not unclassified else 2


if __name__ == "__main__":
    raise SystemExit(main())
