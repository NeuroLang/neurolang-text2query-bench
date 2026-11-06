# neurosynth-v3: DeepSeek V4 Flash against Sonnet 5.5 on hand-checked held-out questions (2026-11-06)

Goal: DeepSeek V4 Flash 0731 (OpenRouter, provider `openrouter-deepseek-0731`,
text tool protocol) answering the NeuroLang assistant's neurosynth questions
as well as Sonnet 5.5, OpenRouter only. English, ReAct, Datalog, 8 steps,
6 BM25 examples, temperature 0, `verify_rounds: 0`.

## The question set: `datasets/neurosynth-v3-heldout.yaml`

65 English questions with hand-checked gold Datalog, split dev (33) / test
(32) by category (`scripts/assign_splits.py`, the pool category as the only
tag). All 65 golds run and return rows on master 8921ae82 (`check-gold`,
`scripts/query_server.py` + `scripts/query_golds.py`).

| category | dev | test | from distill held-out | new |
|---|---:|---:|---:|---:|
| coactivation | 3 | 3 | 2 | 4 |
| cogat_hierarchy | 1 | 1 | 1 | 1 |
| cogat_term | 3 | 3 | 3 | 3 |
| conj_disj | 2 | 2 | 1 | 3 |
| counts | 2 | 3 | 2 | 3 |
| destrieux | 3 | 3 | 2 | 4 |
| free_text | 4 | 4 | 4 | 4 |
| negation | 2 | 2 | 1 | 3 |
| prob_forward | 4 | 4 | 4 | 4 |
| schaefer | 4 | 4 | 4 | 4 |
| study_titles | 2 | 1 | 0 | 3 |
| tian | 3 | 2 | 1 | 4 |

- **25 questions of `neurosynth-distill-heldout`** (gold: Sonnet's ReAct
  answer accepted by the Opus judge). Each gold was read against its question
  and the engine. Changes:
  - dh-052 names the class by `cogat_term(c, 'fixation')` instead of its
    IRI, and scores only the winning subclass (`gaze`), not its count.
  - dh-067 groups the parcels into the networks of the guidance (`VisCent`
    and `VisPeri` apart; the old gold merged them into a `Vis` that no
    question or guidance names), and scores only the winning network.
  - dh-020: the question is reworded to the gold's text, "judging the
    intentions of other people" ("other people's" cannot be written in a
    Datalog string, so every model had to paraphrase, and any paraphrase
    selects other studies).
  - dh-057, dh-062, dh-087 ("which studies"): the study column only. The
    probability of each study is 1/N whatever the query, so it is not scored;
    an answer with it still scores 1. The rows also changed with master: the
    peaks of the studies of UNKNOWN space are no longer converted from
    Talairach (#1085), 4519 → 4490 and 313 → 312 studies (checked: the
    probabilistic and deterministic forms agree on master).
  - The other 19 golds are kept as they are.
- **40 new questions** of the distillation pool that no model had answered
  (`data/distill/pool.json`), 3-4 per category, gold written by hand following
  the guidance and the bank and checked on the engine (row counts and first
  rows read for sanity). Left out: questions above 0.85 cosine to the bank, and
  questions without rows on the engine (no study mentions a subclass of
  skill, reasoning or knowledge).
- **Grist**: `GRIST_API_KEY` is not set; no user-flagged questions.
- **Leakage** (`scripts/leakage.py --openrouter`, bge-m3): highest cosine of
  a v3 question to a bank question 0.814 (master bank, p-038), 0.840 to the
  #1057 distilled bank (p-175).

Conventions of the golds: every question but a count is answered over
`selected_study` as the guidance asks; "which studies" keeps the study column;
an argmax keeps the winner; a free-text topic is the question's own words in
`similar_study`.

## Code

- **before**: upstream master 8921ae82 (`.venv-dsbase`, worktree
  `/Users/bot/NeuroLang-dsbase`), `configs/llm.master-v0.yaml` (DeepSeek
  `max_tokens` 4096).
- **after**: branch `fix/llm-deepseek-parity` (NeuroLang PR, below) with
  #1103 (parser) cherry-picked, `configs/llm.nsv3.yaml` (= master-v0 with
  DeepSeek `max_tokens` 8192), `.venv-dsrun` / worktree
  `/Users/bot/NeuroLang-dsrun`.
- Both include the two commits of the open #1054 (`describe_predicate` under
  the query's time limit): without it DeepSeek hung in
  `describe_predicate('relative_risk')` on the first baseline run.
- Not included: #1102 (sorted ids change the cache key: the cache, rebuilt
  here in master's order, would go stale again).

Environment fixes on the way, before any run counted:

1. **The studies' embeddings were stale** (engine bug, fixed in #1102): #1085
   reordered the `study` relation and the cache key hashes the ids in order,
   so every free-text query re-embedded the 14,371 abstracts and was killed
   by the 30 s limit (all `similar_study` answers of a first, aborted run
   timed out). Rebuilt with `python -m neurolang_apps.utils.text_embeddings`.
2. **The cached nsv2 golds predate #1085**: scoring a master run with
   `datasets/neurosynth-v2.gold.json` gave DeepSeek 0.33/0.39 mean J with the
   right row counts (all activation probabilities moved). `check-gold` was run
   again on master; nsv2 numbers below use the new golds (the old cache is not
   in git).

## Results (single runs, English, temperature 0)

v3 **dev** (33), the split the fixes were made on:

| run | DeepSeek V4 Flash mean J | exact | steps | tokens/q | s/q |
|---|---:|---:|---:|---:|---:|
| before (master) | 0.758 | 25 | 5.1 | 42k | 58 |
| round 1 | 0.926 | 29 | 4.3 | 32k | 35 |
| round 2 (final code) | **0.970** | **32** | 4.5 | 35k | 41 |
| *Sonnet 5.5, master (reference)* | *0.879* | *29* | 3.7 | 28k | 24 |

Sonnet ran on master only (token budget): two of its four dev misses (p-160,
p-165) are the "which studies" single probability that the bank taught and
round 1 fixed, so DeepSeek r2 against Sonnet-on-master is not a parity
measure. p-116's r2 "exact" comes from the out-of-steps fallback (the last
query with rows).

v3 **test** (32), run once, both models on the final code:

| model | mean J | exact | steps | tokens/q | s/q | $/q |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek V4 Flash, before (master) | 0.781 | 25 | 5.6 | 43k | 56 | 0.0036 |
| DeepSeek V4 Flash, final | 0.781 | 25 | 4.6 | 38k | 54 | 0.0033 |
| Sonnet 5.5, final | **0.996** | **31** | 3.3 | 27k | 18 | 0.060 |

DeepSeek's test misses (final): dh-117 (the Tian left hippocampus instead of
the question's MNI point), dh-127 (grouped by structure, plausibly nudged by
the new "a structure is all its parts" sentence; Sonnet 0.87), dh-166, p-008,
p-083, p-186 (out of steps: search loops, p-186 the same `search_values`
six times), p-128 (per parcel, not pairs). Before → final: 4 fixed
(dh-010, dh-020, dh-052, p-035) and 4 lost (dh-166, p-083, p-186: search
loops; p-128: per parcel); the net is zero.

neurosynth-v2 regression check (English, DeepSeek, fresh golds):

| split | before (master) | final |
|---|---|---|
| dev (20) | 0.900, 18 exact | 0.950, 19 exact |
| test (21) | 1.000, 21 exact | 1.000, 21 exact |

## Root causes and fixes

DeepSeek misses on v3 dev before the fixes (8), and the reply-level
failures behind them:

| cause | evidence | fix |
|---|---|---|
| reasoning tokens count in `max_tokens` | 15 of 169 replies empty (5 at the 4096 cap); OpenRouter probe: `reasoning_tokens` in `completion_tokens` | `max_tokens` 8192 (`llm.example.yaml`, `configs/llm.nsv3.yaml`); 16384 only lets loops run longer (three 16k empty replies, 60-80 s each) |
| empty replies from the provider | replaying 8 of them: 7 answer; backends vary (Wafer, DigitalOcean, Venice, PrimeIntellect); `reasoning.max_tokens` 2048 made it worse (8/20 empty vs 3/20), `effort: low` too | the agent asks an empty reply again once, without spending a step |
| text-protocol variants not parsed | `<Action: x>`, `<Action>x</Action>`, `<final_answer>`, a reply starting with an echoed `Observation:`, `Action Input: "tian"`; dh-062 (distill runs) looped 7 times on one | `_KEYWORD_LINE` takes tags; the hallucinated observation is cut only after the action; a lone JSON string is the argument of a one-argument tool |
| parser bug | dh-067: `n('VisCent', l) :- ...` is a parse error | engine PR #1103 |
| bank contradicts guidance | p-160, p-175 (and Sonnet p-160, p-165): "Which studies …" answered `ans(p)` as the bank's 6 "which studies" examples do, while the guidance asks a probability per study | the examples answer `ans(s, p)` |
| free-text topic searched for | dh-015: 8 `search_values` on "imagining future events" | guidance: the text is the question's words, no stored value holds it |
| "lift" undefined | dh-122: the engine's voxel-wise `relative_risk`/`lift` tried | guidance: lift of A given B = P(A \| B) / P(A), from PROB rules |
| Destrieux abbreviations | p-080: "transverse collateral" vs `collat transv` | guidance lists them |
| slow query form | p-130: `startswith` on `schaefer_activated` in two seed rules, 36.8 s (> 30 s limit); the label-rule form 3.0 s | guidance: label rules on `schaefer(l, r)`; engine perf (below) |
| atlas of "brain areas" | dh-015 r1: Destrieux ∪ Schaefer ∪ Tian | guidance: no atlas named → Destrieux |
| Tian parts | p-099 r1: putamen = `aPUT` only | guidance: a structure is all its parts |

Round 2 left dh-067 (grouping 100 parcels into networks, out of steps; Sonnet
answers per parcel).

## What remains

- **Search loops** are DeepSeek's main failure on test (4 of 7 misses), with
  identical repeated calls (10 of 115 tool calls on test, 1-2 on dev). Next
  fix: answer a repeated identical call with "you already ran this; its result
  is above" instead of running it again (not done: found on test).
- **`p_a_given_similar` exceeds the assistant's 4 GB query memory** (test
  dh-010; the bank's "holding information in mind" example uses it); the same
  probability written inline with PROB fits. Sonnet rewrites it; DeepSeek
  loops. Engine memory issue, not investigated.
- **Engine performance** (no issue opened: not authorised from here):
  - a Cognitive Atlas–derived condition in a voxel-wise conditional: p-049's
    gold, 58 s; the same rows with `mentions(s, 'valence')`, 3.5 s; with a fact
    `w('valence')`, 5.8 s; the closure alone 0.9 s, `PROB[term_study(s)]`
    alone 2.8 s;
  - a union of choice-joined rules with `startswith` inline on
    `schaefer_activated` (p-130 above): one rule + label rule 3.0 s, one rule
    with inline `startswith` 8.6 s, two rules with label rules 13.3 s, two
    rules inline 36.8 s.
- The dev-to-test gap: dev went 25 → 32 but test 25 → 25; at temperature 0
  through varying OpenRouter backends, single runs move by several questions.
  Several fixes (atlas default, Tian parts) were prompted by single dev
  questions.

## Tokens and cost

| | runs | tokens | cost |
|---|---|---:|---:|
| Sonnet 5.5 | dev base (33), test final (32), an aborted 2-question run | ≈ 1.9M | ≈ $4.1 |
| DeepSeek V4 Flash | dev base, r1, r2, test base, test final, nsv2 base, nsv2 final (+ an aborted 16k-token r1, replays) | ≈ 9.5M | ≈ $0.8 |

## Reproduce

```bash
# gold rows
VENV=.venv-dsbase; .venv-dsbase/bin/t2q-bench --dataset datasets/neurosynth-v3-heldout.yaml check-gold
# before / after
VENV=.venv-dsbase CONFIG=configs/llm.master-v0.yaml DATASET=datasets/neurosynth-v3-heldout.yaml \
  scripts/run_nsv2.sh openrouter-deepseek-0731 runs/nsv3-dev-base-deepseek --split dev --lang en
VENV=.venv-dsrun CONFIG=configs/llm.nsv3.yaml DATASET=datasets/neurosynth-v3-heldout.yaml \
  scripts/run_nsv2.sh openrouter-deepseek-0731 runs/nsv3-test-final-deepseek --split test --lang en
VENV=.venv-dsrun CONFIG=configs/llm.nsv3.yaml DATASET=datasets/neurosynth-v3-heldout.yaml \
  scripts/run_nsv2.sh openrouter runs/nsv3-test-final-sonnet --split test --lang en
.venv-dsbase/bin/python scripts/nsv2_overlap.py datasets/neurosynth-v3-heldout.yaml --split test \
  DeepSeek=runs/nsv3-test-final-deepseek,runs/nsv3-test-base-deepseek Sonnet=runs/nsv3-test-final-sonnet
# reply-level failures of a run, step by step
.venv-dsbase/bin/python scripts/trace_steps.py runs/nsv3-dev-base-deepseek dh-015
```

`scripts/query_server.py DIR` keeps an engine built and runs every `DIR/*.dl`
(`scripts/query_client.sh NAME QUERY`, `scripts/query_golds.py DATASET DIR`):
how the golds were written and timed.
