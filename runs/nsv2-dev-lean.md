# neurosynth-v2 dev split, lean schema (2026-10-28)

ReAct, Datalog, dev split of `datasets/neurosynth-v2.yaml` (20 questions
× en/fr). NeuroLang branch `feat/llm-lean-schema` (local, 18cb6e80, on
`feat/llm-text-search-examples` 99709845), installed editable in
`.venv-llmfix`. Same settings as the baseline (`configs/llm.yaml`: 8
steps, 6 BM25 examples, temperature 0). DeepSeek is
`openrouter-deepseek-0731`, the model of the baseline and of Albert.

## What changed in NeuroLang

1. **Schema summary.** Predicates named by a full IRI (the 1264
   Cognitive Atlas classes) are counted in one line per namespace. They
   cannot be written in a query anyway: the grammar only takes IRIs as
   constants. The neurosynth ReAct system prompt goes from 108,991 to
   17,868 characters (`scripts/prompt_size.py`); the schema section from
   99,390 to 7,961.
2. **Plain columns.** Predicates are shown as written in a query,
   `study_title(study_id, text)`, not `study_title(study(study_id),
   text)`. `describe_predicate` shows 3 rows, and a value that is
   neither a string nor a number by its type: `tian('aHIP rh',
   ExplicitVBR(…))` instead of thousands of voxel lines.
3. **search_values.** With a predicate and no match, a column with at
   most 200 values lists them all (`search_values('accumbens',
   'tian_activated')` now gives the 32 Tian labels, `NAc core rh`
   included), else the closest by difflib as before.
4. **Guidance.** The neurosynth `assistant_guidance` spells out the Tian
   abbreviations (NAc nucleus accumbens, CAU caudate, PUT putamen…) and
   says that PROB is taken over rules joining `selected_study(s)`, never
   over stored relations.

## Scores, baseline vs lean (dev, n = 40)

| run | n | F1 | exact | valid | runs | steps | calls | tokens | s/q |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| nsv2-react-sonnet | 40 | 0.975 | 98% | 100% | 100% | 3.8 | 3.2 | 202k | 17 |
| nsv2-dev-lean-sonnet | 40 | 1.000 | 100% | 100% | 100% | 3.6 | 3.1 | 27k | 20 |
| nsv2-react-gemma-or-dev | 40 | 0.675 | 68% | 95% | 95% | 3.3 | 3.3 | 157k | 38 |
| nsv2-dev-lean-gemma-or | 40 | 0.775 | 78% | 100% | 100% | 2.4 | 2.4 | 16k | 29 |
| nsv2-react-deepseek-or-dev | 40 | 0.775 | 78% | 92% | 92% | 5.0 | 5.0 | 210k | 58 |
| nsv2-dev-lean-deepseek-or | 40 | 0.801 | 80% | 90% | 92% | 5.3 | 5.3 | 37k | 45 |

| run | aggregation | coactivation | cogat | conjunction | destrieux | disjunction | free-text | mni | negation | prob | schaefer | simple | tian |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| nsv2-react-sonnet | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.97 | 0.90 | 1.00 | 1.00 |
| nsv2-dev-lean-sonnet | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| nsv2-react-gemma-or-dev | 0.17 | 1.00 | 0.83 | 1.00 | 0.67 | 1.00 | 0.50 | 1.00 | 1.00 | 0.71 | 0.70 | 0.50 | 0.50 |
| nsv2-dev-lean-gemma-or | 0.33 | 1.00 | 0.83 | 1.00 | 0.83 | 1.00 | 0.62 | 1.00 | 1.00 | 0.79 | 0.80 | 0.75 | 0.62 |
| nsv2-react-deepseek-or-dev | 0.33 | 1.00 | 1.00 | 1.00 | 0.33 | 1.00 | 0.75 | 1.00 | 1.00 | 0.74 | 0.80 | 1.00 | 0.62 |
| nsv2-dev-lean-deepseek-or | 0.34 | 1.00 | 0.83 | 1.00 | 0.84 | 1.00 | 0.75 | 1.00 | 1.00 | 0.80 | 0.70 | 0.75 | 0.62 |

| run | exact | llm error | timeout | syntax/validation | out of steps | empty answer | no choice | wrong predicate | wrong value | wrong structure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| nsv2-react-sonnet | 39 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| nsv2-dev-lean-sonnet | 40 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| nsv2-react-gemma-or-dev | 27 | 0 | 0 | 0 | 2 | 2 | 3 | 3 | 1 | 2 |
| nsv2-dev-lean-gemma-or | 31 | 0 | 0 | 0 | 0 | 2 | 0 | 3 | 0 | 4 |
| nsv2-react-deepseek-or-dev | 31 | 0 | 0 | 0 | 9 | 0 | 0 | 0 | 0 | 0 |
| nsv2-dev-lean-deepseek-or | 32 | 0 | 0 | 0 | 7 | 0 | 0 | 1 | 0 | 0 |

Tokens are input + output per question, over all its requests. A
request is now about 7-9k tokens (Gemma 16k over 2.4 calls), against
about 48-61k before.

| run | tokens, dev (40 answers) |
|---|---:|
| Sonnet lean | 1.10M |
| Gemma OR lean | 0.64M (baseline 6.27M) |
| DeepSeek OR lean | 1.47M (baseline 8.42M) |

## What still fails

- **Engine: argmax of a probability** (nsv2-12, nsv2-36). Joining a PROB
  result with its max returns no rows; Gemma answers empty, DeepSeek
  runs out of steps. Being fixed on master.
- **Engine: `similar_study` outside the query rule** (nsv2-26,
  nsv2-35): DeepSeek runs out of steps on NoValidChaseClass and
  "already in the IDB with a different signature" errors. Gemma writes
  `PROB[...// similar_study('...', s)]` without `selected_study`
  (nsv2-26 fr), or calls `cogat_definition` in the query with a helper
  rule taking `q` (nsv2-35 fr, wrong predicate).
- **Counting vs probability** (nsv2-03, "How many studies mention
  smoking?"): Gemma (en) and DeepSeek (fr) give the probability, as the
  guidance asks for every question.
- **Wrong structure, Gemma**: union of the hippocampus parts written as
  two rules but conditioned on stored `mentions` (nsv2-14 fr); topic
  terms conditioned through `close(s)` without the choice (nsv2-28 fr);
  `AGGREGATE[l]` grouped by the label in the max (nsv2-36 fr).
- **DeepSeek nsv2-16 (en)**: its first query
  `schaefer(l, r), startswith(...)` timed out at 30 s on the engine, and
  it then tried 4 rules for the 4 parcels until the steps ran out
  (exact in the baseline).

DeepSeek's out-of-steps answers fall from 9 to 7, and all but nsv2-16
come from the two engine bugs. Gemma's "no choice" answers fall from 3
to 0.

## Albert

Gemma 4 31B on Albert could not be run: the key's daily cap was already
used up (`2460000 input tokens per day exceeded (remaining: 0)` on the
first request). At 16k tokens a question, the cap now allows about 150
questions a day, against about 15 before.

## Reproduce

```bash
VENV=.venv-llmfix scripts/run_nsv2.sh openrouter-gemma runs/nsv2-dev-lean-gemma-or --split dev
VENV=.venv-llmfix scripts/run_nsv2.sh openrouter-deepseek-0731 runs/nsv2-dev-lean-deepseek-or --split dev
VENV=.venv-llmfix scripts/run_nsv2.sh openrouter runs/nsv2-dev-lean-sonnet --split dev
python scripts/failure_taxonomy.py datasets/neurosynth-v2.yaml --split dev \
    runs/nsv2-react-sonnet runs/nsv2-dev-lean-sonnet \
    runs/nsv2-react-gemma-or-dev runs/nsv2-dev-lean-gemma-or \
    runs/nsv2-react-deepseek-or-dev runs/nsv2-dev-lean-deepseek-or
.venv-llmfix/bin/python scripts/prompt_size.py [--dump]
```

`.venv-llmfix` is a copy of `.venv-llmex` whose editable installs point
to the `/Users/bot/NeuroLang-llmfix` worktree.
