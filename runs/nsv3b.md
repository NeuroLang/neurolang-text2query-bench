# neurosynth-v3b: DeepSeek V4 Flash ×3 vote + Sonnet fallback (2026-11-07)

Goal: DeepSeek V4 Flash 0731 (OpenRouter) as good as Sonnet 5.5, OpenRouter only.
English, ReAct, Datalog, 8 steps, 6 BM25 examples, `verify_rounds: 0`.

## Code

Worktree `/Users/bot/NeuroLang-nsv3b` (local branch `bench-nsv3b`): upstream master
95aee786 + NeuroLang #1104 (DeepSeek parity: plain-list "which studies", repeated
identical tool call not run again) + #1117 (magic sets: a query constant for a head
variable restricts the body, `p_a_given_similar` 4.2 → 0.9 GB) + #1116 (`samples`
vote for ReAct, `fallback_provider`) + #1054 (describe under the query limits).
Run over `.venv-dsparity` with `source scripts/nsv3b_env.sh` (PYTHONPATH).

- single: `configs/llm.nsv3.yaml` (temperature 0)
- ×3 vote + fallback: `configs/llm.nsv3b-vote.yaml`: `samples: 3` (temperature 0.7),
  `fallback_provider: openrouter` (Sonnet 5.5, temperature 0) when no result has
  2 of the 3 answers or none is valid. The vote-only answers are those of the same
  run, the fallback replaced by the query the vote kept (`scripts/vote_only.py`).
- Golds recomputed with this code (`check-gold`): nsv2 41/41, v3 65/65, fresh 32/32.

## Results

Mean Jaccard of the rows (exact matches); $/question from the traced tokens
(DeepSeek $0.0434/$0.30, Sonnet $2/$10 per M in/out, `scripts/run_cost.py`, the
fallback's replies priced as Sonnet). s/q: up to four runs shared the machine.

| | v3 test (32) | $/q | s/q | fresh (32) | $/q | s/q |
|---|---|---:|---:|---|---:|---:|
| DeepSeek single | 0.844 (27) | 0.0021 | 36 | 0.836 (26) | 0.0029 | 41 |
| DeepSeek ×3 vote | 0.875 (28) | 0.0063 | 95 | **0.963 (30)** | 0.0069 | 88 |
| DeepSeek ×3 vote + Sonnet fallback | 0.906 (29) | 0.0110 | 95 | **0.963 (30)** | 0.0090 | 88 |
| Sonnet 5.5 single | **0.996 (31)** | 0.0625 | 20 | 0.767 (24) | 0.0620 | 18 |

Fallback rate: v3 test 2/32 (p-008: no valid answer → Sonnet right; p-083: right
before and after), fresh 1/32 (outcome unchanged).

Regression, DeepSeek single on neurosynth-v2: dev 0.900 (18/20), test 1.000 (21/21),
$0.0019 and $0.0012/q (before #1104: 0.900/0.950 dev, 1.000 test).

## Reading

- v3 test: the vote fixes nothing that needs a different model: dh-127 (grouped
  by structure, 3 rows for 31) and p-128 (per parcel, not pairs) are wrong by a
  majority of the three DeepSeek answers, so the fallback is never asked; dh-166
  is empty. Sonnet answers all three.
- fresh: Sonnet is below DeepSeek. Its misses are mostly conventions of the golds:
  "most often" kept as the winner (f-078, f-102: Sonnet ranks every region), the
  lift for "raise the probability" (f-121), a term instead of the free-text topic
  (f-011, f-155 the reverse), the lift for "co-activated" (f-131). DeepSeek single
  misses are mostly out of steps (f-179, f-121) and one missing `selected_study`
  (f-061); the vote recovers them.
- Cost: ×3 vote + fallback is 1/6-1/7 of Sonnet's cost per question, 4-5 times
  slower; the Sonnet fallback is $0.0047/q (test) and $0.0021/q (fresh) of it.
- Caveats: the fresh golds' conventions were written with the #1104 guidance, and
  3 of Sonnet's 8 fresh misses are convention calls (argmax, P(both) vs lift): the
  fresh Sonnet number is not a parity measure. The vote samples run at temperature
  0.7, the single runs at 0: part of the vote's gain may be the temperature.

## Fresh golds spot-check

All 32 read against the question and the guidance conventions (plain lists for list
questions, PROB for probability questions, AGGREGATE for counts). One correction:
f-066 ("Which terms are associated with activation in the central visual network?")
was P(term | network); the guidance answers an association with a ratio, so the gold
is the lift P(term | network) / P(term). Judgement calls kept: f-131 (P(both) for
"is X co-activated with Y"), f-078/f-102 (argmax keeps the winner).

## Reproduce

```bash
source scripts/env.sh; source scripts/nsv3b_env.sh
DATASET=datasets/neurosynth-v3-heldout.yaml scripts/run_nsv2.sh openrouter-deepseek-0731 runs/nsv3b-test-deepseek --split test --lang en
DATASET=datasets/neurosynth-v3-heldout.yaml CONFIG=configs/llm.nsv3b-vote.yaml scripts/run_nsv2.sh openrouter-deepseek-0731 runs/nsv3b-test-deepseek-vote --split test --lang en
DATASET=datasets/neurosynth-v3-heldout.yaml scripts/run_nsv2.sh openrouter runs/nsv3b-test-sonnet --split test --lang en
# same with datasets/neurosynth-v3-fresh.yaml (no --split), runs/nsv3b-fresh-*
.venv-dsparity/bin/python scripts/vote_only.py runs/nsv3b-test-deepseek-vote runs/nsv3b-test-deepseek-voteonly
.venv-dsparity/bin/python scripts/reevaluate.py datasets/neurosynth-v3-heldout.yaml runs/nsv3b-test-deepseek-voteonly
.venv-dsparity/bin/python scripts/nsv2_overlap.py datasets/neurosynth-v3-heldout.yaml --split test Vote=runs/nsv3b-test-deepseek-voteonly VoteFB=runs/nsv3b-test-deepseek-vote
.venv-dsparity/bin/python scripts/run_cost.py datasets/neurosynth-v3-heldout.yaml test deepseek-vote=runs/nsv3b-test-deepseek-vote
```

Tokens: Sonnet ≈ 1.9M (two single runs + 3 fallbacks); DeepSeek ≈ 9.7M.
