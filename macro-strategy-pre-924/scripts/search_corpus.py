#!/usr/bin/env python3
"""Simple keyword search over the local macro-strategy transcript corpus."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "references" / "source-texts"


def load_documents() -> list[tuple[str, str]]:
    docs: list[tuple[str, str]] = []
    for path in sorted(ROOT.glob("*.md")):
        docs.append((path.name, path.read_text(encoding="utf-8", errors="ignore")))
    return docs


def score_document(text: str, terms: list[str]) -> int:
    lower = text.lower()
    return sum(lower.count(term) for term in terms)


def collect_snippets(text: str, pattern: re.Pattern[str], limit: int = 3) -> list[str]:
    snippets: list[str] = []
    for line in text.splitlines():
        if pattern.search(line):
            snippets.append(line.strip())
        if len(snippets) >= limit:
            break
    return snippets


def main() -> int:
    parser = argparse.ArgumentParser(description="Search the macro strategy transcript corpus.")
    parser.add_argument("query", help="Keyword query, for example: 政策 流动性 科技")
    parser.add_argument("--top", type=int, default=5, help="Maximum results to return")
    args = parser.parse_args()

    terms = [part.lower() for part in re.split(r"\s+", args.query.strip()) if part]
    if not terms:
        raise SystemExit("Query is empty.")

    pattern = re.compile("|".join(re.escape(term) for term in terms), re.IGNORECASE)
    results = []
    for name, text in load_documents():
        score = score_document(text, terms)
        if score <= 0:
            continue
        results.append(
            {
                "file": name,
                "score": score,
                "snippets": collect_snippets(text, pattern),
            }
        )

    results.sort(key=lambda item: (-item["score"], item["file"]))
    print(json.dumps(results[: args.top], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
