# Distillation round 2: pool, Sonnet teacher, DeepSeek ×3 agreement gate, Sonnet judge (2026-11-13)

Plan step 2 (data generation). NeuroLang master 8532a28b (`scripts/nsv3c_env.sh`,
the nsv3c baseline's), `configs/llm.nsv3.yaml` (English, ReAct, BM25, 8 steps,
verifier off; the question left out of the bank). OpenRouter only.

## Pool: `data/distill/pool2.json` (800 questions)

`scripts/distill.py pool --round 2`: Sonnet writes templates per category (2.2×
the target, 40 per request, `data/distill/round2/templates/`), filled from
`data/distill/slots.json` (terms, CogAt concepts, networks, Destrieux names, Tian
structures, titles) plus 36 MNI landmarks. 1760 proposed; dropped 39 near an
evaluation question (bge-m3 cosine > 0.85 against every question, all languages,
of nsv2, v3-heldout, v3-fresh and distill-heldout), 14 duplicates of the bank or
the round-1 pool, 14 duplicates in the pool (> 0.92). **Max cosine of a kept
question to an evaluation question: 0.850.**

Mix: the 12 v3 categories 35 each (420), and the failure types of nsv3c:
answer_shape 100 (pairs, per-region tables), prob_negation 90 ("not activated"
as a probability), mni_point 90 (MNI millimetres), value_search 100 (names to
look up: plain anatomical names, CogAt synonyms, network names). No held-out
slice: v3 test and fresh are the evaluation sets.

## Runs (`scripts/run_round2.sh`)

One engine per run, forked workers (`--workers`), each question in its own
fork killed after 900 s (`given_up`): five Sonnet questions hung in the engine,
out of reach of the assistant's 30 s / 4 GB guard (the main process at 100% CPU
in Python set unions for > 30 min): p2-0283 "How many concepts are there in the
Cognitive Atlas?", p2-0725/0749/0769 "Which Cognitive Atlas concepts are parts
of …?", p2-0751 "studies mentioning either the left cuneus or reaction times".
To be reproduced on the engine (likely planning blow-up, engine bug).

| | answered | ran with rows | given up (engine) | steps | tokens in/out per q | $ |
|---|---:|---:|---:|---:|---:|---:|
| Sonnet 5.5 (teacher, T 0) | 800 | 755 | 5 | 4.4 | 37.6k / 1.0k | 67.1 (0.085/q) |
| DeepSeek sample 0 (T 0.7) | 800 | 721 | 1 | | | 2.8 |
| DeepSeek sample 1 (T 0.7) | 800 | 697 | 1 | | | 2.7 |
| DeepSeek sample 2, only where 0 and 1 split | 136 | 122 | 2 | | | 0.5 |

Sonnet answers that met the engine's limits (a step stopped by the query
guard, given up, or final rows out of time): 46, of which 11 ended without
rows (`sonnet_failed_engine`, the 5 given up included); the other 31 of the 42
Sonnet failures (29 empty answers, 8 invalid, 5 given up in all) are the model's. The Mac ran ~25 agents at once
(load 30-45): part of the guard hits are load, not the queries (see #1203).

## Agreement gate and Sonnet judge (`scripts/agreement_gate.py`)

Accept when Sonnet's query ran with rows and 2 of the DeepSeek answers return
the same rows (`judge_cascade.same_rows`, F1 = 1 both ways). Every disagreement
goes once to Sonnet on OpenRouter with judge_cascade.py's prompt (VERDICT
yes/no; no DeepSeek judge, too weak in the nsv3d calibration).

| category | accepted | disagreement | judge yes | judge no | kept | Sonnet failed | of which engine |
|---|---:|---:|---:|---:|---:|---:|---:|
| answer_shape | 43 | 55 | 52 | 3 | 95 | 2 | 0 |
| coactivation | 15 | 19 | 16 | 3 | 31 | 1 | 0 |
| cogat_hierarchy | 9 | 18 | 10 | 8 | 19 | 8 | 0 |
| cogat_term | 22 | 11 | 10 | 1 | 32 | 2 | 2 |
| conj_disj | 24 | 8 | 5 | 3 | 29 | 3 | 1 |
| counts | 26 | 5 | 3 | 2 | 29 | 4 | 1 |
| destrieux | 19 | 16 | 16 | 0 | 35 | 0 | 0 |
| free_text | 21 | 14 | 12 | 2 | 33 | 0 | 0 |
| mni_point | 47 | 41 | 36 | 5 | 83 | 2 | 0 |
| negation | 19 | 10 | 7 | 3 | 26 | 6 | 2 |
| prob_forward | 24 | 10 | 9 | 1 | 33 | 1 | 0 |
| prob_negation | 61 | 27 | 25 | 2 | 86 | 2 | 0 |
| schaefer | 23 | 12 | 11 | 1 | 34 | 0 | 0 |
| study_titles | 19 | 14 | 9 | 5 | 28 | 2 | 0 |
| tian | 20 | 13 | 12 | 1 | 32 | 2 | 0 |
| value_search | 49 | 44 | 29 | 15 | 78 | 7 | 5 |
| **all** | **441** | **317** | **262** | **55** | **703** | **42** | **11** |

The Sonnet judge says yes to 83% of the disagreements: a self-judge, so the
judge_yes rows are weaker evidence than the agreement rows (90-98% precise in
the calibration); keep them apart when building the bank.

## Files

- `data/distill/pool2.json`, `round2/templates/`
- `round2/react.sonnet.compact.jsonl`: every Sonnet answer, full steps, first
  10 rows and `n_rows`, its gate record; the full answers (rows; 125 MB) and the
  DeepSeek samples stay out of git in `round2/{react.sonnet,deepseek.N}.w*.jsonl`
- `round2/agreement.json` (counts and per-question status),
  `round2/judge.sonnet.jsonl` (verdicts, reasons, tokens)
- `round2/ledger.jsonl` (the key's spend at each stage), `round2/tokens.jsonl`
  (tokens per answer)

## Spend

OpenRouter key usage 20.02 → 120.30 $: **$100.3** for nsv3c and round 2
(Sonnet teacher $67 traced, judge $6.5, DeepSeek $6, nsv3c ≈ $6, pool $1.4;
the rest are answers lost when runs were restarted). $179.7 left on the key.
