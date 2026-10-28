# neurosynth-v2 test split, integrated NeuroLang (2026-10-28)

ReAct, Datalog, **English only**, test split of
`datasets/neurosynth-v2.yaml` (21 questions), 8 steps, 6 examples
(hybrid retrieval: BM25 fused with bge-m3 on Albert), temperature 0.
NeuroLang is the local branch `llm-integration` (worktree
`/Users/bot/NeuroLang-llmint`, venv `.venv-llmint`), as in
[nsv2-dev-int.md](nsv2-dev-int.md), plus:

- **Text protocol** (`feat/llm-lean-schema`, PR #997, cfe396cf): a reply
  cut at `max_tokens` is kept out of the conversation, except for its
  thought, and the model is told it was cut. The parser accepts raw
  newlines in JSON strings, and its error shows a Datalog example in
  Datalog mode. Gemma's nsv2-21 (en) failure was not multi-line JSON,
  which the parser already read. Gemma looped on `(l != l), (l == l)`
  up to the 2048-token limit. The truncated reply went back into the
  history, and at temperature 0 it was copied on each of the next 6
  steps.
- **PR #995** (`perf/schaefer-startswith`): builtins over a single
  deterministic atom are lifted in PROB queries.
- **PR #996** (`fix/magic-sets-prob-comparison`), four magic-sets fixes.
  Each failing query raised `UnboundVariablesError` in
  `study_similarity`, which needs its text bound by magic sets:
  1. A builtin with a constant, `(p > 0)`, was moved first as if it
     seeded magic sets. This is nsv2-35 fr (DeepSeek), whose query is
     safe: without the comparison it runs.
  2. The aggregate of a query head was adorned as bound.
  3. A bound variable was passed into an aggregate, as in
     `top(m) :- AGGREGATE[](sim(s, v) @ max(v)) = m` and
     `... sim(s, v), top(v)`. This is nsv2-29 (Sonnet, Gemma and
     DeepSeek, test).
  4. A rule literal bound only the variables it shared with earlier
     literals, so `cogat_definition('motor control', d)` left `d`
     free for the `similar_study(d, s)` after it. This is nsv2-35 en
     (Gemma, dev).

  All four were engine bugs, not guidance issues.

The gold rows were recomputed on this engine (`check-gold`, 41/41 ok,
longest 7.7 s): none changed. Tests on `llm-integration`: nl_expr +
nl_core + neurolang 2452 passed; neurolang_apps (llm tests included)
1013 passed.

`int1` runs are the same, with fix 1 of #996 only. They are kept
because they show nsv2-29 failing on every model before fixes 2–4.

## Scores (test, English, n = 21)

The baseline (`nsv2-react-*`) is that of
[neurosynth-v2-baseline.md](neurosynth-v2-baseline.md), restricted to
its English answers: `failure_taxonomy.py --split test --lang en`.

| model (provider) | run | F1 | exact | valid | steps | tokens/q | s/q |
|---|---|---:|---:|---:|---:|---:|---:|
| Sonnet 5.5 (OpenRouter) | baseline | 1.000 | 100% | 100% | 3.0 | 177k | 13 |
| | int1 | 0.952 | 95% | 100% | 3.3 | 27k | 14 |
| | **integrated** | **1.000** | 100% | 100% | 2.9 | 24k | 13 |
| Gemma 4 31B (OpenRouter) | baseline | 0.809 | 76% | 95% | 3.0 | 140k | 28 |
| | int1 | 0.905 | 90% | 95% | 2.3 | 16k | 16 |
| | **integrated** | **0.905** | 90% | 100% | 1.8 | 12k | 18 |
| DeepSeek V4 Flash 0731 (OpenRouter) | baseline | 0.857 | 86% | 100% | 4.1 | 174k | 37 |
| | int1 | 1.000 | 100% | 100% | 3.8 | 26k | 21 |
| | **integrated** | **0.952** | 95% | 100% | 3.5 | 23k | 19 |
| DeepSeek V4 Flash 0731 (Albert) | baseline | 0.857 | 86% | 95% | 4.5 | 170k | 99 |
| | int1 | 0.952 | 95% | 100% | 4.3 | 27k | 33 |
| | **integrated** | **0.904** | 86% | 95% | 4.6 | 28k | 30 |
| Gemma 4 31B (Albert) | baseline (16 of 21 answered before the cap) | 0.524 | 52% | 67% | 2.8 | 88k | 84 |
| | integrated | not run: daily cap still exhausted | | | | | |

F1 per tag (integrated, test, English):

| run | aggr. | coact. | cogat | conj. | destrieux | free-text | mni | neg. | prob | schaefer | simple | tian |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Sonnet | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| Gemma OR | 1.00 | 1.00 | 0.67 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.50 | 1.00 |
| DeepSeek OR | 1.00 | 0.67 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.93 | 1.00 | 1.00 | 0.80 |
| DeepSeek Albert | 1.00 | 0.99 | 1.00 | 1.00 | 1.00 | 0.67 | 1.00 | 0.67 | 0.87 | 0.60 | 1.00 | 1.00 |

Tokens over the 21 answers: Sonnet 0.49M, Gemma 0.25M, DeepSeek 0.48M
(OpenRouter) and 0.59M (Albert), against 3.7M, 2.9M, 3.7M and 3.6M in
the baseline. The int1 run on Albert DeepSeek used another 0.57M.

## What still fails (integrated)

Gemma (OpenRouter):
- nsv2-02, empty answer: `study_title('10022492', t)` quotes the study
  id, an integer.
- nsv2-33, wrong predicate: it takes the labels with `rdfs:label` of a
  Cognitive Atlas IRI instead of `cogat_term`, which the gold uses.

DeepSeek (OpenRouter):
- nsv2-15, out of steps: it looks for the caudate among the Tian labels
  (`aCAU lh`, an abbreviation that a text search cannot find). It also
  calls `describe_predicate` with `predicate` instead of `name`, and
  sends one empty reply, its output budget spent on reasoning.

DeepSeek (Albert):
- nsv2-20, out of steps: it repeats the same two `search_values` calls
  (SalVentAttn, Default) until it runs out of steps.
- nsv2-27, wrong predicate: it conditions on the term `future`
  (`mentions`) instead of the free-text `similar_study`.
- nsv2-15, F1 0.98, wrong structure: it keeps the seed region, which
  the question excludes.

The misses vary between runs on the same code: DeepSeek OpenRouter
went 21 → 20 exact and Albert 20 → 18 between int1 and integrated, on
questions none of the fixes touches (nsv2-15, -20, -27). Treat ±1–2
questions as run noise.

## Dev split, English: regression check

| run | F1 | exact | steps | tokens/q | s/q |
|---|---:|---:|---:|---:|---:|
| Gemma OR, dev-int (before) | 0.900 | 90% | 2.1 | 17k | 41 |
| Gemma OR, dev-int2 (after) | **0.950** | 95% | 1.9 | 13k | 24 |
| DeepSeek OR, dev-int (before) | 1.000 | 100% | 3.6 | 25k | 24 |
| DeepSeek OR, dev-int2 (after) | **0.950** | 95% | 3.9 | 26k | 22 |

Gemma's nsv2-21 (the token-limit loop) is now exact, and so is its
nsv2-35 in the int2 run. The only miss left for either model is
**nsv2-36**, reported separately because its gold and metric await a
decision. Both return the right argmax parcel without its probability,
against the gold `ans(l, p)`. DeepSeek's nsv2-36 en was exact before,
a single-run flip. Without nsv2-36, both models are 19/19 on English dev.

## Albert

Gemma 4 31B on Albert still answers 429 `2460000 input tokens per day
exceeded (remaining: 0)` (5-token probes, twice). DeepSeek on Albert
ran both test runs without hitting a limit (10 requests/min, one job at
a time), at about 28k tokens a question.

## Reproduce

```bash
VENV=.venv-llmint scripts/run_nsv2.sh openrouter runs/nsv2-test-int-sonnet --split test --lang en
VENV=.venv-llmint scripts/run_nsv2.sh openrouter-gemma runs/nsv2-test-int-gemma-or --split test --lang en
VENV=.venv-llmint scripts/run_nsv2.sh openrouter-deepseek-0731 runs/nsv2-test-int-deepseek-or --split test --lang en
VENV=.venv-llmint scripts/run_nsv2.sh albert-deepseek runs/nsv2-test-int-deepseek-albert --split test --lang en
VENV=.venv-llmint scripts/run_nsv2.sh openrouter-gemma runs/nsv2-dev-int2-gemma-or --split dev --lang en
VENV=.venv-llmint scripts/run_nsv2.sh openrouter-deepseek-0731 runs/nsv2-dev-int2-deepseek-or --split dev --lang en
.venv-llmint/bin/python scripts/failure_taxonomy.py datasets/neurosynth-v2.yaml --split test --lang en --examples 20 \
    runs/nsv2-react-sonnet runs/nsv2-test-int-sonnet runs/nsv2-react-gemma-or-test runs/nsv2-test-int-gemma-or \
    runs/nsv2-react-deepseek-or-test runs/nsv2-test-int-deepseek-or \
    runs/nsv2-react-deepseek-albert-test runs/nsv2-test-int-deepseek-albert runs/nsv2-react-gemma-albert-test
```

The last `--lang en` overrides the script's `--lang en fr`.
`failure_taxonomy.py --lang` keeps the answers of one language.
