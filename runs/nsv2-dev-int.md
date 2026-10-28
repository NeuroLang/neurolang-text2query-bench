# neurosynth-v2 dev split, integrated NeuroLang (2026-10-28)

ReAct, Datalog, dev split of `datasets/neurosynth-v2.yaml` (20 questions
× en/fr), 8 steps, 6 examples, temperature 0. NeuroLang is the local
branch `llm-integration` (worktree `/Users/bot/NeuroLang-llmint`, never
pushed), installed editable in `.venv-llmint`:

- `feat/llm-lean-schema` (lean schema, see [nsv2-dev-lean.md](nsv2-dev-lean.md))
  plus one commit: the neurosynth `assistant_guidance` answers "how
  many / combien" questions with a count (`AGGREGATE[](... @ count(s))`
  over the stored relations, `AGGREGATE[x]` for each x, or over the rows
  of a PROB rule when it counts those with a given probability), every
  other question keeping PROB over `selected_study`;
- merged with `feat/llm-example-retrieval`: examples chosen by BM25
  fused (reciprocal rank) with bge-m3 cosines on Albert
  (`example_retrieval: hybrid` and `embeddings:` in `configs/llm.yaml`);
- the engine fixes of PR #993 (`fix/prob-max-join`, argmax of a
  probability) and PR #994 (`fix/similar-study-constant-rule`),
  cherry-picked with #983 which they sit on (a merge would have pulled
  master's squashed package split over the branch's own).

The gold rows were recomputed on this engine (`check-gold`, 41/41 ok):
none changed. Hybrid retrieval was checked in the traces: the examples
of the prompt differ from BM25's (nsv2-03 en/fr), no "BM25 only"
warning in the logs, and the bank's vectors are cached in
`~/.cache/neurolang/llm/`. The `int-bm25-*` runs differ from `int-*`
only by `example_retrieval: bm25` (`RETRIEVAL=bm25`, config kept in the
run directory).

## Scores (dev, n = 40): baseline → lean → integrated

`nsv2-react-*` is the baseline, `nsv2-dev-lean-*` the lean schema.

| run | n | F1 | exact | valid | runs | steps | calls | tokens | s/q |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| nsv2-react-sonnet all | 40 | 0.975 | 98% | 100% | 100% | 3.8 | 3.2 | 202k | 17 |
| nsv2-dev-lean-sonnet all | 40 | 1.000 | 100% | 100% | 100% | 3.6 | 3.1 | 27k | 20 |
| nsv2-dev-int-sonnet all | 40 | 0.975 | 98% | 100% | 100% | 3.2 | 2.8 | 25k | 15 |
| nsv2-react-gemma-or-dev all | 40 | 0.675 | 68% | 95% | 95% | 3.3 | 3.3 | 157k | 38 |
| nsv2-dev-lean-gemma-or all | 40 | 0.775 | 78% | 100% | 100% | 2.4 | 2.4 | 16k | 29 |
| nsv2-dev-int-bm25-gemma-or all | 40 | 0.850 | 85% | 98% | 98% | 2.4 | 2.4 | 16k | 29 |
| nsv2-dev-int-gemma-or all | 40 | 0.925 | 92% | 98% | 98% | 2.3 | 2.3 | 17k | 34 |
| nsv2-react-deepseek-or-dev all | 40 | 0.775 | 78% | 92% | 92% | 5.0 | 5.0 | 210k | 58 |
| nsv2-dev-lean-deepseek-or all | 40 | 0.801 | 80% | 90% | 92% | 5.3 | 5.3 | 37k | 45 |
| nsv2-dev-int-bm25-deepseek-or all | 40 | 0.925 | 92% | 100% | 100% | 4.5 | 4.5 | 31k | 35 |
| nsv2-dev-int-deepseek-or all | 40 | 0.950 | 95% | 98% | 98% | 4.0 | 4.0 | 28k | 27 |

| run | aggregation | coactivation | cogat | conjunction | destrieux | disjunction | free-text | mni | negation | prob | schaefer | simple | tian |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| nsv2-react-sonnet | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.97 | 0.90 | 1.00 | 1.00 |
| nsv2-dev-lean-sonnet | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| nsv2-dev-int-sonnet | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.97 | 0.90 | 1.00 | 1.00 |
| nsv2-react-gemma-or-dev | 0.17 | 1.00 | 0.83 | 1.00 | 0.67 | 1.00 | 0.50 | 1.00 | 1.00 | 0.71 | 0.70 | 0.50 | 0.50 |
| nsv2-dev-lean-gemma-or | 0.33 | 1.00 | 0.83 | 1.00 | 0.83 | 1.00 | 0.62 | 1.00 | 1.00 | 0.79 | 0.80 | 0.75 | 0.62 |
| nsv2-dev-int-bm25-gemma-or | 0.50 | 1.00 | 1.00 | 1.00 | 0.83 | 1.00 | 0.75 | 1.00 | 1.00 | 0.82 | 0.70 | 1.00 | 0.88 |
| nsv2-dev-int-gemma-or | 0.67 | 0.75 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.91 | 0.70 | 1.00 | 1.00 |
| nsv2-react-deepseek-or-dev | 0.33 | 1.00 | 1.00 | 1.00 | 0.33 | 1.00 | 0.75 | 1.00 | 1.00 | 0.74 | 0.80 | 1.00 | 0.62 |
| nsv2-dev-lean-deepseek-or | 0.34 | 1.00 | 0.83 | 1.00 | 0.84 | 1.00 | 0.75 | 1.00 | 1.00 | 0.80 | 0.70 | 0.75 | 0.62 |
| nsv2-dev-int-bm25-deepseek-or | 0.67 | 1.00 | 0.83 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.91 | 0.80 | 1.00 | 0.88 |
| nsv2-dev-int-deepseek-or | 0.83 | 1.00 | 0.83 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.94 | 0.90 | 1.00 | 0.88 |

| run | exact | llm error | timeout | syntax/validation | out of steps | empty answer | no choice | wrong predicate | wrong value | wrong structure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| nsv2-react-sonnet | 39 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| nsv2-dev-lean-sonnet | 40 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| nsv2-dev-int-sonnet | 39 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| nsv2-react-gemma-or-dev | 27 | 0 | 0 | 0 | 2 | 2 | 3 | 3 | 1 | 2 |
| nsv2-dev-lean-gemma-or | 31 | 0 | 0 | 0 | 0 | 2 | 0 | 3 | 0 | 4 |
| nsv2-dev-int-bm25-gemma-or | 34 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 4 |
| nsv2-dev-int-gemma-or | 37 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 2 |
| nsv2-react-deepseek-or-dev | 31 | 0 | 0 | 0 | 9 | 0 | 0 | 0 | 0 | 0 |
| nsv2-dev-lean-deepseek-or | 32 | 0 | 0 | 0 | 7 | 0 | 0 | 1 | 0 | 0 |
| nsv2-dev-int-bm25-deepseek-or | 37 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 2 |
| nsv2-dev-int-deepseek-or | 38 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 |

Tokens over the 40 answers: Sonnet 1.00M, Gemma 0.68M (bm25 0.65M),
DeepSeek 1.13M (bm25 1.23M). The embeddings cost one bge-m3 request per
question plus the bank once (cached on disk).

## What the integration changed

- **Counts** (nsv2-03, "How many studies mention smoking?"): exact for
  every model in both languages; Gemma (en) and DeepSeek (fr) gave a
  probability on the lean branch.
- **Engine fixes**: DeepSeek no longer runs out of steps on nsv2-12,
  nsv2-26 and nsv2-36 (7 → 1 out of steps); the argmax queries now
  return one row.
- **Retrieval**, bm25 → hybrid on the same code: Gemma 0.850 → 0.925
  (34 → 37 exact), DeepSeek 0.925 → 0.950 (37 → 38 exact, 4.5 → 4.0
  steps, 35 → 27 s/q). With BM25 a French question shares almost no
  word with the English bank, so its scores tie and every French
  question gets the bank's first six examples (pain, terms, language
  or speech...); hybrid picks related ones (nsv2-26 fr: amygdala
  co-activation, superior temporal gyrus, regions of a Cognitive Atlas
  concept). Gemma's bm25-only misses are nsv2-12, -26 and -28 fr
  (wrong structure) and nsv2-18 fr (a 120 s engine timeout, then out
  of steps), all exact with hybrid. These are single runs: Sonnet
  flipped nsv2-18 fr between lean and integrated with no relevant
  change, so ±1-2 questions is run-to-run noise, the size of
  DeepSeek's gain; Gemma's +3 is just above it.
- Sonnet: 39/40, nsv2-18 fr unions `saccade` and `saccades` (wrong
  value; the same miss as in the baseline, exact on the lean run).

## What still fails (integrated, hybrid)

Gemma (OpenRouter):
- nsv2-36 en, fr: the argmax query returns 1 row, the parcel label
  only, without its probability (gold `ans(l, p)`); fr also groups the
  max by label (`AGGREGATE[l]`). A form mismatch: DeepSeek's identical
  query previews the gold parcel, `17Networks RH SalVentAttnA Ins 1`.
- nsv2-21 en: out of steps; after `search_values` it wrote the Action
  Input as multi-line JSON 7 times (text-protocol parse error; the
  error's example is a SQUALL query even in Datalog mode).

DeepSeek (OpenRouter):
- nsv2-36 fr: answers the gold parcel without its probability (form
  mismatch), and conditions `co(l, s)`
  (activation and pain) on pain, which gives the same argmax but no p.
- nsv2-35 fr: out of steps; joins `cogat_definition` with a helper rule
  taking the text `q` (`close(q, s)`), so `study_similarity` gets an
  unbound `q` (UnboundVariablesError): the case PR #994 does not cover.

## Albert

Gemma 4 31B on Albert still answers 429 `2460000 input tokens per day
exceeded (remaining: 0)` (one 5-token request), so neither Albert run
was made; DeepSeek on Albert answers. bge-m3 on Albert served all the
embeddings.

## Reproduce

```bash
VENV=.venv-llmint scripts/run_nsv2.sh openrouter runs/nsv2-dev-int-sonnet --split dev
VENV=.venv-llmint scripts/run_nsv2.sh openrouter-gemma runs/nsv2-dev-int-gemma-or --split dev
VENV=.venv-llmint scripts/run_nsv2.sh openrouter-deepseek-0731 runs/nsv2-dev-int-deepseek-or --split dev
VENV=.venv-llmint RETRIEVAL=bm25 scripts/run_nsv2.sh openrouter-gemma runs/nsv2-dev-int-bm25-gemma-or --split dev
VENV=.venv-llmint RETRIEVAL=bm25 scripts/run_nsv2.sh openrouter-deepseek-0731 runs/nsv2-dev-int-bm25-deepseek-or --split dev
.venv-llmint/bin/python scripts/failure_taxonomy.py datasets/neurosynth-v2.yaml --split dev --examples 20 \
    runs/nsv2-react-sonnet runs/nsv2-dev-lean-sonnet runs/nsv2-dev-int-sonnet \
    runs/nsv2-react-gemma-or-dev runs/nsv2-dev-lean-gemma-or runs/nsv2-dev-int-bm25-gemma-or runs/nsv2-dev-int-gemma-or \
    runs/nsv2-react-deepseek-or-dev runs/nsv2-dev-lean-deepseek-or runs/nsv2-dev-int-bm25-deepseek-or runs/nsv2-dev-int-deepseek-or
```

`.venv-llmint` is a copy of `.venv-llmfix` whose scripts and editable
installs point to `/Users/bot/NeuroLang-llmint`. `configs/llm.yaml` now
has `example_retrieval` and `embeddings`, which the older venvs
(`.venv-llmex`, `.venv-llmfix`) reject: rerun those with the config of
commit 008f477.
