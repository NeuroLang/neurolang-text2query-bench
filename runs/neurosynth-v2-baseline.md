# neurosynth-v2 baseline (2026-10-28)

ReAct, Datalog, on `datasets/neurosynth-v2.yaml` (41 held-out questions,
English and French). NeuroLang `feat/llm-text-search-examples` at
ec0b916a (the runs started on test splits after 99709845, which only adds
the feedback server; the agent, prompts and example bank are the same).
Settings of `configs/llm.yaml`: `max_steps` 8, `few_shot_k` 6 (BM25),
temperature 0, 60 s per LLM request. The bench skips the rule comments.

## Dataset

41 questions, dev 20 / test 21. Each tag is split as evenly as it can be:

| tag | dev | test |
|---|---:|---:|
| prob (marginal or conditional over selected_study) | 17 | 15 |
| schaefer | 5 | 5 |
| tian | 4 | 5 |
| destrieux | 3 | 4 |
| free-text (similar_study) | 4 | 3 |
| cogat | 3 | 3 |
| aggregation | 3 | 4 |
| coactivation | 2 | 3 |
| negation | 2 | 3 |
| mni | 2 | 2 |
| simple | 2 | 2 |
| conjunction | 1 | 1 |
| disjunction | 1 | 0 |

- **Leakage.** The highest bge-m3 cosine of a question to a question of
  the example bank is 0.811 (nsv2-40 against the bank's fear/amygdala
  question). The threshold was 0.85; see `scripts/leakage.py`.
- **Gold queries.** All 41 run and return rows (`check-gold`), each in
  under 9 s.
- **Gold changes.** Three golds were changed after the first Sonnet run,
  to follow what their questions ask:
  - nsv2-08 and nsv2-29 ask for titles, so they now return the titles only;
  - nsv2-15 asks for the regions other than the seed.

  All the runs were then scored again (`scripts/reevaluate.py`).

## Scores

| model (provider) | split | n | F1 | exact | valid | runs | steps | calls | tokens/q | s/q |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Sonnet 5.5 (OpenRouter, native tools) | dev | 40 | **0.975** | 98% | 100% | 100% | 3.8 | 3.2 | 202k | 17 |
| Sonnet 5.5 (OpenRouter, native tools) | test | 42 | **0.952** | 95% | 100% | 100% | 3.7 | 3.3 | 204k | 17 |
| Gemma 4 31B (OpenRouter) | dev | 40 | 0.675 | 68% | 95% | 95% | 3.3 | 3.3 | 157k | 38 |
| Gemma 4 31B (OpenRouter) | test | 42 | 0.666 | 64% | 93% | 93% | 3.6 | 3.6 | 171k | 40 |
| Gemma 4 31B (Albert) | test, en | 21 | 0.524 | 52% | 67% | 67% | 2.8 | 2.3 | 88k | 84 |
| DeepSeek V4 Flash 0731 (OpenRouter) | dev | 40 | 0.775 | 78% | 92% | 92% | 5.0 | 5.0 | 210k | 58 |
| DeepSeek V4 Flash 0731 (OpenRouter) | test | 42 | 0.714 | 71% | 90% | 90% | 4.8 | 4.8 | 203k | 49 |
| DeepSeek V4 Flash 0731 (Albert) | test | 42 | 0.738 | 74% | 86% | 88% | 4.6 | 4.6 | 175k | 104 |

Gemma and DeepSeek use the text protocol, Sonnet native tool calls.

- **Gemma on Albert.** The run stopped at Albert's daily cap of 2.46M
  input tokens after 16 of the 21 English test questions. 5 questions
  got HTTP 429 and 2 hit the 60 s request timeout. On the 14 questions
  it answered, its F1 is 0.786, against 0.785 for the same model on
  OpenRouter. OpenRouter is therefore a faithful stand-in for the dev
  split.
- **DeepSeek on Albert.** It hit no quota limit, at 7.3M input tokens.
  On the first pass 9 of its 42 requests timed out. After one retry of
  those, 3 timeouts are left; they count as failures.

### F1 per tag (dev and test together; Albert runs on test only)

| run | aggr. | coact. | cogat | conj. | destrieux | disj. | free-text | mni | neg. | prob | schaefer | simple | tian |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Sonnet | 1.00 | 1.00 | 0.83 | 1.00 | 0.93 | 1.00 | 1.00 | 0.88 | 1.00 | 0.95 | 0.95 | 1.00 | 1.00 |
| Gemma OR dev | 0.17 | 1.00 | 0.83 | 1.00 | 0.67 | 1.00 | 0.50 | 1.00 | 1.00 | 0.71 | 0.70 | 0.50 | 0.50 |
| Gemma OR test | 0.63 | 0.66 | 0.50 | 0.50 | 0.50 | | 0.67 | 0.75 | 1.00 | 0.73 | 0.90 | 0.50 | 0.70 |
| Gemma Albert test (en) | 0.25 | 1.00 | 0.33 | 0.00 | 0.50 | | 0.67 | 0.50 | 0.67 | 0.60 | 0.80 | 0.50 | 0.40 |
| DeepSeek OR dev | 0.33 | 1.00 | 1.00 | 1.00 | 0.33 | 1.00 | 0.75 | 1.00 | 1.00 | 0.74 | 0.80 | 1.00 | 0.62 |
| DeepSeek OR test | 0.88 | 0.50 | 0.50 | 0.50 | 0.75 | | 1.00 | 0.75 | 1.00 | 0.67 | 0.70 | 1.00 | 0.30 |
| DeepSeek Albert test | 0.88 | 0.50 | 0.67 | 1.00 | 0.50 | | 0.83 | 1.00 | 0.83 | 0.67 | 0.70 | 1.00 | 0.60 |

### Failure kinds (answers, `scripts/failure_taxonomy.py`)

| run | exact | LLM error | out of steps | empty | no choice | wrong predicate | wrong value | wrong structure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Sonnet (82) | 79 | 0 | 2 | 0 | 0 | 0 | 1 | 0 |
| Gemma OR dev (40) | 27 | 0 | 2 | 2 | 3 | 3 | 1 | 2 |
| Gemma OR test (42) | 27 | 0 | 5 | 2 | 2 | 2 | 1 | 3 |
| Gemma Albert test (21) | 11 | 7 | 2 | 1 | 0 | 0 | 0 | 0 |
| DeepSeek OR dev (40) | 31 | 0 | 9 | 0 | 0 | 0 | 0 | 0 |
| DeepSeek OR test (42) | 30 | 0 | 10 | 0 | 0 | 2 | 0 | 0 |
| DeepSeek Albert test (42) | 31 | 3 | 5 | 0 | 0 | 0 | 0 | 3 |

No answer failed syntax or validation, and none timed out on the engine.
"No choice" means a probability not taken over `selected_study` (PROB
over stored relations, or a list instead of a probability).

## What fails

**DeepSeek runs out of steps** (9 to 10 answers out of 40 to 42 on
OpenRouter). It spends them on finding the values:

- nsv2-13: seven `search_values` and `describe_predicate` calls look for
  "accumbens" among the Tian labels. These are abbreviations (`NAc core
  rh`), which a text search cannot find. Sonnet writes
  `tian_activated('NAc core rh', s)` at once. Both Gemma and DeepSeek
  lose steps the same way on the caudate (`aCAU lh`) and the putamen.
- Some replies have no `Action:` at all, and the agent spends a step
  reminding it of the protocol.

**Gemma copies the sort notation of `describe_predicate`.** The tool
shows `study_title(study(study_id), text)`, and Gemma writes
`ans(t) :- study_title(study(10022492), t)`. The query runs and returns
no rows, on nsv2-02, in both languages and on both providers. It also
writes `tian(tian_label(l), r)`, which is an arity error, until it runs
out of steps (nsv2-15 and nsv2-22, French).

**Gemma puts stored relations in PROB.** For nsv2-11 (French) it writes
`PROB[destrieux_activated(l, s) // mentions(s, 'face')]`, which leaves
out `selected_study`.

**Sonnet** fails on 3 of 82 answers:

- nsv2-31 and nsv2-34 in French run out of steps on the
  NoValidChaseClass error, an engine problem (see below);
- nsv2-18 in French uses both `'saccade'` and `'saccades'`.

## Engine and prompt problems found (not fixed here)

1. **Every request is about 61k tokens.** The schema summary of the
   system prompt (107k characters) lists 1264 Cognitive Atlas classes as
   predicates (`- http://www.cognitiveatlas.org/...`). A question takes
   about 3 requests, so about 200k tokens. This is why Gemma's Albert
   quota lasts for only about 15 questions. Hiding those classes is the
   cheapest gain in tokens and steps.
2. **The argmax of a probability returns no rows.** Joining the result
   of a PROB with the max aggregated over that same result gives
   nothing, even as a plain product (Destrieux and the term motor):

   ```
   region_probability(l, p) :- PROB[active(l, s) // term_association(s, 'motor')] = p
   best(m) :- AGGREGATE[](region_probability(l, p) @ max(p)) = m
   ans(l, p, m) :- region_probability(l, p), best(m)
   ```

   `best` alone returns 0.5947, and `region_probability` alone returns
   148 rows. The marginal `PROB[active(l, s)]` fails in the same way.
   `prompts.py` teaches exactly this pattern for "the largest …". The
   golds of nsv2-12 and nsv2-36 avoid it with
   `~beaten(l)`. DeepSeek's out-of-steps answers on these two questions
   (on dev) come from this bug.
3. **`similar_study` fails outside the query rule.** With a constant
   text in a rule other than the query, e.g.
   `close(s) :- similar_study('...', s)`, the query raises
   `NoValidChaseClassForStratumException`. A conjunction
   `act(q, s) :- near(s), close(q, s)` fails the same way. This costs
   Sonnet nsv2-31 and nsv2-34 in French.
4. **Albert times out.** With 61k-token prompts, requests to Albert hit
   the 60 s timeout:
   - Gemma: 2 of 16 answers;
   - DeepSeek: 9 of 42 on the first pass.

## Regression set (the 32 old questions, Sonnet)

Sonnet on OpenRouter scores F1 0.757 on the current code, against 0.918
for Sonnet through claude-code on 2026-10-14:

| | n | F1 | exact | steps | tokens/q | s/q |
|---|---:|---:|---:|---:|---:|---:|
| current code | 64 | 0.757 | 75% | 2.9 | 167k | 12 |
| 2026-10-14 | 64 | 0.918 | 89% | 4.1 | | 24 |

- **The new engine guidance explains the drop.** Of the 16 failures:
  - 13 answer with a probability, as `assistant_guidance` asks, where
    the old gold expects the list of studies or a count;
  - 1 uses `similar_study` instead of the term;
  - 2 are ns-029, which the old run also got wrong.

  The old golds predate that guidance: the set needs new golds, or
  should be read as a measure of the conflict.
- **Albert regression run.** It did not fit in Gemma's quota and was not
  run.

## Cost

| run | input tokens |
|---|---:|
| Sonnet, neurosynth-v2 | 16.6M |
| Sonnet, regression | 10.7M |
| Gemma, OpenRouter | 13.5M |
| DeepSeek, OpenRouter | 17.0M |
| Gemma, Albert | 1.85M recorded, cap of 2.46M reached |
| DeepSeek, Albert | 7.3M, no cap hit |

## Reproduce

```bash
source scripts/env.sh
scripts/run_nsv2.sh openrouter runs/nsv2-react-sonnet
scripts/run_nsv2.sh openrouter-gemma runs/nsv2-react-gemma-or-dev --split dev
scripts/run_nsv2.sh albert-deepseek runs/nsv2-react-deepseek-albert-test --split test
python scripts/failure_taxonomy.py datasets/neurosynth-v2.yaml runs/nsv2-react-*
```
