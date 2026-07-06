---
name: macro-strategy-post-924-2026
description: Use the user's post-924 and 2026 Quark macro-strategy transcript corpus to reason about regime change, policy transmission, A-share market outlook, quarterly strategy, and medium-term asset-allocation logic. Use when the user asks for macro-strategy judgment anchored in the later 924-after period and 2026 materials.
---

# Macro Strategy Post 924 2026

## Overview

Use this skill for macro-strategy thinking based only on the post-924 plus 2026 corpus. It is designed for the later regime where market outlook, policy shifts, and quarterly strategy discussions differ materially from the earlier period.

## Scope Guardrail

- Stay inside the `924 after` and `2026` corpus only.
- If the user is actually asking about the earlier period before 9/24, stop and ask them to switch to `$macro-strategy-pre-924`.
- Do not backfill earlier-period logic unless the user explicitly asks for a cross-period comparison.

## Core Workflow

### 1. Anchor to the User's Investing Framework

Read [user-framework.md](./references/user-framework.md) first.

Default emphasis:

- First: long-cycle macro and policy understanding
- Second: medium-term industry transmission
- Third: only light execution translation unless the user explicitly asks for tactics

### 2. Lock the Period

Read [period-brief.md](./references/period-brief.md) before answering.

Treat this corpus as the later regime:

- after the 924 divide, the market discussion changes
- quarterly A-share strategy becomes more explicit
- policy transmission, market-level framing, and regime comparison matter more
- 2026 files extend the same later-period logic forward

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
- Some titles are market-outlook oriented; translate them into variables, regime, and policy chain rather than repeating slogans.
- Prefer repeated ideas across multiple source files over one noisy line.

## Default Answer Shape

1. Core judgment
2. Macro and policy chain
3. Industry transmission
4. Variables to watch
5. What would change the view

If the user asks for allocation implications, translate the answer into watchlist, exposure direction, and invalidation conditions instead of direct personalized buy or sell commands.

## Good Fit

- Post-924 regime-shift questions
- 2025 and 2026 market outlook discussion
- Quarterly A-share strategy and policy transmission
- Comparing later-stage market levels, risk appetite, and liquidity
- Translating later-period macro views into medium-term industry attention

## Not a Good Fit

- Earlier pre-924 regime calls
- Short-term trading execution in isolation
- Single-stock financial modeling

## Resources

- [period-brief.md](./references/period-brief.md)
- [user-framework.md](./references/user-framework.md)
- [macro-framework.md](./references/macro-framework.md)
- [corpus-observations.md](./references/corpus-observations.md)
- [source-index.md](./references/source-index.md)
- `scripts/search_corpus.py`
