# neurosynth-v3d: Cognitive Atlas first for cognitive concepts (2026-11-13)

(Not the same experiment as `runs/nsv3d-step1.md`, the Albert DeepSeek runs. These runs
are `runs/nsv3d-cogat-*`.)

## Rule (user decision)

A question that names a cognitive process, task or concept ("studies about working
memory", "regions for response inhibition", "the n-back task") and does not say
mention, term or word is answered as follows:

1. look the concept up in the Cognitive Atlas: `search_values` over `cogat_term`
   (lower-case labels);
2. if it is found, use its definition, `cogat_definition('<term>', d)` with
   `similar_study(d, s)` (SPECTER2), joined in the queried rule;
3. if it is not found, use the question's own words with `similar_study`;
4. use `mentions(s, t)` only when the question says mention, term or word, or asks
   about the vocabulary.

The probability, list and count conventions are unchanged.

"Found" means that the label itself, or its singular, is in the atlas, and not a
longer label (`scripts/cogat_lookup.py` shows what `search_values` returns).
Examples: `emotion regulation` gives only `emotional regulation task`, so it is not
found; `recollection` and `speech` are not found; `emotions` is found as `emotion`.
Topics that are not cognitive concepts (anatomy, disorders, populations, stimuli)
stay on `mentions`.

## Code

- NeuroLang PR #1221 (branch `feat/llm-cogat-first`, worktree
  `/Users/bot/NeuroLang-cogatfirst`), from upstream master d66a4245:
  - the guidance paragraph rewritten as the rule;
  - 15 bank examples converted, plus one new example (the n-back task);
  - docs and changelog.
- Master arm: d66a4245, detached worktree `/Users/bot/NeuroLang-cogatmaster`.
- Both arms ran over `.venv-dsparity` with the same configs as nsv3b/c:
  - `configs/llm.nsv3.yaml` (single, temperature 0);
  - `configs/llm.nsv3b-vote.yaml` (3 samples, Sonnet 5.5 fallback).
- English, ReAct, BM25, 8 steps, `verify_rounds: 0`.
- Runs: `scripts/run_nsv3d_cogat.sh nsv2|v3|fresh`, which runs both arms of a set at
  the same time.
  - `branch-v3-sonnet` was rerun alone: its first start found no
    `OPENROUTER_API_KEY` while `~/.zshrc` was being edited.
- The machine was heavily loaded by other sessions (load 20–80).

## Golds rewritten under the rule (old → new; `check-gold` on the branch: nsv2 41/41, v3 65/65, fresh 32/32)

| id (split) | question | old | new | why |
|---|---|---|---|---|
| p-038 (v3 dev) | Is the left amygdala activated by studies on choice? | `PROB[active // mentions 'choice']` | `cogat_definition('choice', d)`, `p_active_given_close(d, p)` | `choice` is a label |
| p-041 (v3 test) | Which studies about efficiency report an activation within 5 mm of MNI (40, -50, 44)? | `near(s), mentions(s, 'efficiency')` | `cogat_definition('efficiency', d), similar_study(d, s), near(s)` | `efficiency` is a label (judgement call) |
| dh-122 (v3 dev) | How much does emotion regulation increase the chance of activating right FFA? | lift via `mentions 'emotion regulation'` | `P(near \| close('emotion regulation')) / P(near)` | not found (only `emotional regulation task`), so its words |
| f-030 (fresh) | Which gyri and sulci are activated by studies about navigation? | `// mentions 'navigation'` | `cogat_definition('navigation')` + `close(q, s)` | label |
| f-031 (fresh) | … subcortical regions … about arousal? | `// mentions 'arousal'` | `cogat_definition('arousal')` + close | label |
| f-048 (fresh) | Which brain regions are activated by studies about any kind of knowledge? | `kind(t), mentions(s, t)` | `kind(t), cogat_definition(t, d), similar_study(d, s)` | label plus subclasses: union of the definitions' studies (runs in 12 s) |
| f-078 (fresh) | Which gyri and sulci does retrieval activate most often? | argmax `// mentions 'retrieval'` | argmax over `cogat_definition('retrieval')` + close | label |
| f-102 (fresh) | Which subcortical parcels are most often activated by studies on recollection? | argmax `// mentions 'recollection'` | argmax over `close('recollection')` | not found, so its words |
| f-133 (fresh) | Which brain regions are co-activated in studies about memory? | pairs `// mentions 'memory'` | pairs `// close(d)`, `cogat_definition('memory', d)` | label |

These stay on `mentions` (judgement calls; they make up the "about-term" subset below):
- not cognitive concepts:
  - dh-127 injury, dh-166 adolescence, dh-117 deficit;
  - p-058 premotor, p-068 frontal lobe, p-079 parahippocampal (anatomy);
  - f-071 depressive (disorder);
  - p-083 sentences, f-155 emotional stimuli (stimuli);
  - f-114 "studies on auditory" (a modality adjective);
- word-like: dh-107 (behavioural/sensorimotor) and p-116 (syntactic).

Every question that says mention, term or word keeps `mentions` (p-049, dh-052,
dh-034, …). nsv2 has no question that names a concept without "mention", so no
nsv2 gold changed.

## Results

Mean Jaccard (exact matches); $/q from the traces (DeepSeek $0.0434/$0.30, Sonnet
$2/$10 per M in/out; the fallback's tokens are priced as Sonnet; `scripts/run_cost.py`).
Both arms are scored with the rewritten golds.

| run | nsv2 dev (20) | nsv2 test (21) | v3 test (32) | fresh (32) | $/q nsv2 / v3 / fresh |
|---|---|---|---|---|---|
| DeepSeek single, master | 0.950 (19) | 1.000 (21) | 0.781 (25) | 0.703 (22) | 0.0015 / 0.0031 / 0.0033 |
| DeepSeek single, branch | 0.950 (19) | 1.000 (21) | 0.747 (23) | 0.688 (22) | 0.0018 / 0.0036 / 0.0035 |
| DeepSeek ×3 + fallback, master | 0.950 (19) | 1.000 (21) | 0.902 (28) | 0.750 (24) | 0.0046 / 0.0163 / 0.0150 |
| DeepSeek ×3 + fallback, branch | 0.950 (19) | 1.000 (21) | **0.934 (29)** | 0.751 (24) | 0.0056 / 0.0103 / 0.0197 |
| Sonnet 5.5 single, master | | | 0.875 (28) | 0.663 (21) | – / 0.0726 / 0.0757 |
| Sonnet 5.5 single, branch | | | 0.846 (27) | **0.751 (24)** | – / 0.0810 / 0.0771 |

Fallback rate (vote runs):
- master: nsv2 0/41, v3 2/32, fresh 2/32;
- branch: nsv2 0/41, v3 1/32, fresh 4/32.

### By subset (v3 test + fresh): concept (7) / about-term (10) / rest (47)

`scripts/nsv3d_cogat_usage.py`; mean Jaccard (exact):

| run | concept, master → branch | about-term, master → branch | rest, master → branch |
|---|---|---|---|
| DeepSeek single | 0.14 (1) → 0.43 (3) | 0.55 (5) → 0.49 (4) | 0.87 (41) → 0.81 (38) |
| DeepSeek ×3 + fallback | 0.14 (1) → 0.58 (4) | 0.99 (9) → 0.79 (7) | 0.89 (42) → 0.89 (42) |
| Sonnet single | 0.03 (0) → 0.58 (4) | 0.90 (9) → 0.60 (6) | 0.85 (40) → 0.87 (41) |

### How the concept questions are answered (7 per run, from the steps)

| run | master | branch |
|---|---|---|
| looked up CogAt (`search_values` over `cogat_term`, or a query on `cogat_term`/`cogat_definition`) | 2/21 (f-048 hierarchy only) | **21/21** |
| final query follows the rule (definition + `similar_study` if found; words if not) | 0/21 | 16/21 |
| DeepSeek single (branch) | – | 5/7 (2 timed out, final = the lookup query) |
| DeepSeek ×3 + fallback (branch) | – | 6/7 |
| Sonnet single (branch) | – | 5/7 (2 kept `mentions`: f-048 hierarchy, f-078 retrieval) |

Sonnet uses `search_values` over `cogat_term`. DeepSeek queries
`cogat_definition` directly.

## Reading

- **The rule is followed.** On the branch, every model looks the concept up for
  every concept question (21/21; master 0/21 uses the definition). The concept subset
  goes from 0.03–0.14 to 0.43–0.58.
  - Most remaining concept misses are not about the rule:
    - "most often" ranked instead of argmax (f-102 Sonnet and vote; known from nsv3b);
    - the hierarchy question f-048, answered with the definition of `knowledge`
      alone, or with `mentions` of the subclasses;
    - DeepSeek timeouts (below).
- **Over-application costs the about-term subset.** Topics that are not concepts get
  the words with `similar_study`:
  - p-058 "premotor" (DeepSeek and Sonnet), dh-166 "adolescence" (Sonnet);
  - descriptions get mapped to a CogAt class: dh-020 "judging the intentions of other
    people" → `theory of mind` (DeepSeek), dh-010 "being socially excluded in a
    ball-tossing game" → `cyberball task` (Sonnet);
  - the guidance's gate ("topics that are no cognitive concept … stay on mentions")
    is not enough on its own;
  - net effect on all questions: Sonnet fresh +0.09, the vote v3 +0.03, DeepSeek
    single −0.03 (v3) and −0.02 (fresh), Sonnet v3 −0.03 (28 → 27 exact); nsv2
    unchanged.
- **Engine findings.**
  - **Wrong results (fixed):** `RESAMPLE` replicates of a PROB over a rule that uses
    another choice rule were wrong. Flattening a query did not rename apart a rule's
    head variables (`a(s, s)` queried as `a(c, s)` dropped the rest of the body).
    Fixed in NeuroLang PR #1212, with tests under two hash seeds.
    - The bank's Bayes-factor-with-CI example is written flat, so it was
      right even before #1212.
  - **Slow (not fixed):** a rule that joins `cogat_definition('memory', d)` with
    `similar_study(d, s)` and another atom is slow:
    - `close(s) :- cogat_definition('memory', d), similar_study(d, s),
      selected_study(s)` under PROB hits the 30 s limit;
    - `… , study_journal(s, 'Neuron')` takes 81 s, against 4 s with
      `neuron(s) :- study_journal(s, 'Neuron')` as a rule of its own;
    - passing the text as a head argument (`close(q, s)`, then
      `cogat_definition('memory', d), p(d, l, p)`) runs in about 4 s;
    - the in-body constant does not restrict `similar_study`'s text (no sideways
      binding), so the similarity is computed for every definition;
    - DeepSeek writes the slow form and times out (f-102, f-133);
    - the guidance says such a text "is not known and the query fails"; in fact it
      runs out of time.

## Leakage

`scripts/leakage.py --openrouter`, bge-m3, on the branch bank (84 questions):
- the new n-back example's highest cosine to any dataset question is 0.737 (nsv2-18);
- the other converted examples keep their questions;
- per dataset: nsv2 0.840, v3 0.839, fresh 0.867 (f-097, as in nsv3c; it predates
  this change).

## Spend

From the traces, both arms:
- $12.74 in total: Sonnet $9.80, DeepSeek single $0.56, vote + fallback $2.38;
- Sonnet tokens: 4.93M in and 0.09M out, fallbacks included.

The key's remaining credit went from $202.3 to $179.2 over the session. The key is
shared: about $8 of that went to another session before these runs started.

## Reproduce

```bash
source scripts/env.sh
scripts/run_nsv3d_cogat.sh v3; scripts/run_nsv3d_cogat.sh fresh; scripts/run_nsv3d_cogat.sh nsv2
source scripts/nsv3c_env.sh
.venv-dsparity/bin/python scripts/nsv3d_cogat_usage.py datasets/neurosynth-v3-fresh.yaml - \
    master=runs/nsv3d-cogat-master-fresh-deepseek branch=runs/nsv3d-cogat-branch-fresh-deepseek
.venv-dsparity/bin/python scripts/run_cost.py datasets/neurosynth-v3-fresh.yaml - \
    deepseek-vote=runs/nsv3d-cogat-branch-fresh-deepseek-vote
.venv-dsparity/bin/python scripts/cogat_lookup.py recollection "emotion regulation" speech
```
