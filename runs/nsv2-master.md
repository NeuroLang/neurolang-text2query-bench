# neurosynth-v2 on NeuroLang master (2026-11-03, 81298847)

ReAct, Datalog, **English only**, dev (20) and test (21) splits of
`datasets/neurosynth-v2.yaml`, 8 steps, 6 examples, temperature 0.

## Setup

- NeuroLang: upstream `master` at **81298847** (#1027, 2026-11-02),
  detached worktree `/Users/bot/NeuroLang-benchmaster`. It has #997 (lean
  schema), #996 (magic sets), #995, #993/#994, the count guidance, #973
  (back-translation verifier) and #1003 (Albert/OpenRouter DeepSeek and
  Gemma providers); it does not have #1000 (example retrieval).
- Venv `.venv-master`: a copy of `.venv-llmint` with its scripts and
  `.pth` files repointed, then `uv pip install -e` of the four packages
  and the bench. The imports resolve to `NeuroLang-benchmaster`.
- Config `configs/llm.master.yaml`: `configs/llm.yaml` without
  `example_retrieval`/`embeddings` (so **BM25** examples, against hybrid
  on Oct 28), `comment_rules: false` (master defaults it to true),
  `verify_rounds: 1` (master's default). Run with
  `CONFIG=configs/llm.master.yaml VENV=.venv-master scripts/run_nsv2.sh ...`.
- Gold: `check-gold` 41/41 ok, **no gold row changed** (row-by-row diff
  against the Oct 28 cache). nsv2-08 took 32 s, against 7.7 s at most
  on Oct 28, but next to a run building its engine. Alone it takes
  8.6 s (2.2 s warm), so this is not a regression.

## Overlap

J = |pred ∩ gold| / |pred ∪ gold| over the bench's normalised rows,
under its best column alignment. `rows` in results.json is the raw row
count, before the projection on the gold columns removes duplicates, so
J comes from precision and recall: J = p·r / (p + r − p·r) = F1 / (2 − F1).
Cells are J (rows/gold rows); R*n* = *n* verifier rejections. Steps are
the agent's tool steps; the verifier steps are not counted.
`scripts/nsv2_overlap.py` prints these tables.

### Dev (n = 20): questions where some model has J < 1

| question | Sonnet | Gemma OR | DeepSeek OR | cause |
|---|---|---|---|---|
| nsv2-36 | 1.00 (1/1) | 0.00 (1/1) | 0.00 (1/1) | Gemma and DeepSeek: right argmax parcel, but without its probability (gold `ans(l, p)`). This is the known form mismatch, the same as on Oct 28. |

### Test (n = 21): questions where some model has J < 1

| question | Sonnet | Gemma OR | DeepSeek OR | Gemma Albert | DeepSeek Albert | cause |
|---|---|---|---|---|---|---|
| nsv2-08 | 1.00 (565/565) | 0.97 (548/565) R1 | 1.00 (565/565) R1 | 0.97 (548/565) R1 | 1.00 (565/565) | **The verifier rejected the gold-equivalent query.** One returned title contains "default mode" ("…a default mode of brain function"), but `mentions` is a TF-IDF threshold. Gemma then excluded more terms (`'default'` and `'mode'` on OR; `'default'` and `'default network'` on Albert, out of steps, as the fallback query): wrong value. Both tried `regexp(title, …)` first and got an internal TypeError. DeepSeek OR ran out of steps after the rejection, and its fallback was the correct query. |
| nsv2-29 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 (1/1) | DeepSeek Albert: out of steps. 4 `describe_predicate` calls on `study_similarity`/`similar_study` fail with UnboundVariablesError (an old tool bug, also on Oct 28). It found the study but not its title; the fallback answers the id. |
| nsv2-33 | 1.00 (21/21) | 0.00 (21/21) | 0.00 (21/21) | 0.00 (21/21) | 0.00 (0/21) | Wrong predicate: `rdfs:label` ('Spatial memory') instead of `cogat_term` ('spatial memory'). The verifier accepted it (DeepSeek OR: "unclear"). DeepSeek Albert: out of steps, repeating `search_values 'memory'` on rdfs:label/skos:prefLabel. |

DeepSeek Albert first hit three request timeouts (60 s) on nsv2-11, -13
and -40. These were asked again with `--resume` (twice for nsv2-13). The
first pass is kept as `answers.first.json`/`results.first.json` (16/21
exact).

## Summary per model

| split | model | mean J | exact | steps | verify calls | rejections | tokens/q | s/q |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| dev | Sonnet 5.5 (OpenRouter) | 1.000 | 20/20 | 3.1 | 20 | 0 | 35k | 27 |
| dev | Gemma 4 31B (OpenRouter) | 0.950 | 19/20 | 2.2 | 21 | 2 | 24k | 33 |
| dev | DeepSeek V4 Flash 0731 (OpenRouter) | 0.950 | 19/20 | 4.0 | 20 | 0 | 37k | 63 |
| test | Sonnet 5.5 (OpenRouter) | 1.000 | 21/21 | 2.8 | 21 | 0 | 34k | 25 |
| test | Gemma 4 31B (OpenRouter) | 0.951 | 19/21 | 2.3 | 23 | 2 | 24k | 36 |
| test | DeepSeek V4 Flash 0731 (OpenRouter) | 0.952 | 20/21 | 4.5 | 21 | 1 | 40k | 51 |
| test | Gemma 4 31B (Albert) | 0.951 | 19/21 | 2.0 | 22 | 3 | 22k | 30 |
| test | DeepSeek V4 Flash 0731 (Albert) | 0.905 | 19/21 | 4.8 | 21 | 6 | 39k | 129 |

Run totals: dev Sonnet 0.71M tokens, Gemma 0.48M, DeepSeek 0.75M.
Test Sonnet 0.72M, Gemma OR 0.51M, DeepSeek OR 0.85M, Gemma Albert
0.46M, DeepSeek Albert 0.82M (+0.70M for the first pass).

## Against 2026-10-28 (`nsv2-*-int*`)

Earlier runs: dev `nsv2-dev-int-sonnet`, `nsv2-dev-int2-{gemma,deepseek}-or`;
test `nsv2-test-int-*`; Gemma Albert has no Oct 28 run, so it is
compared with the baseline `nsv2-react-gemma-albert-test`.

| split | model | exact Oct 28 → master | tokens/q | s/q |
|---|---|---|---|---|
| dev | Sonnet | 20 → 20 | 25k → 35k | 15 → 27 |
| dev | Gemma OR | 19 → 19 | 13k → 24k | 24 → 33 |
| dev | DeepSeek OR | 19 → 19 | 26k → 37k | 22 → 63 |
| test | Sonnet | 21 → 21 | 24k → 34k | 13 → 25 |
| test | Gemma OR | 19 → 19 | 12k → 24k | 18 → 36 |
| test | DeepSeek OR | 20 → 20 | 23k → 40k | 19 → 51 |
| test | DeepSeek Albert | 18 → 19 | 28k → 39k | 30 → 129 |
| test | Gemma Albert (baseline) | 11 → 19 | 88k → 22k | 84 → 30 |

Questions that changed outcome:

- Dev: none, for any model.
- Gemma OR test: nsv2-02 fixed: the study id is no longer quoted, so
  the answer is no longer empty. nsv2-08 broke, after the verifier's
  rejection (see above).
- DeepSeek OR test: nsv2-15 fixed; it had run out of steps on the Tian
  abbreviations. nsv2-33 broke: it now uses `rdfs:label`, which the
  verifier did not catch.
- DeepSeek Albert test: three fixed. nsv2-15 had kept the seed
  region. nsv2-20 had repeated its searches. nsv2-27 was fixed **by the
  verifier**, which rejected `mentions(s, 'future')`, the Oct 28 miss;
  the agent switched to `similar_study`. Two broke: nsv2-29 (out of
  steps, see above) and nsv2-33 (out of steps).
- Gemma Albert against the baseline: 8 llm errors or out-of-steps
  answers of the capped baseline are now exact. nsv2-08 broke (verifier).

Apart from the two verifier cases, the flips are of the ±1–2 run-noise
size seen on Oct 28. They also mix with the switch from hybrid to BM25
example retrieval.

## Verifier impact (verify_rounds = 1)

14 rejections over the 8 runs (dev 2, test 12). With one round, a
second "no" is overridden and the answer is accepted.

- **Helpful (2):** DeepSeek Albert nsv2-27 (a term instead of free
  text) and nsv2-40 (a conditional `PROB[A // B]` where the question
  asks for the joint "both … and …"). Both were then fixed.
- **Rejected the gold query, nsv2-08 (3):** harmful for Gemma OR and
  Gemma Albert. DeepSeek OR survived the same rejection only through
  the out-of-steps fallback.
- **False, without effect (9):** the back-translation misreads
  `PROB[A // B]`, either as the joint probability (DeepSeek: nsv2-11 ×2,
  -17, -27) or as P(B | A) (Gemma: nsv2-14 ×2, -17, -31 ×2). The cap of
  one round let each correct answer through.
- Missed: nsv2-33's `rdfs:label` in every model that got it wrong.

Cost: 2 more calls per question, +10–17k tokens per question, and
about twice the time per question on OpenRouter.

## Broken / notes

- `describe_predicate` on `study_similarity`/`similar_study` raises
  UnboundVariablesError (nsv2-29; also on Oct 28).
- `regexp(title, pattern)` in a query gives "Internal error —
  TypeError: RegionSolver.function_regexp() takes 2 positional
  arguments". The model can reach a region builtin with the wrong
  arity, and gets an internal error rather than a clear one.
- Albert DeepSeek: 4 timeouts of the 60 s request limit. There was no
  429 from either Albert model: both answered a 5-token probe, and
  Gemma's daily cap was not hit (0.46M).
- Bench: `--ids` naming no question of the `--split` asks every
  question instead of none.

## Reproduce

```bash
export CONFIG=configs/llm.master.yaml VENV=.venv-master
.venv-master/bin/t2q-bench --dataset datasets/neurosynth-v2.yaml check-gold
for s in dev test; do
  scripts/run_nsv2.sh openrouter runs/nsv2-$s-master-sonnet --split $s --lang en
  scripts/run_nsv2.sh openrouter-gemma runs/nsv2-$s-master-gemma-or --split $s --lang en
  scripts/run_nsv2.sh openrouter-deepseek-0731 runs/nsv2-$s-master-deepseek-or --split $s --lang en
done
scripts/run_nsv2.sh albert-gemma runs/nsv2-test-master-gemma-albert --split test --lang en
scripts/run_nsv2.sh albert-deepseek runs/nsv2-test-master-deepseek-albert --split test --lang en  # + --resume after timeouts
.venv-master/bin/python scripts/nsv2_overlap.py datasets/neurosynth-v2.yaml --split test \
    Sonnet=runs/nsv2-test-master-sonnet,runs/nsv2-test-int-sonnet \
    Gemma-OR=runs/nsv2-test-master-gemma-or,runs/nsv2-test-int-gemma-or \
    DeepSeek-OR=runs/nsv2-test-master-deepseek-or,runs/nsv2-test-int-deepseek-or \
    Gemma-Albert=runs/nsv2-test-master-gemma-albert,runs/nsv2-react-gemma-albert-test \
    DeepSeek-Albert=runs/nsv2-test-master-deepseek-albert,runs/nsv2-test-int-deepseek-albert
```

`failure_taxonomy.py` now leaves verifier steps out of the step count.
It counts an answer as accepted only when no verifier rejection follows
its final answer.
