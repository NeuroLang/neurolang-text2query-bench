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
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

QUERY_LANGUAGES = ("datalog", "squall")


class DatasetError(ValueError):
    """Raised when a dataset file is invalid."""


@dataclass
class Question:
    """A question, in several languages, with its gold queries and tags."""

    id: str
    text: dict
    gold: dict
    tags: list = field(default_factory=list)

    def gold_query(self):
        """Return ``(language, query)`` of the gold query, Datalog first."""
        for language in QUERY_LANGUAGES:
            if self.gold.get(language):
                return language, self.gold[language]
        raise DatasetError(f"Question {self.id} has no gold query.")


@dataclass
class Dataset:
    """The questions of a benchmark on an engine."""

    uri: str
    engine: str
    questions: list
    description: str = ""
    path: Path = None

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
    unknown = set(gold) - set(QUERY_LANGUAGES)
    if unknown or not gold:
        raise DatasetError(
            f"Question {entry['id']} needs a gold query in "
            f"{' or '.join(QUERY_LANGUAGES)}."
        )
    return Question(
        str(entry["id"]), dict(text), gold, list(entry.get("tags") or [])
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
    return Dataset(
        data.get("dataset", path.stem), data["engine"], questions,
        data.get("description", ""), path,
    )
