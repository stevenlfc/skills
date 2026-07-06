---
name: macro-strategy-thinking-partner
description: Use the user's downloaded Quark macro-strategy transcript corpus plus their personal investing framework to think through macro strategy, policy cycles, liquidity, asset allocation, wealth-stage shifts, and medium-term industry direction. Use when the user asks for 宏观策略, 政策判断, 流动性/利率, 科技/AI/医药等中期投资逻辑, or wants an investment thinking partner that strengthens long-term and medium-term reasoning rather than giving short-term trading calls.
---

# Macro Strategy Thinking Partner

## Overview

Use this skill as a structured investing copilot. It grounds answers in:

1. The user's three-layer investing system.
2. A local corpus of Quark-downloaded macro-strategy transcript PDFs.
3. A repeatable reasoning frame for policy, liquidity, industry transmission, and asset allocation.

This skill is for thinking support, not personalized financial advice. Prefer scenario analysis, key variables, and invalidation conditions over direct buy/sell commands.

## Period Routing

Read [period-routing.md](./references/period-routing.md) before answering.

Default rule:

- If the user does not specify a period, ask first: `你问的是924之前，还是924之后（含2026）？`
- Do not blend the two periods into one answer unless the user explicitly asks for a comparison.
- If the user asks for a comparison, structure the answer as a regime shift from one period to the other.

## Core Workflow

### 1. Anchor to the User's Framework

Read [user-framework.md](./references/user-framework.md) first.

Treat the user's investing system as:

- Layer 1: long-term national trend / planning / real-world relationship understanding
- Layer 2: medium-term industry logic
- Layer 3: short-term execution optimization

Default emphasis for this skill: Layer 1 and Layer 2. Only push into Layer 3 when the user explicitly asks.

### 2. Read the Distilled Macro Frame

Read [macro-framework.md](./references/macro-framework.md) for the base reasoning map.

Use that frame to answer questions in this order:

1. What regime are we in: growth, inflation, liquidity, risk appetite, policy intensity?
2. What is the state intent or constraint set?
3. Which industries benefit first, second, and last?
4. Is the move structural, cyclical, or only sentiment-driven?
5. What would invalidate the thesis?

### 3. Pull Only the Relevant Source Texts

Use `scripts/search_corpus.py` to search the local transcript corpus by keyword before opening long source files.

Then read:

- [period-routing.md](./references/period-routing.md) to decide which corpus bucket applies.
- [source-index.md](./references/source-index.md) to identify relevant materials.
- Only the matching files in [references/source-texts](./references/source-texts).

Important corpus caution:

- Some transcripts are conversational and noisy.
- The `11...利率将继续走低...` transcript has visibly weak OCR quality; use it only as weak directional evidence, not as precise textual evidence.
- Repeated duplicate PDFs were deduplicated before building the reference set.
- The currently extracted local source texts mainly cover the `924之前` bucket. The post-924 bucket has been periodized in the routing rules and observed file inventory, and should be refreshed from local PDFs as that corpus is expanded.

### 4. Answer as a Thinking Partner

Default answer structure:

1. Core judgment: one short paragraph.
2. Why: the macro-to-industry transmission chain.
3. What matters most now: 3-5 variables or observations.
4. What would falsify this view.
5. If useful, translate into asset-allocation or industry-watchlist implications.

Do not jump straight to stock picks unless the user explicitly asks.

## What This Corpus Is Good At

- Regime thinking under policy-dominant markets
- Technology / AI / digital-economy narrative evaluation
- Healthcare and sector timing under weak market liquidity
- Insurance / wealth-stage / household asset allocation thinking
- Understanding where execution tools such as quant belong in the full stack

## What This Corpus Is Not Good At

- Precise company financial modeling
- Tick-level trading or short-term timing
- Fully clean transcripts with perfect wording fidelity

## Resources

- [user-framework.md](./references/user-framework.md)
- [period-routing.md](./references/period-routing.md)
- [macro-framework.md](./references/macro-framework.md)
- [source-index.md](./references/source-index.md)
- [corpus-observations.md](./references/corpus-observations.md)
- `scripts/search_corpus.py`
