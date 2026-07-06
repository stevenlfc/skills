---
name: macro-strategy-pre-924
description: Use the user's pre-924 Quark macro-strategy transcript corpus to reason about macro regime, policy intent, medium-term industry logic, technology, healthcare, insurance, rates, and execution tools. Use when the user asks for macro-strategy judgment anchored in the earlier period before 9/24 and does not want the later 924-after regime mixed in.
---

# Macro Strategy Pre 924

## Overview

Use this skill for macro-strategy thinking based only on the pre-924 corpus. It is a thinking partner for the user's Layer 1 and Layer 2 investing framework, not a short-term trading signal engine.

## Scope Guardrail

- Stay inside the `924 before` corpus only.
- If the user is actually asking about the `924 after` or `2026` regime, stop and ask them to switch to `$macro-strategy-post-924-2026`.
- Do not blend later-period conclusions into this skill unless the user explicitly asks for a cross-period comparison.

## Core Workflow

### 1. Anchor to the User's Investing Framework

Read [user-framework.md](./references/user-framework.md) first.

Default emphasis:

- First: long-cycle macro and policy understanding
- Second: medium-term industry transmission
- Third: only light execution translation unless the user explicitly asks for tactics

### 2. Lock the Period

Read [period-brief.md](./references/period-brief.md) before answering.

Treat this corpus as the earlier regime:

- fragile market backdrop
- policy expectations matter, but later 924-style regime change has not happened yet
- technology / healthcare / insurance / rates / quant are discussed from an earlier-cycle angle

### 3. Use the Macro Reasoning Frame

Read [macro-framework.md](./references/macro-framework.md).

Answer in this order:

1. What regime is the speaker describing?
2. What policy problem or constraint set is being discussed?
3. Which industries benefit first, second, and last?
4. Is the move structural, cyclical, or mostly sentiment?
5. What would invalidate the thesis?

### 4. Pull Corpus Evidence

Use `scripts/search_corpus.py` before opening long source files.

Then read:

- [source-index.md](./references/source-index.md)
- [corpus-observations.md](./references/corpus-observations.md)
- only the matching files under [references/source-texts](./references/source-texts)

Important caution:

- These are transcript-style documents, not clean research notes.
- The falling-rates transcript has visibly weak OCR quality, so use it only as weak directional evidence.
- Prefer repeated ideas across multiple source files over one noisy line.

## Default Answer Shape

1. Core judgment
2. Macro and policy chain
3. Industry transmission
4. Variables to watch
5. What would change the view

If the user asks for allocation implications, translate the answer into watchlist, exposure direction, and invalidation conditions instead of direct personalized buy or sell commands.

## Good Fit

- Pre-924 macro-strategy discussion
- Earlier-period technology and healthcare positioning
- Insurance and wealth-stage allocation logic
- Rates and household balance-sheet implications
- Where quant belongs in the investing stack

## Not a Good Fit

- Later 924-after or 2026 regime calls
- Short-term trading execution in isolation
- Single-stock financial modeling

## Resources

- [period-brief.md](./references/period-brief.md)
- [user-framework.md](./references/user-framework.md)
- [macro-framework.md](./references/macro-framework.md)
- [corpus-observations.md](./references/corpus-observations.md)
- [source-index.md](./references/source-index.md)
- `scripts/search_corpus.py`
