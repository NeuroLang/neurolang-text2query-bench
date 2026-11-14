# neurosynth-v3e: distilled bank, worked traces, hybrid retrieval (2026-11-14)

Plan steps 2 (outputs) and 3 (ablation) of the distillation plan, on
DeepSeek V4 Flash 0731 (OpenRouter `openrouter-deepseek-0731`, the model of
Albert's `albert-deepseek`).

## Code

- **A (baseline):** upstream master **1a4dafd8**, which already holds the
  step-1 fixes #1201–#1205 (all merged 2026-11-13), so no integration
  branch was needed: every variant runs the fixed code. Detached worktree
  `/Users/bot/NeuroLang-nsv3e-A`.
- **B–E:** NeuroLang branch `feat/llm-distilled-bank` (worktree
  `/Users/bot/NeuroLang-distbank`, from 1a4dafd8): an optional `trace` field
  of bank entries (`llm/examples.py` `Example.trace`, `prompts.py`
  `format_examples` renders the traces of at most 2 chosen examples, ReAct
  only, as `Action / Action Input / Observation` lines; tests in
  `llm/tests/test_examples.py`). One local branch and worktree per variant
  (`nsv3e-B` … `nsv3e-E`, `/Users/bot/NeuroLang-nsv3e-<V>`), the bank in
  `engines/neurosynth/examples.yaml`: the engine's own bank, concatenated
  after the shared hand-written `coordinate_meta_analysis` bank (83
  questions) by `extends`, no code needed.
- **E:** C plus #1000's hybrid selection (BM25 fused by RRF with bge-m3
  cosines on Albert), ported locally behind `NL_HYBRID_EXAMPLES` (commit
  `exp/nsv3e-hybrid`, not pushed; no BM25 fallback, every choice logged in
  the run's `hybrid.jsonl`).
- Bench: `scripts/run_nsv3e.sh VARIANT SET MODE` (one run at a time; load
  average logged each minute in `load.log`), `scripts/nsv3e_env.sh`,
  `scripts/nsv3e_table.py` (the tables below), `configs/llm.nsv3.yaml`
  (English, ReAct, BM25, 6 examples, 8 steps, T 0, verify off) and
  `llm.nsv3b-vote.yaml` (×3, Sonnet 5.5 fallback). Golds: those of
  5bce790 (Cognitive-Atlas-first rule, runs/nsv3d.md).

## The distilled bank (`scripts/distilled_bank.py`)

From the 703 kept Sonnet answers of round 2 (441 by DeepSeek agreement, 262
by the Sonnet judge):

| step | agreement | judge | all |
|---|---:|---:|---:|
| kept answers | 441 | 262 | 703 |
| duplicate question (bank or earlier) | 0 | 0 | 0 |
| duplicate query | 1 | 1 | 2 |
| `mentions` for a Cognitive Atlas label with a definition, question not saying mention/term/word (against the CogAt-first golds and #1221) | 38 | 26 | 64 |
| query failing, stopped by the guard (30 s, 4 GB) or without rows on 1a4dafd8, run one at a time | 5 | 1 | 6 |
| bge-m3 cosine > 0.85 to a question of nsv2, v3, fresh or distill-heldout (any language) | 0 | 0 | 0 |
| **bank entries** | **397 (B)** | 234 | **631 (C)** |
| with a trace | 131 | 97 | 228 |

- Hard-coded 6 mm radii the question does not state are written
  `{kernel_radius_mm}`, as in the hand-written bank (98 entries).
- **Leakage:** max cosine of a new entry to an evaluation question
  **0.850** (p2-0787); `scripts/leakage.py` over the whole bank gives 0.850
  (nsv2), 0.845 (v3), 0.867 (fresh): the 0.867 is f-097 against a
  hand-written master entry ("Which studies report an activation in
  hippocampus?"), not a new one.
- **Trace:** the `search_values`/`describe_predicate` steps whose
  observation shows a constant of the final query that the question does
  not spell out; ≤ 3 steps, observations cut to 6 lines. D's prompts carry
  a trace on 24 of 33 dev questions.

## Dev ablation (v3 dev, 33 questions, DeepSeek single, T 0)

| run | n | mean J (exact) | steps | tokens in/out per q | $/q | fallback | invalid | max load | misses by category |
|---|---:|---|---:|---|---:|---:|---:|---:|---|
| A | 33 | 0.848 (28) | 4.0 | 30.7k / 2.24k | 0.0020 | 0/33 | 0 | 17 | cogat_hierarchy: p-049(0.00); cogat_term: dh-029(0.00) p-038(0.00); prob_forward: dh-122(0.00) p-116(0.00) |
| A-r2 | 33 | 0.758 (25) | 3.9 | 32.9k / 3.30k | 0.0024 | 0/33 | 1 | 8 | cogat_hierarchy: p-049(0.00); cogat_term: dh-029(0.00) p-038(0.00); counts: dh-151(0.00); prob_forward: dh-122(0.00) p-116(0.00); schaefer: dh-067(0.00) p-060(0.00) |
| B | 33 | 0.848 (28) | 3.2 | 23.8k / 1.64k | 0.0015 | 0/33 | 1 | 11 | cogat_hierarchy: p-049(0.00); cogat_term: dh-029(0.00) p-038(0.00); prob_forward: dh-122(0.00); schaefer: dh-067(0.00) |
| C | 33 | 0.909 (30) | 3.0 | 23.4k / 1.76k | 0.0015 | 0/33 | 0 | 8 | cogat_hierarchy: p-049(0.00); cogat_term: dh-029(0.00) p-038(0.00) |
| C-r2 | 33 | 0.788 (26) | 3.7 | 30.4k / 2.41k | 0.0020 | 0/33 | 1 | 8 | cogat_hierarchy: p-049(0.00); cogat_term: dh-029(0.00) p-038(0.00); counts: dh-151(0.00); prob_forward: dh-122(0.00); schaefer: dh-067(0.00) p-060(0.00) |
| D | 33 | 0.879 (29) | 3.2 | 25.6k / 2.02k | 0.0017 | 0/33 | 1 | 13 | coactivation: p-130(0.00); cogat_hierarchy: p-049(0.00); cogat_term: p-038(0.00); prob_forward: dh-122(0.00) |
| D-r2 | 33 | 0.848 (28) | 3.6 | 29.3k / 4.33k | 0.0026 | 0/33 | 1 | 5 | coactivation: p-130(0.00); cogat_hierarchy: p-049(0.00); cogat_term: p-038(0.00); prob_forward: dh-122(0.00); schaefer: dh-067(0.00) |
| E | 33 | 0.909 (30) | 3.3 | 25.6k / 2.05k | 0.0017 | 0/33 | 0 | 10 | cogat_hierarchy: p-049(0.00); cogat_term: dh-029(0.00) p-038(0.00) |

- **Noise:** the same variant twice moves by 3–4 exact (A 28/25, C 30/26,
  D 29/28). p-038 and p-049 are missed by all 8 runs (CogAt rule).
- **Reproducible effects:** p-116 (search loop) is missed by both A runs
  and answered by all six bank runs; dh-029 is answered only by D (both
  runs), p-130 missed only by D (both runs): traces +1/−1.
- **Hybrid (E):** chooses different examples from BM25 on every question
  (3.7 of 6 shared on average) and scores as C (30).
- r2 misses dh-151, p-060 (right number of rows, wrong values) and dh-067
  (100 rows, argmax missing) are model errors, not request errors.

**Win threshold, fixed before any test run:** the best variant minus A must
exceed the largest same-variant spread on that set (4 exact on dev).
