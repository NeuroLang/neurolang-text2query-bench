# neurolang-text2query-bench

A benchmark of the translation of natural-language questions into
[NeuroLang](https://github.com/NeuroLang/NeuroLang) queries (Datalog or
SQUALL), modelled on the
[TEXT2SPARQL challenge](https://text2sparql.aksw.org/latest/):

- **Questions in several natural languages.** Each question is asked in
  English and French.
- **Gold queries.** Each question has a gold query; its gold answers are
  the rows that query returns on the engine.
- **Scores.** The rows a system's query returns are scored by precision,
  recall and F1 against the gold rows. Columns are aligned, so a system
  may return them in another order or add columns.
- **Systems.** A system is either run in process or reached as an HTTP
  endpoint speaking the TEXT2SPARQL protocol:
  `GET /?question=...&dataset=...` returns `{"dataset", "question", "query"}`.
- **Two separate steps.** `ask` collects the queries; `evaluate` runs and
  scores them.

The systems benchmarked out of the box are the two strategies of the
NeuroLang LLM query assistant (`neurolang_apps.utils.llm`, the `.ask` command
of the interactive `neurolang-query -i`):

- **ICL**: in-context learning. The prompt holds the syntax of the
  language, the engine's predicates (schema linking) and the examples
  closest to the question. The query is then validated on the engine and
  corrected from its error. With `samples > 1`, several candidates are
  generated and the most common result is kept (self-consistency).
- **ReAct**: an agent reasons and calls tools until its query passes
  the checks. The tools list and describe predicates, search the stored
  values (entity resolution), and check and run queries. Tool calls are
  native, or use a Thought/Action/Observation text protocol for models
  without tool calling.

These follow the techniques of
[Google Cloud's text-to-SQL work](https://cloud.google.com/blog/products/databases/techniques-for-improving-text-to-sql)
and of the TEXT2SPARQL participants:

- schema linking
- value sampling
- dialect-specific examples
- validation and reprompting
- self-consistency
- execution-based evaluation

## Dataset

`datasets/neurosynth.yaml` holds 32 questions on NeuroLang's `neurosynth`
engine. The engine covers studies, the terms their abstracts mention
with TF-IDF weights, reported activation peaks, the Schaefer atlas, and
a probabilistic choice over studies. Each question is tagged:

| tag | what it tests |
|---|---|
| simple, constant | one predicate, constants |
| join, multi-hop | joins across predicates |
| negation, disjunction, conjunction | connectives |
| comparison | arithmetic comparisons |
| aggregation | count, max, per group |
| atlas | the Schaefer atlas |
| probabilistic | marginal and conditional probabilities |
| entity-resolution | the question's words differ from the stored constant ("decision-making" → `'decision making'`) |

The gold queries avoid NeuroLang constructs that currently fail. A
system writing them is still scored against the gold rows, so engine
bugs show up as failures of the systems that hit them.

## Setup

NeuroLang is a uv workspace of four packages (`nl_expr`, `nl_core`,
`neurolang`, `neurolang_apps`); the assistant is
`neurolang_apps.utils.llm`. Install a checkout of them, editable, then
the bench:

```bash
uv venv --python 3.12 .venv-llmex
N=/path/to/NeuroLang/packages
uv pip install --python .venv-llmex/bin/python \
    -e $N/nl_expr -e $N/nl_core -e $N/neurolang \
    -e "$N/neurolang_apps[llm,tui,embeddings]" -e ".[dev]"
```

The neurosynth-v2 runs used the branch `feat/llm-text-search-examples`
(free-text search, Cognitive Atlas, atlases). The TEXT2SPARQL sets need
`feat/rdf-data-loading` (NeuroLang/NeuroLang#912) for loading RDF
instances, IRIs and prefixed names in Datalog, SPARQL-like builtins,
`min` and `avg`.

The free-text predicates (`similar_study`) embed the question with
SPECTER2 (extra `embeddings`) against the embeddings of the abstracts
cached in `<data-dir>/neurosynth/embeddings`. With torch 2.2 (the last
for Intel Macs), transformers loads the base model only from
safetensors: put `model.safetensors` of `allenai/specter2_base` in
`embeddings/models/allenai--specter2_base/`.

`scripts/env.sh` exports `ALBERT_API_KEY` and `OPENROUTER_API_KEY` from
`~/.zshrc` for non-interactive shells.

The engine needs the NeuroSynth data: pass `--data-dir` (it is
downloaded on first use). Building the engine takes about 1.5 minutes.

LLM providers are configured as for NeuroLang's assistant, in
`~/.config/neurolang/llm.yaml`, `$NEUROLANG_LLM_CONFIG` or `--llm-config`.
See `neurolang_apps/utils/llm/llm.example.yaml`. The supported providers are:

- OpenRouter
- Albert (`https://albert.api.etalab.gouv.fr/v1`)
- Anthropic
- any OpenAI-compatible server
- a local command such as `claude -p` (provider `claude-code`)

`configs/llm.yaml` uses Gemma 4 31B on Albert (`albert-gemma`) by
default. It reads the key from `ALBERT_API_KEY` and keeps to Albert's
limit of 25 requests a minute.

## Usage

```bash
# run the gold queries once and cache their rows (datasets/*.gold.json)
t2q-bench --data-dir ~/neurolang_data check-gold

# ask and evaluate a system in process
t2q-bench --data-dir ~/neurolang_data run --strategy react \
    --provider claude-code --lang en fr -o runs/react-claude

# or serve the assistant as a TEXT2SPARQL endpoint…
t2q-bench --data-dir ~/neurolang_data serve --strategy icl --provider albert
# …and benchmark any endpoint
t2q-bench --data-dir ~/neurolang_data run \
    --endpoint http://127.0.0.1:8000/ --name icl-albert -o runs/icl-albert

# compare runs
t2q-bench report runs/*/results.json
```

`--split dev` (or `test`) asks only the questions of a split, for the
datasets that have one (neurosynth-v2).

Each run directory gets three files:

- `answers.json`: the queries and their costs
- `results.json`: the scores, per question and aggregated overall, per
  language and per tag
- `report.md`: the tables, and the answers that are not exact

### Monitoring the requests to the LLM

`debug` asks a few questions and prints each request to the LLM and its
reply as they go, then scores the answers:

```bash
t2q-bench --data-dir ~/neurolang_data --dataset datasets/ck26.yaml debug \
    --provider openrouter-gemma --ids ck26-4 --lang en
```

Each request shows only the messages added since the previous one: the
system prompt and question first, then the model's previous reply and
the observation of its action. Messages are cut to a few thousand
characters (the system prompt to 800); `--full` prints them whole.

`run` and `ask` record the same events, one file per question:
`trace/<id>-<lang>.jsonl` in the run directory, or `<answers>.trace/`
beside the answers file of `ask -o <answers>` (`--no-trace` turns this
off). Follow the question a run is asking from another terminal with:

```bash
t2q-bench watch runs/react-gemma            # follows the run question by question
t2q-bench watch runs/answers.json           # the answers file of an ask run
t2q-bench watch runs/react-gemma/trace/ck26-4-en.jsonl --no-follow
```

### Tuning ReAct for Gemma 4 31B (2026-10-15)

The ReAct agent was tuned on a dev split and evaluated once on held-out
questions, measured by the overlap of the query results with the
official answers (F1). Both splits are ReAct with Gemma 4 31B on
OpenRouter.

- **Dev split:** db25 and the odd ck26 questions, English only.
- **Test split:** db26 in English and Spanish, with db25 as few-shot
  examples, and the even ck26 questions in English and German.

| system | ck26 en | ck26 de | db26 en | db26 es | all |
|---|---:|---:|---:|---:|---:|
| Gemma 4 31B, baseline agent | 0.404 | 0.229 | 0.353 | 0.400 | 0.357 |
| Gemma 4 31B, tuned agent | 0.628 | 0.606 | 0.645 | 0.584 | **0.615** |
| DeepSeek V4.1 Flash, tuned agent | 0.683 | 0.567 | 0.615 | 0.591 | 0.610 |
| Datalog ceiling (checked translations) | 0.980 | 0.980 | 1.000 | 1.000 | |

The ceiling is the score of the checked Datalog translations of the gold
queries. It shows that nearly all of the remaining gap comes from the
agent, not from translating SPARQL to Datalog.

The changes, each found in Gemma's dev trajectories:

1. `search_values(pattern)` searches every stored relation, takes a
   column by name or number, and shows the matching facts with their
   IRIs. It also matches IRIs, with spaces as underscores, and shows at
   most 3 facts per predicate.
2. The text protocol accepts the usual formatting slips.
3. When the agent runs out of steps, its answer is the most detailed
   query that gave rows.
4. `final_answer` runs the query first. A runtime error rejects it. An
   answer with no rows must be confirmed, and the agent is reminded of
   its query that gave rows.
5. `check_query` rejects an aggregation over a conjunction, and grouping
   by the aggregated variable.
6. The reference covers yes/no questions, answer classes, max/min, and
   top k.
7. Queries run in a child process, stopped after 30 s or above 4 GB.

On the dev split, Gemma's F1 rose:

| dev half | baseline | v1 | v2 | v3 |
|---|---:|---:|---:|---:|
| ck26 | 0.384 | 0.553 | 0.685 | 0.613 |
| db25 | 0.379 | 0.469 | 0.604 | 0.667 |

v4, the version tested, is v3 with the max-first guidance for "the
most …" questions.

On the test split, the tuned agent had 76 exact answers out of 150,
against 44 for the baseline. It had 17 empty answers instead of 42, and
9 errors instead of 21.

## neurosynth-v2 baseline (2026-10-28)

`datasets/neurosynth-v2.yaml` holds 41 held-out questions, in English
and French, on the current neurosynth engine. It covers:

- free-text search of the studies (`similar_study`);
- Cognitive Atlas concepts and their hierarchy;
- the Schaefer networks, and the Destrieux and Tian atlases;
- MNI points and co-activation;
- negation and aggregation;
- marginal and conditional probabilities over `selected_study`.

Each question has a `split`, dev (20) or test (21), balanced across the
tags (`scripts/assign_splits.py`). None is in the assistant's example
bank. The highest bge-m3 cosine of a question to a bank question is
0.811 (`scripts/leakage.py`). All 41 gold queries run and return rows.

These are ReAct runs writing Datalog, with NeuroLang's
`feat/llm-text-search-examples`, at most 8 steps and 6 BM25 examples:

| model (provider) | dev F1 | test F1 | test exact | steps | tokens/q | s/q |
|---|---:|---:|---:|---:|---:|---:|
| Sonnet 5.5 (OpenRouter) | **0.975** | **0.952** | 95% | 3.7 | 204k | 17 |
| Gemma 4 31B (OpenRouter) | 0.675 | 0.666 | 64% | 3.6 | 171k | 40 |
| Gemma 4 31B (Albert), 21 English test questions | | 0.524 | 52% | 2.8 | 88k | 84 |
| DeepSeek V4 Flash 0731 (OpenRouter) | 0.775 | 0.714 | 71% | 4.8 | 203k | 49 |
| DeepSeek V4 Flash 0731 (Albert) | | 0.738 | 74% | 4.6 | 175k | 104 |

- **Gemma on Albert** stopped at its daily cap of 2.46M input tokens
  after 16 questions; 7 answers were lost to HTTP 429 and timeouts. On
  the 14 questions it answered, its F1 (0.786) is that of the same model
  on OpenRouter (0.785).
- **DeepSeek runs out of steps.** That is its main failure: 9 to 10 of
  40 answers. It searches for Tian labels with anatomical words
  ("accumbens"), but the labels are abbreviations (`NAc core rh`).
- **Gemma copies the sort notation** of `describe_predicate`, e.g.
  `study_title(study(10022492), t)`, and puts stored relations in PROB
  without `selected_study`.
- **Every request is about 61k tokens.** The schema lists 1264
  Cognitive Atlas classes as predicates.
- **Engine bugs.** The max of a probability, joined back to it, returns
  no rows, although `prompts.py` teaches that pattern. `similar_study`
  with a constant text fails outside the query rule.
- **Regression set.** On the 32 old questions, Sonnet now scores F1
  0.757 (0.918 on 2026-10-14). The drop comes from the engine's new
  guidance, which answers with probabilities where the old golds list
  studies or counts.

Per tag, the failure kinds and examples are in
[runs/neurosynth-v2-baseline.md](runs/neurosynth-v2-baseline.md). The
scripts:

- `scripts/run_nsv2.sh PROVIDER OUT [--split dev|test]` runs a provider;
- `scripts/failure_taxonomy.py` gives the scores and failure kinds per
  split;
- `scripts/reevaluate.py` scores runs again after a gold change.

## neurosynth-v2, lean schema (2026-10-28)

NeuroLang branch `feat/llm-lean-schema` (local, on
`feat/llm-text-search-examples`) fixes the three prompt and tool
problems of the baseline:

- the schema counts the 1264 Cognitive Atlas classes named by IRI in
  one line: the system prompt goes from 109k to 18k characters;
- predicates are shown with plain columns (`study_title(study_id,
  text)`), and regions by their type, not their voxels;
- `search_values` on a predicate without a match lists all the values
  of a column of at most 200 (the 32 Tian labels), and the guidance
  spells out the Tian abbreviations and PROB over `selected_study`.

Dev split, ReAct, baseline → lean:

| model (OpenRouter) | F1 | exact | steps | tokens/q | s/q |
|---|---:|---:|---:|---:|---:|
| Sonnet 5.5 | 0.975 → **1.000** | 98% → 100% | 3.8 → 3.6 | 202k → 27k | 17 → 20 |
| Gemma 4 31B | 0.675 → 0.775 | 68% → 78% | 3.3 → 2.4 | 157k → 16k | 38 → 29 |
| DeepSeek V4 Flash 0731 | 0.775 → 0.801 | 78% → 80% | 5.0 → 5.3 | 210k → 37k | 58 → 45 |

Most of what still fails comes from the two engine bugs (argmax of a
probability, `similar_study` outside the query rule). Gemma on Albert
could not be run: the daily cap was already used up. At 16k tokens a
question it now allows about 150 questions a day. Details, per tag and
failure kind, in [runs/nsv2-dev-lean.md](runs/nsv2-dev-lean.md).
`VENV=.venv-llmfix scripts/run_nsv2.sh ...` runs against the branch,
and `scripts/prompt_size.py` measures the prompt.

## TEXT2SPARQL question sets in Datalog

The four question sets of the TEXT2SPARQL challenge are also in the
benchmark:

| set | questions | languages | knowledge graph |
|---|---:|---|---|
| ck25 | 50 | en | eccenca's corporate graph (27k triples) |
| ck26 | 50 | en, de | the same, with paraphrased questions |
| db25 | 100 | en, es | DBpedia 2015-10 |
| db26 | 50 | en, es | DBpedia 2015-10 |

**Loading the graphs.** Both graphs are loaded with NeuroLang's own
ontology loader, through the engines in `engines/text2sparql.yaml`
(`load_ontology(..., individuals=True, names="prefixed")`). Every triple
`s p o` becomes the fact `p(s, o)`, and `s rdf:type C` also becomes
`C(s)`. Predicates are named by prefix (`pv:name`), and IRIs are written
`<http://...>`, so a SPARQL query reads naturally in Datalog:

```
ans(r) :- pv:areaOfExpertise(r, <http://ld.company.org/prod-instances/prod-cat-Sensor>)
```

The corporate graph is loaded whole. DBpedia (about 200 million triples)
is loaded as the subgraph that `t2q-bench build-dbpedia-subgraph` fetches
from the challenge's endpoint. That subgraph holds:

- the triples matching each gold query, from a `CONSTRUCT` over its
  `WHERE` clause;
- the outgoing triples of the entities the queries name;
- the labels and types of those entities, of their neighbours and of
  the gold answers.

The gold queries therefore give their full answers on it, while other
queries may see only part of DBpedia.

**Translations.** `datasets/translations/<set>.yaml` translates each
gold SPARQL query to Datalog. `check-gold` checks every translation
against the official answers. Datalog has no ORDER BY, LIMIT or OPTIONAL:

- `ORDER BY … LIMIT 1` becomes an aggregate (argmin/argmax);
- a `LIMIT k` becomes a rank threshold;
- an `OPTIONAL` is flattened, which the official metric allows.

A `note` explains each translation that cannot match exactly, usually
a tie that the endpoint broke arbitrarily. The translations reproduce
the official answers on 45 of ck25's 50 questions (two of its official
answers are wrongly empty), 47 of ck26's 50, all 100 of db25's and all
50 of db26's.

**Scoring.** These sets are scored as in the challenge: the set of the
values of all the answers, numbers in a canonical form, against the
official result set.

```bash
t2q-bench import-text2sparql                 # download, write datasets/{ck,db}2{5,6}.yaml
t2q-bench build-dbpedia-subgraph             # data/dbpedia-subgraph.ttl (about 1M triples)
t2q-bench --data-dir ~/neurolang_data --dataset datasets/ck26.yaml check-gold
t2q-bench --data-dir ~/neurolang_data --dataset datasets/ck26.yaml run \
    --strategy react --provider claude-code --lang en de
```

`--examples-from DATASET` puts the gold queries of another dataset into
the prompt as few-shot examples, e.g. db25's for db26. `self` uses the
dataset's own other questions (leave-one-out).

The question sets and gold result sets are not redistributed here;
`import-text2sparql` downloads them:

- [AKSW/text2sparql.aksw.org](https://github.com/AKSW/text2sparql.aksw.org): 2026 sets and the corporate graph, CC-BY-SA-4.0;
- [AKSW/text2sparql-client-examples](https://github.com/AKSW/text2sparql-client-examples): 2025 sets, Apache-2.0;
- [eccenca/ck25-dataset](https://github.com/eccenca/ck25-dataset): ck25, CC-BY-4.0.

DBpedia is CC-BY-SA-3.0. The Datalog translations are derived from the
gold queries of these sets and are distributed under the same terms.

## Results

These are first results of NeuroLang's LLM assistant with Claude Sonnet,
through the `claude-code` provider, writing Datalog. The run date is
2026-10-14 and the scores are the mean over all the questions and
languages of each set.

| dataset | strategy | F1 | exact | valid | LLM calls | s/question |
|---|---|---:|---:|---:|---:|---:|
| neurosynth (en, fr) | ICL | 0.875 | 86% | 100% | 1.2 | 10 |
| neurosynth (en, fr) | ReAct | **0.918** | 89% | 95% | 4.1 | 25 |
| ck26 (en, de), zero-shot | ICL | 0.496 | 37% | 98% | 1.0 | 10 |
| ck26 (en, de), zero-shot | ReAct | **0.677** | 54% | 69% | 6.7 | 37 |
| db26 (en, es), db25 as examples | ICL | 0.394 | 39% | 99% | 1.2 | 13 |
| db26 (en, es), db25 as examples | ReAct | **0.590** | 55% | 61% | 5.2 | 44 |

- **ReAct beats ICL by 0.04 to 0.20 F1.** Its tools resolve entities to
  stored constants, and it can check its queries' results before
  answering.
- **Some answers are missing.** The `claude -p` usage limit cut off 2 of
  ck26's ReAct answers and 15 of db26's, and those count as 0. Resume
  them with `run --resume`.
- **On the TEXT2SPARQL sets, most errors are about what to return.**
  Examples are returning entity names instead of IRIs, or adding
  columns. The official metric scores these as wrong answers.

## Metrics

For each question and natural language:

- **precision / recall / F1**: computed on the sets of rows. Values are
  normalised, with floats rounded to 4 decimals. The system's columns
  are projected and permuted onto the gold columns, and the best
  alignment is kept.
- **exact**: F1 = 1.
- **valid**: the system's own check accepted its query.
- **runs**: the query ran on the engine without error, within the time
  limit (`--timeout`).
- **calls, tokens, s/question**: the cost of the generation.

Two parts of TEXT2SPARQL are not reproduced:

- **nDCG** is not computed, because NeuroLang queries return sets, not
  ranked lists.
- **The complexity analysis** is replaced by the tags.

## Tests

```bash
pytest
```

The tests use a small in-memory engine and a scripted model. They need
neither the data nor an LLM.
