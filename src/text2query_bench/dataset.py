"""
Benchmark datasets: questions on a NeuroLang engine with gold queries.

A dataset is a YAML file::

    dataset: https://neurolang.github.io/text2query/2026/neurosynth/
    engine: neurosynth
    description: ...
    questions:
      - id: ns-001
        tags: [simple, constant]
        question:
          en: Which studies mention pain?
          fr: Quelles études mentionnent la douleur ?
        gold:
          datalog: ans(s) :- mentions(s, 'pain')

As in the TEXT2SPARQL challenge, the gold answers are the rows the gold
query returns on the engine, and a question can be asked in several
natural languages. The gold query is written in Datalog (and may also
be given in SQUALL); the answers of a system are compared with the gold
rows, whatever the query language of the system.

A dataset imported from TEXT2SPARQL (see :mod:`.text2sparql`) has the
``metric`` ``text2sparql``: its questions are scored against the
official result set of ``gold_results``, and their gold is a SPARQL
query with, when there is one, its Datalog translation. Its engine is
declared in ``engines_file``, relative to the dataset.
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

QUERY_LANGUAGES = ("datalog", "squall")
GOLD_LANGUAGES = QUERY_LANGUAGES + ("sparql",)
METRICS = ("rows", "text2sparql")


class DatasetError(ValueError):
    """Raised when a dataset file is invalid."""


@dataclass
class Question:
    """A question, in several languages, with its gold queries and tags."""

    id: str
    text: dict
    gold: dict
    tags: list = field(default_factory=list)
    source_id: str = ""

    def gold_query(self):
        """
        Return ``(language, query)`` of the NeuroLang gold, Datalog first.

        It is None for a question whose gold is only a SPARQL query.
        """
        for language in QUERY_LANGUAGES:
            if self.gold.get(language):
                return language, self.gold[language]
        return None


@dataclass
class Dataset:
    """The questions of a benchmark on an engine."""

    uri: str
    engine: str
    questions: list
    description: str = ""
    path: Path = None
    metric: str = "rows"
    engines_file: Path = None
    gold_results: Path = None
    set: str = ""

    @property
    def languages(self) -> list:
        """Return the natural languages of the questions."""
        languages = []
        for question in self.questions:
            languages += [lang for lang in question.text if lang not in languages]
        return languages

    def question(self, question_id: str) -> Question:
        """Return the question *question_id*."""
        for question in self.questions:
            if question.id == question_id:
                return question
        raise KeyError(question_id)

    def select(self, ids=None, tags=None) -> list:
        """Return the questions with one of the *ids* or of the *tags*."""
        selected = self.questions
        if ids:
            selected = [q for q in selected if q.id in ids]
        if tags:
            selected = [q for q in selected if set(tags) & set(q.tags)]
        return selected


def _question(entry: dict, index: int) -> Question:
    """Return the question described by the YAML mapping *entry*."""
    if not isinstance(entry, dict) or "id" not in entry:
        raise DatasetError(f"Question {index} has no id.")
    text = entry.get("question")
    if isinstance(text, str):
        text = {"en": text}
    if not text:
        raise DatasetError(f"Question {entry['id']} has no text.")
    gold = {
        language: query.strip()
        for language, query in (entry.get("gold") or {}).items()
    }
    unknown = set(gold) - set(GOLD_LANGUAGES)
    if unknown or not gold:
        raise DatasetError(
            f"Question {entry['id']} needs a gold query in "
            f"{', '.join(GOLD_LANGUAGES)}."
        )
    return Question(
        str(entry["id"]), dict(text), gold, list(entry.get("tags") or []),
        str(entry.get("source_id", "")),
    )


def load_dataset(path) -> Dataset:
    """Read the dataset of the YAML file at *path*."""
    path = Path(path)
    with open(path, encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}
    questions = [
        _question(entry, i) for i, entry in enumerate(data.get("questions", []))
    ]
    ids = [q.id for q in questions]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise DatasetError(f"Duplicate question ids: {', '.join(duplicates)}")
    if not data.get("engine"):
        raise DatasetError("The dataset names no engine.")
    metric = data.get("metric", "rows")
    if metric not in METRICS:
        raise DatasetError(f"Unknown metric {metric!r}.")
    if metric == "rows":
        missing = [q.id for q in questions if q.gold_query() is None]
        if missing:
            raise DatasetError(
                f"Questions without a Datalog or SQUALL gold query: "
                f"{', '.join(missing)}."
            )
    elif not data.get("gold_results"):
        raise DatasetError("A text2sparql dataset needs gold_results.")
    relative = (
        lambda key: path.parent / data[key] if data.get(key) else None
    )
    return Dataset(
        data.get("dataset", path.stem), data["engine"], questions,
        data.get("description", ""), path, metric,
        relative("engines_file"), relative("gold_results"),
        data.get("set", ""),
    )
