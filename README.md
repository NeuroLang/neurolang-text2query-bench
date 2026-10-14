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
NeuroLang LLM query assistant (`neurolang.utils.llm`, the `.ask` command
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

```bash
uv venv --python 3.12
uv pip install -e "/path/to/NeuroLang[llm]"
uv pip install -e ".[dev]"
```

Until they are merged, NeuroLang needs two branches:

- `tui-5-llm` (NeuroLang/NeuroLang#904), the LLM assistant;
- `feat/rdf-data-loading`, for the TEXT2SPARQL sets: loading RDF
  instances, IRIs and prefixed names in Datalog, SPARQL-like builtins,
  `min` and `avg`.

Check out a branch that merges both, and install it.

The engine needs the NeuroSynth data: pass `--data-dir` (it is
downloaded on first use). Building the engine takes about 1.5 minutes.

LLM providers are configured as for NeuroLang's assistant, in
`~/.config/neurolang/llm.yaml`, `$NEUROLANG_LLM_CONFIG` or `--llm-config`.
See `neurolang/utils/llm/llm.example.yaml`. The supported providers are:

- OpenRouter
- Albert (`https://albert.api.etalab.gouv.fr/v1`)
- Anthropic
- any OpenAI-compatible server
- a local command such as `claude -p` (provider `claude-code`)

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

Each run directory gets three files:

- `answers.json`: the queries and their costs
- `results.json`: the scores, per question and aggregated overall, per
  language and per tag
- `report.md`: the tables, and the answers that are not exact

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
