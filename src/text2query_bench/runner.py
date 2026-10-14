"""
Running a system on a dataset and scoring its answers.

The two steps of the TEXT2SPARQL client are kept apart: :func:`ask`
collects the queries of a system (``answers.json``), :func:`evaluate`
runs them and the gold queries on the engine and scores them
(``results.json``); :func:`summary` aggregates the scores, overall, per
tag and per natural language.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Optional

from . import text2sparql
from .dataset import Dataset
from .engine import execute
from .metrics import mean, score


def ask(
    system, dataset: Dataset, languages, questions=None,
    progress: Optional[Callable] = None,
) -> list:
    """
    Return the answers of *system* to the questions of *dataset*.

    Each answer is a dict: the question id, natural language, text and
    the :class:`~.systems.Generation` of the system. Questions without a
    text in a language are skipped for it.
    """
    answers = []
    for question in questions or dataset.questions:
        for language in languages:
            text = question.text.get(language)
            if not text:
                continue
            generation = system.generate(text, language).as_dict()
            answer = {
                "id": question.id, "language": language, "question": text,
                "system": system.name,
                "query_language": generation.pop("language"),
                **generation,
            }
            answers.append(answer)
            if progress:
                progress(answer)
    return answers


def gold_answers(nl, dataset: Dataset, timeout: float = 300.0) -> dict:
    """
    Return the gold answers of the questions, by id.

    They are the rows of the gold queries on the engine or, for a
    TEXT2SPARQL dataset, the official values, by natural language.
    """
    if dataset.metric == "text2sparql":
        return official_gold(dataset)
    gold = {}
    for question in dataset.questions:
        language, query = question.gold_query()
        execution = execute(nl, query, language, timeout)
        gold[question.id] = {
            "query": query, "language": language,
            "rows": execution.rows, "columns": execution.columns,
            "error": execution.error, "seconds": execution.seconds,
        }
    return gold


def official_gold(dataset: Dataset) -> dict:
    """Return the official values of a TEXT2SPARQL dataset, by id."""
    results = text2sparql.load_gold(dataset.gold_results)
    gold = {}
    for question in dataset.questions:
        gold[question.id] = {"values": {
            language: sorted(text2sparql.gold_values(
                results,
                text2sparql.question_key(
                    dataset.set, question.source_id, language
                ),
            ))
            for language in question.text
        }}
    return gold


def _score(dataset, expected: dict, language: str, rows):
    """Return the score of *rows* and the size of the gold answer."""
    if dataset.metric == "text2sparql":
        gold_values = set(expected["values"].get(language, ()))
        scored = text2sparql.score_values(
            text2sparql.values(rows), gold_values
        )
        return scored, len(gold_values)
    return score(rows, expected["rows"]), len(expected["rows"])


@dataclass
class Result:
    """The score of an answer, with its execution."""

    id: str
    language: str
    system: str
    query: str
    query_language: str
    valid: bool
    executed: bool
    precision: float
    recall: float
    f1: float
    rows: int
    gold_rows: int
    error: str
    generation_seconds: float
    execution_seconds: float
    calls: int
    tokens: int


def evaluate(
    nl, dataset: Dataset, answers: list, gold: dict,
    timeout: float = 120.0, progress: Optional[Callable] = None,
) -> list:
    """Run the *answers* on the engine and score them against *gold*."""
    results = []
    for answer in answers:
        expected = gold[answer["id"]]
        executed, rows, error, seconds = False, [], answer.get("error", ""), 0.0
        if answer.get("query"):
            execution = execute(
                nl, answer["query"], answer["query_language"], timeout
            )
            executed, rows = execution.ok, execution.rows
            seconds = execution.seconds
            error = execution.error
        scored, gold_size = _score(dataset, expected, answer["language"], rows)
        if not executed:
            scored = None
        result = Result(
            answer["id"], answer["language"], answer.get("system", ""),
            answer.get("query", ""), answer["query_language"],
            bool(answer.get("valid")), executed,
            scored.precision if scored else 0.0,
            scored.recall if scored else 0.0,
            scored.f1 if scored else 0.0,
            len(rows), gold_size, error,
            answer.get("seconds", 0.0), seconds,
            answer.get("calls", 0), answer.get("tokens", 0),
        )
        results.append(result)
        if progress:
            progress(result)
    return results


def _group(results, key) -> dict:
    """Return the *results* grouped by *key*."""
    groups = {}
    for result in results:
        for value in key(result):
            groups.setdefault(value, []).append(result)
    return groups


def _aggregate(results) -> dict:
    """Return the mean scores and costs of *results*."""
    return {
        "questions": len(results),
        "precision": mean(r.precision for r in results),
        "recall": mean(r.recall for r in results),
        "f1": mean(r.f1 for r in results),
        "exact": mean(r.f1 == 1.0 for r in results),
        "valid": mean(r.valid for r in results),
        "executed": mean(r.executed for r in results),
        "seconds": mean(r.generation_seconds for r in results),
        "calls": mean(r.calls for r in results),
        "tokens": mean(r.tokens for r in results),
    }


def summary(dataset: Dataset, results: list) -> dict:
    """Return the scores overall, per tag and per natural language."""
    tags = {q.id: q.tags for q in dataset.questions}
    return {
        "overall": _aggregate(results),
        "languages": {
            language: _aggregate(group) for language, group in sorted(
                _group(results, lambda r: [r.language]).items()
            )
        },
        "tags": {
            tag: _aggregate(group) for tag, group in sorted(
                _group(results, lambda r: tags.get(r.id, [])).items()
            )
        },
    }


def write_json(path, data) -> None:
    """Write *data* as JSON at *path*, creating its directory."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def results_as_dicts(results) -> list:
    return [asdict(r) for r in results]
