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
| C-vote | 33 | 0.848 (28) | 10.9 | 86.5k / 7.00k | 0.0116 | 1/33 | 1 | 10 | cogat_hierarchy: p-049(0.00); cogat_term: dh-029(0.00) p-038(0.00); prob_forward: dh-122(0.00); schaefer: dh-067(0.00) |
| D-vote | 33 | 0.818 (27) | 10.6 | 86.3k / 7.04k | 0.0175 | 2/33 | 0 | 7 | coactivation: p-130(0.00); cogat_hierarchy: p-049(0.00); cogat_term: dh-029(0.00) p-038(0.00); prob_forward: dh-122(0.00); schaefer: dh-067(0.00) |

- **Noise:** the same variant twice moves by 3–4 exact (A 28/25, C 30/26,
  D 29/28). p-038 and p-049 are missed by all 8 runs (CogAt rule).
- **Reproducible effects:** p-116 (search loop) is missed by both A runs
  and answered by all six bank runs; dh-029 is answered only by D (both
  runs), p-130 missed only by D (both runs): traces +1/−1.
- **Hybrid (E):** chooses different examples from BM25 on every question
  (3.7 of 6 shared on average) and scores as C (30).
- r2 misses dh-151, p-060 (right number of rows, wrong values) and dh-067
  (100 rows, argmax missing) are model errors, not request errors.

- **Votes (×3 + Sonnet fallback):** C 28, D 27, no better than the
  singles on dev. **C is carried** to test and fresh: the bank alone, no
  code; traces are a wash (+1/−1) and hybrid changes nothing.

**Win threshold, fixed before any test run:** the best variant minus A must
exceed the largest same-variant spread on that set (4 exact on dev).

## Final runs: A (master) against C (+631 distilled entries), v3 test and fresh

`scripts/nsv3e_queue.sh` then `scripts/nsv3e_queue2.sh`, one run at a time,
A and C interleaved. Vote-only rows: `scripts/vote_only.py` +
`reevaluate.py` on the vote runs (their tokens and $ are those of the vote
run). $/q at OpenRouter prices (DeepSeek $0.0434/$0.30 per M, the
fallback's replies as Sonnet $2/$10); the Albert runs cost nothing.

### v3 test (32), DeepSeek on OpenRouter

| run | n | mean J (exact) | steps | tokens in/out per q | $/q | fallback | invalid | max load | misses by category |
|---|---:|---|---:|---|---:|---:|---:|---:|---|
| A single | 32 | 0.906 (29) | 4.0 | 31.4k / 2.65k | 0.0022 | 0/32 | 0 | 4 | coactivation: p-128(0.00); cogat_term: p-041(0.00); free_text: dh-010(0.00) |
| A single r2 | 32 | 0.902 (28) | 3.8 | 28.8k / 3.13k | 0.0022 | 0/32 | 1 | 4 | coactivation: dh-127(0.88) p-128(0.00); cogat_term: p-041(0.00); free_text: p-008(0.00) |
| C single | 32 | 0.906 (29) | 3.7 | 28.8k / 2.82k | 0.0021 | 0/32 | 1 | 4 | coactivation: dh-127(0.00); cogat_term: p-041(0.00); tian: p-096(0.00) |
| C single r2 | 32 | 0.844 (27) | 3.3 | 25.4k / 2.31k | 0.0018 | 0/32 | 1 | 5 | coactivation: dh-127(0.00) p-128(0.00); cogat_term: p-041(0.00); free_text: dh-010(0.00); tian: p-096(0.00) |
| A vote only | 32 | 0.902 (28) | 12.7 | 0.0k / 0.00k | 0.0000 | 1/32 | 1 | 0 | coactivation: dh-127(0.88) p-128(0.00); cogat_term: p-041(0.00); free_text: dh-010(0.00) |
| C vote only | 32 | 0.844 (27) | 10.4 | 0.0k / 0.00k | 0.0000 | 1/32 | 1 | 0 | coactivation: dh-127(0.00) p-128(0.00); cogat_term: p-041(0.00); free_text: dh-010(0.00); tian: p-096(0.00) |
| A vote + fallback | 32 | 0.902 (28) | 12.7 | 99.1k / 7.47k | 0.0124 | 1/32 | 0 | 4 | coactivation: dh-127(0.88) p-128(0.00); cogat_term: p-041(0.00); free_text: dh-010(0.00) |
| C vote + fallback | 32 | 0.844 (27) | 10.4 | 82.4k / 7.26k | 0.0121 | 1/32 | 0 | 4 | coactivation: dh-127(0.00) p-128(0.00); cogat_term: p-041(0.00); free_text: dh-010(0.00); tian: p-096(0.00) |

### fresh (32), DeepSeek on OpenRouter

| run | n | mean J (exact) | steps | tokens in/out per q | $/q | fallback | invalid | max load | misses by category |
|---|---:|---|---:|---|---:|---:|---:|---:|---|
| A single | 32 | 0.688 (22) | 3.6 | 28.2k / 2.42k | 0.0020 | 0/32 | 1 | 4 | coactivation: f-131(0.00) f-133(0.00); cogat_hierarchy: f-048(0.00); cogat_term: f-030(0.00) f-031(0.00); conj_disj: f-173(0.00) f-179(0.00); prob_forward: f-121(0.00); schaefer: f-066(0.00); tian: f-102(0.00) |
| A single r2 | 32 | 0.720 (23) | 4.0 | 30.9k / 3.01k | 0.0022 | 0/32 | 0 | 4 | coactivation: f-131(0.00) f-133(0.00); cogat_hierarchy: f-048(0.00); cogat_term: f-030(0.00) f-031(0.00); conj_disj: f-173(0.00); prob_forward: f-121(0.00); schaefer: f-066(0.00); tian: f-102(0.03) |
| C single | 32 | 0.720 (23) | 3.6 | 27.5k / 2.62k | 0.0020 | 0/32 | 1 | 5 | coactivation: f-133(0.00); cogat_hierarchy: f-048(0.00); cogat_term: f-030(0.00) f-031(0.00); conj_disj: f-173(0.00); destrieux: f-086(0.00); schaefer: f-066(0.00) f-071(0.00); tian: f-102(0.03) |
| C single r2 | 32 | 0.781 (25) | 2.9 | 22.8k / 2.23k | 0.0017 | 0/32 | 1 | 5 | coactivation: f-133(0.00); cogat_hierarchy: f-048(0.00); cogat_term: f-030(0.00) f-031(0.00); schaefer: f-066(0.00) f-071(0.00); tian: f-102(0.00) |
| A vote only | 32 | 0.719 (23) | 11.6 | 0.0k / 0.00k | 0.0000 | 2/32 | 0 | 0 | coactivation: f-131(0.00) f-133(0.00); cogat_hierarchy: f-048(0.00); cogat_term: f-030(0.00) f-031(0.00); conj_disj: f-173(0.00); prob_forward: f-121(0.00); schaefer: f-066(0.00); tian: f-102(0.00) |
| C vote only | 32 | 0.750 (24) | 10.3 | 0.0k / 0.00k | 0.0000 | 0/32 | 0 | 0 | coactivation: f-133(0.00); cogat_hierarchy: f-048(0.00); cogat_term: f-030(0.00) f-031(0.00); conj_disj: f-173(0.00); schaefer: f-066(0.00) f-071(0.00); tian: f-102(0.00) |
| A vote + fallback | 32 | 0.750 (24) | 11.6 | 92.4k / 7.77k | 0.0143 | 2/32 | 0 | 5 | coactivation: f-131(0.00) f-133(0.00); cogat_hierarchy: f-048(0.00); cogat_term: f-030(0.00) f-031(0.00); conj_disj: f-173(0.00); schaefer: f-066(0.00); tian: f-102(0.00) |
| C vote + fallback | 32 | 0.750 (24) | 10.3 | 79.7k / 6.48k | 0.0054 | 0/32 | 0 | 5 | coactivation: f-133(0.00); cogat_hierarchy: f-048(0.00); cogat_term: f-030(0.00) f-031(0.00); conj_disj: f-173(0.00); schaefer: f-066(0.00) f-071(0.00); tian: f-102(0.00) |

### Albert (free): v3 test, then fresh as time allowed

| run | n | mean J (exact) | steps | tokens in/out per q | $/q | fallback | invalid | max load | misses by category |
|---|---:|---|---:|---|---:|---:|---:|---:|---|
| A Albert DeepSeek | 32 | 0.656 (21) | 4.6 | 36.5k / 0.68k | 0.0018 | 0/32 | 3 | 8 | coactivation: dh-127(0.00) p-128(0.00); cogat_hierarchy: dh-052(0.00); cogat_term: p-041(0.00); destrieux: p-079(0.00) p-083(0.00); free_text: dh-010(0.00) p-008(0.00); prob_forward: p-113(0.00); schaefer: dh-062(0.00); tian: p-096(0.00) |
| A Albert DeepSeek r2 | 32 | 0.688 (22) | 4.8 | 37.5k / 0.79k | 0.0019 | 0/32 | 2 | 14 | coactivation: dh-127(0.00) p-128(0.00); cogat_hierarchy: dh-052(0.00); cogat_term: p-041(0.00); free_text: dh-010(0.00) p-008(0.00); prob_forward: dh-117(0.00) p-113(0.00); schaefer: p-058(0.00); tian: p-096(0.00) |
| C Albert DeepSeek | 32 | 0.844 (27) | 4.0 | 31.9k / 0.97k | 0.0017 | 0/32 | 2 | 11 | coactivation: dh-127(0.00) p-128(0.00); cogat_term: p-041(0.00); free_text: dh-010(0.00); tian: p-096(0.00) |
| C Albert DeepSeek r2 | 32 | 0.844 (26) | 4.0 | 31.5k / 0.67k | 0.0016 | 0/32 | 2 | 23 | coactivation: dh-127(0.00); cogat_term: p-041(0.00); free_text: dh-010(0.00); negation: p-162(1.00); prob_forward: dh-117(0.00); tian: p-096(0.00) |
| A Albert Gemma | 32 | 0.812 (26) | 2.3 | 18.6k / 0.50k | 0.0039 | 0/32 | 0 | 8 | cogat_term: p-041(0.00); counts: p-153(0.00); free_text: dh-010(0.00) p-008(0.00); prob_forward: p-108(0.00); tian: p-096(0.00) |
| C Albert Gemma | 32 | 0.840 (25) | 1.8 | 14.4k / 0.39k | 0.0030 | 0/32 | 0 | 8 | coactivation: dh-127(0.88) p-128(0.00); cogat_hierarchy: dh-052(0.00); cogat_term: p-041(0.00); free_text: dh-010(0.00); negation: p-162(1.00); tian: p-096(0.00) |
| A Albert DeepSeek | 32 | 0.720 (23) | 4.2 | 32.2k / 0.84k | 0.0016 | 0/32 | 0 | 46 | coactivation: f-131(0.00) f-133(0.00); cogat_hierarchy: f-048(0.00); cogat_term: f-030(0.00) f-031(0.00); conj_disj: f-173(0.00); schaefer: f-066(0.00) f-071(0.00); tian: f-102(0.03) |
| C Albert DeepSeek | 32 | 0.720 (23) | 4.0 | 31.1k / 0.59k | 0.0015 | 0/32 | 1 | 47 | coactivation: f-133(0.00); cogat_hierarchy: f-048(0.00); cogat_term: f-030(0.00) f-031(0.00); conj_disj: f-173(0.00); free_text: f-011(0.00); schaefer: f-066(0.00) f-071(0.00); tian: f-102(0.03) |

**Sonnet 5.5 reference** (not rerun; master d66a4245, same golds,
runs/nsv3d.md): v3 test 0.875 (28), fresh 0.663 (21), $0.073–0.076/q.

## Reading

| exact, sum of runs | A | C | C − A |
|---|---:|---:|---:|
| dev, DeepSeek single ×2 | 53 | 56 | +3 |
| test + fresh, DeepSeek single ×2 | 102 | 104 | +2 |
| test + fresh, ×3 vote only | 51 | 51 | 0 |
| test + fresh, ×3 vote + Sonnet fallback | 52 | 51 | −1 |
| test, Albert DeepSeek ×2 | 43 | 53 | **+10** |
| fresh, Albert DeepSeek ×1 | 23 | 23 | 0 |
| test, Albert Gemma ×1 | 26 | 25 | −1 |

- **No variant clearly wins.** On OpenRouter DeepSeek every C − A gap is
  within the same-variant spread (dev 4, test 2, fresh 2), and the votes
  are even. The one gap above it, Albert DeepSeek on v3 test (+5 per run,
  reproduced: dh-052, p-008, p-113 right in both C runs and wrong in both A
  runs; A also ran out of steps 2–3 times), does not carry over to fresh
  (23 = 23). Albert's DeepSeek writes far fewer output tokens (0.6–0.8k
  against 2.2–3.3k on OpenRouter with `max_tokens` 8192), so it may
  benefit more from examples; one more fresh pair would tell.
- **Cheaper, not better:** C uses fewer steps on most pairs (dev 3.0–3.7
  vs 3.9–4.0; test 3.3–3.7 vs 3.8–4.0; fresh 2.9–3.6 vs 3.6–4.0) and
  slightly fewer tokens, within run-to-run variation.
- **Traces (D)** fix dh-029 and break p-130 reproducibly on dev: a wash.
  **Hybrid retrieval (E)** picks other examples (3.7 of 6 shared with
  BM25) for the same score as C.
- **What the bank cannot fix:** the CogAt-rule golds (p-038, p-049,
  p-041, f-030, f-031, f-048) and the answer shape (p-128, dh-127, f-133);
  dh-010 is the memory guard.
- **No NeuroLang PR.** The trace field stays on the local branch
  `feat/llm-distilled-bank` (fa0365e2, tests pass), the banks on the local
  `nsv3e-*` branches, the hybrid port on `exp/nsv3e-hybrid`; nothing pushed.

## Caveats

- **Load:** one run at a time, but other sessions shared the Mac: the
  1-minute load average over all runs had median 4.1 and max 47 (fresh
  Albert pair, 46–47; `load.log` of each run). The guard (30 s, 4 GB) may
  have stopped queries it would let through on an idle machine.
- **Noise:** single runs at T 0 move by 1–4 exact of 32–33 on their own;
  most rows are one run.
- The Albert pair on fresh ran under the highest load.

## Spend

OpenRouter key 121.09 → 124.07: **$2.97** (`runs/nsv3e-ledger.jsonl`).
Albert: 6 DeepSeek and 2 Gemma runs of 32 questions (about 1.1 M
Gemma tokens).
