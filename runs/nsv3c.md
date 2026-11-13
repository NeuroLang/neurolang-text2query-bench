# neurosynth-v3c: baseline of NeuroLang master after the DeepSeek-parity PRs (2026-11-13)

Goal: rerun the nsv3b comparison (runs/nsv3b.md) on upstream master, now that
#1057 (distilled bank), #1104, #1116 (vote, fallback), #1117, #1126, #1127,
#1102, #1103 and #1176 are merged: the step-0 baseline of the distillation plan.
OpenRouter only.

## Code

Upstream master **8532a28b** (0.1a22, after #1176), detached worktree
`/Users/bot/NeuroLang-nsv3c`, over `.venv-dsparity` with
`source scripts/nsv3c_env.sh`. A first attempt on 30db798e stopped at the old
key's $600 limit (its partial runs are kept in `runs/nsv3c-partial-30db798e/`,
its findings below); the restart moved to 8532a28b because #1176 made
`activated` and the `{atlas}_activated` predicates 6 mm (were 3 mm) and the
MNI golds were moved to 6 mm with it (commit 4692a67): a 30db798e engine would
mis-score every MNI and atlas question. Golds recomputed on 8532a28b
(`check-gold`): nsv2 41/41, fresh 32/32; v3 cached by nsv3d on the same commit.

Configs as nsv3b: `configs/llm.nsv3.yaml` (single, temperature 0),
`configs/llm.nsv3b-vote.yaml` (`samples: 3` at 0.7, `fallback_provider:
openrouter` = Sonnet 5.5). English, ReAct, BM25, 6 examples, 8 steps,
`verify_rounds: 0`. DeepSeek = `openrouter-deepseek-0731`. Runs:
`scripts/run_nsv3c.sh nsv2|v3|fresh`, then `vote_only.py`, `reevaluate.py`
(final scoring on the datasets of 4692a67), `nsv2_overlap.py` (Jaccard) and
`run_cost.py`. Gemma on Albert (in the plan) was not run: Albert was reserved
for the nsv3d jobs.

## Results

Mean Jaccard of the rows (exact matches of 32); steps = tool calls per
question; $/q from the traced tokens (DeepSeek $0.0434/$0.30, Sonnet $2/$10
per M in/out; the fallback's replies priced as Sonnet). s/q are not
comparable with nsv3b: the Mac ran up to 30 agents at once (round-2 teacher).

| | v3 test (32) | steps | tok/q | $/q | fresh (32) | steps | tok/q | $/q |
|---|---|---:|---:|---:|---|---:|---:|---:|
| DeepSeek single | 0.840 (26) | 4.1 | 35k | 0.0025 | 0.844 (27) | 4.2 | 35k | 0.0024 |
| DeepSeek ×3 vote | 0.871 (27) | 13.9 | 113k | 0.0072 | 0.875 (28) | 11.6 | 92k | 0.0058 |
| DeepSeek ×3 vote + Sonnet fallback | **0.902 (28)** | 13.9 | 113k | 0.0197 | **0.906 (29)** | 11.6 | 92k | 0.0079 |
| Sonnet 5.5 single | 0.875 (28) | 3.3 | 31k | 0.0668 | 0.845 (27) | 3.6 | 33k | 0.0703 |

Fallback rate: v3 test 3/32 (dh-010, p-008, p-041), fresh 1/32 (f-121),
nsv2 0/41. Without f-097 (cosine 0.867 to a bank question, all four right on
it): fresh single 0.839 (26/31), vote 0.871 (27), vote + fallback 0.903 (28),
Sonnet 0.840 (26).

Regression on neurosynth-v2 (DeepSeek): single dev 0.950 (19/20), test 1.000
(21/21), $0.0016/q; ×3 vote, with or without fallback, the same, $0.0046/q.

Against nsv3b (master before #1176, 3 mm): DeepSeek single v3 0.844 → 0.840,
fresh 0.836 → 0.844; vote + fallback v3 0.906 → 0.902, fresh 0.963 → 0.906;
Sonnet v3 0.996 → 0.875, fresh 0.767 → 0.845. Not like-for-like (kernel radius,
golds and bank changed), so read the table as the new baseline only.

Misses common to every model: dh-166 (probabilistic "not activated": all
answer the empty deterministic query), p-128 (one value per parcel instead of
pairs), dh-010 (`p_a_given_similar` stopped by the memory guard / out of
steps), f-131 and f-066 (gold conventions). Sonnet only: p-096 (P(t ∧ r) for
P(t | r)), f-078/f-102 (ranking for "most often"), f-071. DeepSeek single
only: out of steps on dh-052, p-083, f-048, f-121 (the vote recovers them),
f-173 (voxel-level, 1.1M rows; Sonnet right).

OpenRouter spend of nsv3c (3 datasets): about $6 (Sonnet runs and fallbacks
$4.6, DeepSeek ≈ $1.5).

## Leakage (from the 30db798e attempt; bank unchanged since) (bank of master: 80 questions, #1057 included)

`scripts/leakage.py --openrouter` (bge-m3), highest cosine of a dataset question
to a bank question:

| dataset | max | question → nearest bank question |
|---|---:|---|
| v3 (65) | 0.839 | p-175 "Which studies activate both left subcallosal gyrus and globus pallidus?" |
| fresh (32) | **0.867** | f-097 "Which terms co-occur with activation of hippocampus in a study?" → "Which studies report an activation in hippocampus?" (#1057) |
| nsv2 (41) | 0.840 | nsv2-40 |

Only f-097 is above 0.85, and it is not a copy: it asks for the terms, the bank
question for the studies; what it shares is the definition of the hippocampus
(Tian aHIP, pHIP). No v3 or fresh question, nor a near-copy, is in the bank (an
exact or reworded copy scores above 0.95). Fresh was to be scored with and
without f-097; the fresh runs could not be made.

## Golds (`check-gold` on master)

nsv2 41/41, v3 65/65, fresh 32/32 run and return rows; **no gold changed**
against the nsv3b golds (`scripts/gold_diff.py`, rows rounded to 6 digits).

## Diagnosis (30db798e partial runs)

- **dh-127** (subcortical structures co-activating with hippocampus in injury
  studies): DeepSeek single on master now conditions on hippocampus ∧ injury,
  as the gold, and leaves out the 4 hippocampus parcels (27 of 31 rows, J
  0.87), the reading Sonnet took in nsv3b. The nsv3b misses were P(hip ∧ l |
  injury). Not a bug; whether the seed belongs in the answer is a gold
  convention.
- **dh-166** (gyri and sulci not activated by adolescence studies): DeepSeek
  (single, both nsv3b and master) and now Sonnet answer the regions activated by
  *no* such study, a deterministic query with no rows, and confirm the empty
  answer. The gold is P(not active | adolescence) per region. BM25 now retrieves
  two "Which studies do not mention X?" plain-list examples (one new from #1057)
  and the bank has no example of a probabilistic non-activation. Generic remedy:
  the guidance would say that the regions "not activated" by a topic get the
  probability of not being activated. It is justified only by this test
  question (no dev, fresh or nsv2 question asks it): described, not made.
- **p-128** (networks co-activated in grey-matter studies): lost to the 403 on
  master. In nsv3b, 2 of 3 DeepSeek answers gave per-parcel activation instead
  of pairs; the guidance already says pairs for a network (`co_active(l1, l2,
  s)`, `l1 < l2`), and the fresh question of the same shape (f-133 "Which brain
  regions are co-activated in studies about memory?") was answered right by DeepSeek single and vote in nsv3b: model
  variance, no fix.
- **dh-117** (new miss, lift of a MNI point and "deficit"): DeepSeek took the
  MNI millimetres for voxel indices (`lift('deficit', -28, -22, -14, l)`,
  `brain_mask(-28, -22, -14)`) and ran out of steps. On the way it hit an
  **engine bug**: `check_query` of any yes/no query (`ans() :- ...`) failed with
  `TypeError: object of type 'Constant' has no len()` (dry_run returns a
  placeholder Constant; `query()` took its len). Found in 5 traces of the bench
  (nsv3b fresh ×2, nsv2, dh-after, nsv3c). Fixed in NeuroLang **PR #1144**
  (`fix/dry-run-boolean-query`, regression tests in test_show_ra.py and
  test_validation.py).
- **p-096** (Sonnet, new miss): P(term ∧ putamen) instead of P(term | putamen),
  same rows, other values: model variance at temperature 0.
- Seen in an nsv3b trace, not on master: a rule named `activated` clashes with
  the engine's `activated(i, j, k, s)` ("already in the IDB with different
  signature"); the model renamed it at the next step. No change.

