# Distilled examples: Sonnet 5.5 ReAct answers as few-shot examples (2026-11-03)

NeuroLang branch `feat/llm-distilled-examples` on upstream master 75a40cb2
(#1047: the bank is `engines/coordinate_meta_analysis/examples.yaml`),
venv `.venv-distill`, config `configs/llm.master-v0.yaml` (BM25, 6
examples, `verify_rounds: 0`), English, ReAct, temperature 0, OpenRouter
only. Scripts: `scripts/distill.py` (slots, pool, answer, filter,
calibrate, bank), `scripts/run_nsv2.sh` (`DATASET=`), `scripts/leakage.py
--openrouter`, `scripts/nsv2_overlap.py`.

## Pipeline

1. **Pool.** Slot values come from the engine (`distill.py slots`: 250
   topical terms picked by Sonnet among the `mentions` vocabulary, 118
   Cognitive Atlas concepts, 55 concept parents, the 8 Schaefer network
   families, 148 Destrieux labels with English names, the Tian structures,
   study ids and titles, 14 MNI landmarks). Sonnet wrote 12 question
   categories of templates (free text, cogat term, cogat hierarchy,
   Schaefer, Destrieux, Tian, MARG/PROB, co-activation, counts,
   negation, conjunction/disjunction, study titles); 268 questions after
   filling. 3 dropped (2 above bge-m3 cosine 0.85 to a neurosynth-v2
   question, 1 duplicate); **194 kept**, the highest cosine to a
   neurosynth-v2 question being 0.843 (baai/bge-m3 on OpenRouter, en and
   fr questions). Grist: `GRIST_API_KEY` is not set, so no real-user
   questions.
2. **Teacher.** Sonnet 5.5 ReAct, native tool calls, 8 steps, every step
   kept. Budget: Sonnet usage was capped at ~3M tokens, ReAct costs 28k
   tokens a question, so **79 of the 194 questions were answered** (all
   34 held-out ones, then the training ones with the categories
   interleaved: 45 of 160). All 79 ran and returned rows.
3. **Filter.** Per the later decision, every ReAct answer that ran with
   rows goes to the judge (Opus 5.5, `anthropic/claude-opus-5.5`): the
   assistant's own verification instructions, the engine's description,
   schema and guidance, the question, the query and its first 10 rows;
   `VERDICT: yes/no`. **66 kept, 13 rejected** (train 39/6, held-out
   27/7). A first pass had used an independent Sonnet ICL answer
   (temperature 0.7, 10 examples) as the gate, with the judge on
   disagreement (72 ICL answers, 0.67M tokens); it was dropped, and its
   decisions are not used.
   Rejections: 6 are "which studies" questions answered with a single
   probability (`ans(p)`) where the judge wants one probability per
   study (the guidance says a list gets the probability of each); 3 are
   titles questions on stored relations without PROB over
   `selected_study`; 4 others: a count asked for but a list returned
   (pool-047), a count that includes the term itself (pool-146), a
   negation over voxels that drops the voxels never activated
   (pool-161), "term weights" asked but all-1 probabilities (pool-185).
4. **Judge calibration** (`distill.py calibrate`, same single-query
   prompt) on the 41 neurosynth-v2 gold queries and 25 broken variants:
   gold judged right **38/41**, broken judged wrong **23/25**, overall
   61/66 = 92%. By kind: swapped term 4/4, negation dropped 4/4,
   `selected_study` dropped 4/4, query of another question 4/4, wrong
   atlas 4/4, `rdfs:label` for `cogat_term` 1/1, condition (`// B`)
   dropped 2/4. The 3 golds judged wrong are nsv2-08, nsv2-25, nsv2-30
   (title lists with similar_study): the judge is stricter than the
   golds on "list the studies" answers, which is also why it rejects
   9 teacher answers above for their form.
5. **Bank.** 39 training questions (the 6 rejected excluded; none near a
   held-out question, none a duplicate query) appended after the 46
   hand-written entries of `examples.yaml`: free text 4, cogat term 4,
   cogat hierarchy 2, Schaefer 4, Destrieux 4, Tian 4, MARG/PROB 4,
   co-activation 4, counts 4, negation 2, conj/disj 2, study titles 1.
   Highest cosine of an addition to a neurosynth-v2 question: 0.800.
   The bank test (`NEUROLANG_TEST_DATA_DIR`, neurosynth and neurostore)
   passes. No worked traces: the bank has no `trace` field.
6. **Held-out slice** `datasets/neurosynth-distill-heldout.yaml`: the
   27 kept held-out answers as gold. dh-082 and dh-156 got no "before"
   run (judge verdicts changed when the ICL gate was dropped) and are
   left out of the tables: **25 questions**.

## Results (single runs, English)

neurosynth-v2 (dev 20, test 21): before (bank of 46) → after (bank of 85).

| split | model | mean J | exact | steps | tokens/q | s/q |
|---|---|---|---|---:|---:|---:|
| dev | Gemma 4 31B | 0.950 → 0.900 | 19 → 18 | 1.9 → 1.6 | 13k → 11k | 29 → 25 |
| dev | DeepSeek V4 Flash 0731 | 0.950 → 0.950 | 19 → 19 | 4.2 → 3.5 | 29k → 24k | 35 → 30 |
| test | Gemma 4 31B | 0.952 → 0.903 | 20 → 18 | 2.0 → 1.7 | 14k → 11k | 23 → 23 |
| test | DeepSeek V4 Flash 0731 | 0.952 → 0.952 | 20 → 20 | 4.1 → 3.7 | 30k → 26k | 30 → 26 |

Per-question overlap, rows with a miss (after):

| split | question | Gemma | DeepSeek |
|---|---|---|---|
| dev | nsv2-12 | 0.01 (148/1) wrong predicate (was exact) | 1.00 |
| dev | nsv2-36 | 0.00 (1/1) wrong structure | 0.00 (known form mismatch) |
| test | nsv2-15 | 0.97 (32/31) (was exact) | 1.00 |
| test | nsv2-31 | 1.00 | 0.00 (0/1) out of steps |
| test | nsv2-37 | 0.00 (32/32) wrong predicate (was exact) | 1.00 |
| test | nsv2-38 | 0.00 (1/1) no choice (was exact) | 1.00 |

Changed outcomes: Gemma nsv2-12, -15, -37, -38 broke and nsv2-29 was
fixed; DeepSeek none. The benchmark was already at its ceiling; the
distilled bank does not improve it (Gemma -2 exact on each split, within
the 1-2 question run-to-run noise seen before, but not better), and costs
about 15% fewer tokens and steps.

Held-out slice (25 questions of the generated pool, gold = Sonnet
ReAct + judge). Sonnet is the teacher: it scores 1.00 by construction,
a ceiling, not a measurement.

| model | mean J | exact | steps | tokens/q | s/q |
|---|---|---|---:|---:|---:|
| Gemma, before → after | 0.776 → 0.840 | 18 → 21 | 3.2 → 2.9 | 22k → 20k | 31 → 27 |
| DeepSeek, before → after | 0.736 → 0.720 | 17 → 18 | 5.8 → 5.0 | 42k → 37k | 54 → 54 |

Held-out rows with a miss (after): dh-052 (both, wrong structure),
dh-067, dh-087 (Gemma no choice, DeepSeek out of steps), dh-020 (Gemma
out of steps), dh-117, dh-122 (DeepSeek out of steps), dh-127 and dh-151
(DeepSeek). Gemma fixed dh-015, -057, -127; DeepSeek fixed dh-015, -020,
-062, -166 and lost dh-122, -127, -087, -151.

Caveats: single runs at temperature 0 (the ±2 question noise of the
earlier runs applies); the held-out questions come from the same
generator as the bank additions (different slot values, same
templates), so that gain is an upper bound for unseen phrasings; the
"before" DeepSeek run on the slice was resumed after a hang (below) and
its first 11 answers ran on the previous commit of the fix (the same
code but for the guard).

## Engine bug found

`describe_predicate('lift')` (and `relative_risk`) ran a probabilistic
query over every term and voxel, with no time limit: DeepSeek hung 40
minutes in it, twice. Fixed in PR NeuroLang/NeuroLang#1054
(`describe_predicate` runs in a forked child with the query's limits);
the distill branch contains that commit.

## Cost

Sonnet 5.5: 2.97M tokens (pool templates 27k, ReAct teacher 2.30M for 79
answers, ICL 0.67M, dropped). Opus 5.5 judge: 1.14M tokens, 176 calls
(calibration 66, two filter passes). Gemma and DeepSeek runs: about
2 x 4 runs of 25-41 questions at 11-37k tokens.
