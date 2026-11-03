# neurosynth-v2: verifier and Cognitive Atlas fix (2026-11-03)

NeuroLang branch `fix/llm-verifier-conditional` (worktree
`/Users/bot/NeuroLang-verifix`, 57e2a619 on upstream master 7437e9c5).
Baseline: `runs/nsv2-master.md` (81298847). Between the two, master
only gained #1026 (semi-naive perf) and `Agent.explain`; the prompts
were identical. ReAct, Datalog, English, 8 steps, 6 BM25 examples,
temperature 0, OpenRouter only. Venv `.venv-verifix`: a copy of
`.venv-master` repointed to the worktree. Configs: `configs/llm.master.yaml`
(verify_rounds 1) and `configs/llm.master-v0.yaml` (verify_rounds 0).

## Changes

1. Back-translation prompt: `PROB[A // B] = p` (and `r(PROB) :- A // B`)
   is P(A | B), the share of the cases of B that are cases of A, not the
   joint and not P(B | A). Verification prompt: judge the conditions
   from what the query returns, never from the text of its rows (a
   title can contain a word that its study does not `mention`); "how
   likely is a study that does B to do A" is P(A | B), "both A and B"
   the joint.
2. `assistant_guidance` (coordinate_meta_analysis): Cognitive Atlas
   classes are named by `cogat_term` (lower case), to find a class and
   to answer with one, not by `rdfs:label`/`skos:prefLabel`;
   `cogat_subclass_of(x, c)` holds for the x below c. The engine's REPL
   examples (not in the LLM prompt) used `rdfs:label` and now use
   `cogat_term`. Nothing was added to the example bank.

## Results

| split | model | verify | mean J | exact | rejections (false) | tokens/q | s/q |
|---|---|---:|---:|---:|---:|---:|---:|
| test | Gemma 4 31B OR, master | 1 | 0.951 | 19/21 | 2 (2) | 24k | 36 |
| test | Gemma 4 31B OR, fix | 1 | 1.000 | 21/21 | 4 (4) | 24k | 36 |
| test | Gemma 4 31B OR, fix | 0 | 1.000 | 21/21 | – | 13k | 22 |
| test | DeepSeek V4 Flash 0731 OR, master | 1 | 0.952 | 20/21 | 1 (1) | 40k | 51 |
| test | DeepSeek V4 Flash 0731 OR, fix | 1 | 1.000 | 21/21 | 0 | 37k | 40 |
| test | DeepSeek V4 Flash 0731 OR, fix | 0 | 0.952 | 20/21 | – | 27k | 22 |
| dev | Gemma 4 31B OR, master | 1 | 0.950 | 19/20 | 2 (2) | 24k | 33 |
| dev | Gemma 4 31B OR, fix | 1 | 0.950 | 19/20 | 1 (1) | 22k | 42 |
| dev | DeepSeek V4 Flash 0731 OR, master | 1 | 0.950 | 19/20 | 0 | 37k | 63 |
| dev | DeepSeek V4 Flash 0731 OR, fix | 1 | 0.950 | 19/20 | 0 | 42k | 46 |

Runs: `runs/nsv2-{test,dev}-verifix-{gemma,deepseek}-or`,
`runs/nsv2-test-verifix-v0-{gemma,deepseek}-or`.

Changed outcomes, test, verify 1 against master:

- nsv2-33 fixed for both: `cogat_term(x, t)` instead of `rdfs:label`.
- nsv2-08 fixed for Gemma: it was rejected twice again, but kept
  the gold query (`~mentions(s, 'default mode')`), and the cap of
  one round accepted it.

Dev: no outcome changed; nsv2-36 is still the argmax without its
probability for both models.

verify 0 against verify 1 (test): DeepSeek nsv2-15 ran out of steps
on the Tian names before any final answer (the Oct 28 failure).
The verifier was not involved, so this is run noise.

## Verifier rejections after the fix

DeepSeek: 0 on test and dev (master: 1 test, 4 on Albert, all false).
The joint misreading of `//` is gone.

Gemma: 5, all false, none changed an outcome:

- test nsv2-08 ×2: still judged from the row title "…a default mode
  of brain function" (in a 1-question smoke run, Gemma accepted after
  that wording).
- test nsv2-15, nsv2-17, dev nsv2-07: the back-translation still
  inverts the conditional (P(seed | region), P(term | network), "a
  study activating the region is also a study that mentions…"). On
  nsv2-17 it also reads Schaefer's `Cont` as "contralateral"; the
  back-translation does not see the guidance that spells it out.
  The 1-question smoke runs on nsv2-14, -17 and -31 read `//` right.

Helpful rejections after the fix: 0 out of 5. Over the master runs
there were 2 helpful ones (DeepSeek on Albert, nsv2-27 and -40), out of 14.

## Recommendation

Keep the fix: it removes DeepSeek's false rejections and the nsv2-33
miss. The verifier still does more harm than good on these models. On
OpenRouter it caught nothing after the fix: 5 false rejections and 0
helpful ones. Exact is 21 + 21 with it against 21 + 20 without, a
difference of one out-of-steps run before any verification. It costs
+11k (Gemma) and +10k (DeepSeek) tokens per question and 1.6–1.8× the
time. Recommend `verify_rounds: 0` as the default, with 1 as an opt-in.
The default was not changed.

## Reproduce

```bash
export VENV=.venv-verifix
for s in test dev; do
  CONFIG=configs/llm.master.yaml scripts/run_nsv2.sh openrouter-gemma runs/nsv2-$s-verifix-gemma-or --split $s --lang en
  CONFIG=configs/llm.master.yaml scripts/run_nsv2.sh openrouter-deepseek-0731 runs/nsv2-$s-verifix-deepseek-or --split $s --lang en
done
CONFIG=configs/llm.master-v0.yaml scripts/run_nsv2.sh openrouter-gemma runs/nsv2-test-verifix-v0-gemma-or --split test --lang en
CONFIG=configs/llm.master-v0.yaml scripts/run_nsv2.sh openrouter-deepseek-0731 runs/nsv2-test-verifix-v0-deepseek-or --split test --lang en
.venv-verifix/bin/python scripts/nsv2_overlap.py datasets/neurosynth-v2.yaml --split test \
    Gemma-OR=runs/nsv2-test-verifix-gemma-or,runs/nsv2-test-master-gemma-or \
    DeepSeek-OR=runs/nsv2-test-verifix-deepseek-or,runs/nsv2-test-master-deepseek-or
```
