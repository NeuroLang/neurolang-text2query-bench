# neurosynth-v3c: validation of NeuroLang master after the DeepSeek-parity PRs (2026-11-09, INCOMPLETE)

Goal: rerun the nsv3b comparison (runs/nsv3b.md) on upstream master, now that
#1057 (distilled bank), #1104, #1116 (vote, fallback), #1117, #1126, #1127,
#1102 and #1103 are merged. OpenRouter only.

**Stopped by the OpenRouter key limit**: about 13 minutes into the runs every
request got `HTTP 403 Key limit exceeded (total limit) ... $600.03 of $600.00
used; does not reset`. The fresh runs were never started; the nsv2 and v3 runs
were stopped. Only the questions answered before the limit are scored below.

## Code

Upstream master **30db798e** (after #1143), detached worktree
`/Users/bot/NeuroLang-nsv3c`, over `.venv-dsparity` with
`source scripts/nsv3c_env.sh` (PYTHONPATH). Configs as nsv3b:
`configs/llm.nsv3.yaml` (single, temperature 0), `configs/llm.nsv3b-vote.yaml`
(`samples: 3`, `fallback_provider: openrouter`; the agent raises the samples'
temperature to max(T, 0.7) = 0.7, agent.py `_answer`). English, ReAct, BM25,
6 examples, 8 steps, `verify_rounds: 0`. Runs: `scripts/run_nsv3c.sh nsv2|v3|fresh`.

## Leakage (bank of master: 80 questions, #1057 included)

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

## Results (partial)

"clean" = questions none of whose requests got the 403; compared with the nsv3b
run on the same questions (`scripts/clean_subset.py`). Mean Jaccard (exact).

| run | answered | clean | master | nsv3b, same questions |
|---|---:|---:|---|---|
| v3 test, DeepSeek single | 32 | 17 | 0.816 (13) | 0.765 (13) |
| v3 test, DeepSeek ×3 vote + fallback | 19 | 8 | 1.000 (8) | 1.000 (8) |
| v3 test, Sonnet 5.5 single | 32 | 31 | 0.935 (29) | 0.996 (30) |
| nsv2 dev, DeepSeek single | 20 | 14 | 1.000 (14) | 0.929 (13) |
| nsv2 test, DeepSeek single | 21 | 14 | 1.000 (14) | 1.000 (14) |
| nsv2 dev, DeepSeek ×3 vote + fallback | 11 | 6 | 1.000 (6) | 0.833 (5)* |
| nsv2 test, DeepSeek ×3 vote + fallback | 12 | 6 | 1.000 (6) | 1.000 (6)* |

\* against nsv3b's DeepSeek single (nsv3b ran no vote on nsv2).
Sonnet, all 32 (p-186 lost to the 403): 0.906 (29), $0.060/q, 16 s/q.
The fallback counts of the vote runs (10 and 11) are the 403s, not
disagreements: no fallback rate can be given. $/q of the clean single runs:
DeepSeek ≈ $0.001/q (14.5k in, 1.1k out), as in nsv3b.

Changes on the clean questions:
- DeepSeek single, v3 test: dh-052 0 → 1, dh-127 0 → 0.87, dh-117 1 → 0.
- Sonnet, v3 test: dh-127 0.87 → 1, dh-166 1 → 0, p-096 1 → 0.
- nsv2-07 0 → 1 (DeepSeek, single and vote).

## Diagnosis

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

## Remains (needs a working OpenRouter key)

```bash
source scripts/env.sh; source scripts/nsv3c_env.sh
scripts/run_nsv3c.sh nsv2; scripts/run_nsv3c.sh v3; scripts/run_nsv3c.sh fresh
# (remove the partial runs/nsv3c-* first, or pass --resume through run_nsv2.sh)
.venv-dsparity/bin/python scripts/vote_only.py runs/nsv3c-test-deepseek-vote runs/nsv3c-test-deepseek-voteonly
.venv-dsparity/bin/python scripts/reevaluate.py datasets/neurosynth-v3-heldout.yaml runs/nsv3c-test-deepseek-vote runs/nsv3c-test-deepseek-voteonly
.venv-dsparity/bin/python scripts/run_cost.py datasets/neurosynth-v3-heldout.yaml test deepseek=runs/nsv3c-test-deepseek deepseek-vote=runs/nsv3c-test-deepseek-vote sonnet=runs/nsv3c-test-sonnet
```

then fresh with and without f-097, and the fallback rate. Tokens spent here:
DeepSeek 2.3M in / 0.16M out, Sonnet 0.88M in / 0.02M out.
