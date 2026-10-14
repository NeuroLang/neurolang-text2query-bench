"""
The TEXT2SPARQL challenge's question sets, translated to NeuroLang.

The four sets of the challenge are imported: ``ck25`` and ``ck26``
(questions on eccenca's corporate knowledge graph, in English and
German) and ``db25`` and ``db26`` (questions on DBpedia, in English and
Spanish). Each question keeps its gold SPARQL query and is scored, as in
the challenge, against its official gold result set; its gold Datalog
translation, when there is one, is checked against the same result set
(:func:`check_translations`).

The knowledge graphs are loaded into NeuroLang with its ontology loader
(``load_ontology(..., individuals=True, names="prefixed")``, see the
engines of ``engines/text2sparql.yaml``): the corporate graph whole, and
DBpedia as the subgraph its public endpoint gives for the gold queries
(:mod:`.dbpedia_subgraph`).

Answers are compared as the challenge's client does: the values of all
the columns of all the rows form a set, numbers being written in a
canonical form, and an ASK query's answer is ``true`` or ``false``.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

import httpx
import yaml

from .metrics import Score, _prf

RAW = "https://raw.githubusercontent.com/AKSW"
CLIENT_EXAMPLES = f"{RAW}/text2sparql-client-examples/main"
SITE_2026 = f"{RAW}/text2sparql.aksw.org/2026/docs/results"


@dataclass(frozen=True)
class QuestionSet:
    """A question set of the challenge and where its files are."""

    name: str
    uri: str
    engine: str
    questions_url: str
    gold_url: str
    description: str


SETS = {
    "ck25": QuestionSet(
        "ck25", "https://text2sparql.aksw.org/2025/corporate/",
        "text2sparql-corporate",
        f"{CLIENT_EXAMPLES}/examples_ck25/questions_ck25.yml",
        f"{CLIENT_EXAMPLES}/examples_ck25/ck25_true_result_set.json",
        "TEXT2SPARQL 2025, corporate knowledge graph (English).",
    ),
    "ck26": QuestionSet(
        "ck26", "https://text2sparql.aksw.org/2026/corporate/",
        "text2sparql-corporate",
        f"{SITE_2026}/ck26/questions_ck26.yml",
        f"{SITE_2026}/ck26/ck26_true_result_set.json",
        "TEXT2SPARQL 2026, corporate knowledge graph (English, German).",
    ),
    "db25": QuestionSet(
        "db25", "https://text2sparql.aksw.org/2025/dbpedia/",
        "text2sparql-dbpedia",
        f"{CLIENT_EXAMPLES}/examples_db25/questions_db25.yml",
        f"{CLIENT_EXAMPLES}/examples_db25/db25_true_result_set.json",
        "TEXT2SPARQL 2025, DBpedia (English, Spanish).",
    ),
    "db26": QuestionSet(
        "db26", "https://text2sparql.aksw.org/2026/dbpedia/",
        "text2sparql-dbpedia",
        f"{SITE_2026}/db26/questions_db26.yml",
        f"{SITE_2026}/db26/db26_true_result_set.json",
        "TEXT2SPARQL 2026, DBpedia (English, Spanish).",
    ),
}

DATASETS_DIR = Path("datasets")
RAW_DIR = DATASETS_DIR / "text2sparql"
ENGINES_FILE = Path("engines/text2sparql.yaml")
TRANSLATIONS_DIR = DATASETS_DIR / "translations"


def raw_paths(name: str, raw_dir: Path = RAW_DIR):
    """Return the local paths of the questions and gold files of *name*."""
    return (
        raw_dir / f"questions_{name}.yml",
        raw_dir / f"{name}_true_result_set.json",
    )


def download(name: str, raw_dir: Path = RAW_DIR) -> None:
    """Download the questions and gold result set of the set *name*."""
    question_set = SETS[name]
    raw_dir.mkdir(parents=True, exist_ok=True)
    questions, gold = raw_paths(name, raw_dir)
    for url, path in (
        (question_set.questions_url, questions),
        (question_set.gold_url, gold),
    ):
        if not path.exists():
            response = httpx.get(url, follow_redirects=True, timeout=120)
            response.raise_for_status()
            path.write_bytes(response.content)


def question_key(name: str, question_id, language: str) -> str:
    """Return the key of a question in the gold result sets."""
    return f"{name}:{question_id}-{language}"


def load_translations(name: str, directory: Path = TRANSLATIONS_DIR):
    """Return the Datalog translations of the set *name*, by id."""
    path = directory / f"{name}.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(k): v for k, v in (data.get("translations") or {}).items()}


def import_set(name: str, raw_dir: Path = RAW_DIR) -> dict:
    """
    Return the benchmark dataset of the question set *name*.

    Its questions are those of the challenge, with their gold SPARQL
    query and, when there is one, their Datalog translation; their tags
    are the challenge's features. Its ``gold_results`` is the official
    result set file.
    """
    question_set = SETS[name]
    questions_path, gold_path = raw_paths(name, raw_dir)
    source = yaml.safe_load(questions_path.read_text(encoding="utf-8"))
    translations = load_translations(name)
    questions = []
    for entry in source["questions"]:
        question_id = str(entry["id"])
        gold = {"sparql": entry["query"]["sparql"].strip()}
        translation = translations.get(question_id) or {}
        if translation.get("datalog"):
            gold["datalog"] = translation["datalog"].strip()
        questions.append({
            "id": f"{name}-{question_id}",
            "source_id": question_id,
            "tags": [f.lower() for f in entry.get("features") or []],
            "question": dict(entry["question"]),
            "gold": gold,
        })
    return {
        "dataset": question_set.uri,
        "engine": question_set.engine,
        "engines_file": str(Path("..") / ENGINES_FILE),
        "metric": "text2sparql",
        "gold_results": os.path.relpath(gold_path, DATASETS_DIR),
        "set": name,
        "description": question_set.description,
        "questions": questions,
    }


class _BlockDumper(yaml.SafeDumper):
    """A YAML dumper writing multi-line strings as literal blocks."""


def _represent_str(dumper, value):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_BlockDumper.add_representer(str, _represent_str)


def dump_yaml(data) -> str:
    """Return *data* as YAML, multi-line strings as literal blocks."""
    return yaml.dump(
        data, Dumper=_BlockDumper, allow_unicode=True, sort_keys=False,
        width=100,
    )


def write_dataset(name: str, raw_dir: Path = RAW_DIR) -> Path:
    """Import the set *name* and write it to ``datasets/<name>.yaml``."""
    download(name, raw_dir)
    dataset = import_set(name, raw_dir)
    path = DATASETS_DIR / f"{name}.yaml"
    path.write_text(
        "# Imported from the TEXT2SPARQL challenge by "
        "`t2q-bench import-text2sparql`; edit the Datalog translations in "
        f"datasets/translations/{name}.yaml.\n"
        + dump_yaml(dataset),
        encoding="utf-8",
    )
    return path


def canonical(value) -> str:
    """Return *value* as the challenge compares it, numbers canonical."""
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    try:
        number = float(text)
    except ValueError:
        return text
    if number != number or number in (float("inf"), float("-inf")):
        return text
    number = round(number, 4)
    if number.is_integer():
        return str(int(number))
    return repr(number)


def values(rows) -> set:
    """Return the set of canonical values of all the columns of *rows*."""
    return {canonical(value) for row in rows for value in row}


def gold_values(gold: dict, key: str) -> set:
    """Return the gold values of the question *key* of a result set."""
    answers = gold.get(key, {})
    if set(answers) == {"true"}:
        return {"true" if answers["true"] else "false"}
    return {canonical(value) for value in answers}


def score_values(predicted: set, expected: set) -> Score:
    """Return the precision, recall and F1 of *predicted* values."""
    return _prf(predicted, expected)


def check_translations(nl, dataset, timeout: float = 120.0) -> list:
    """
    Run the Datalog translations and compare them to the official answers.

    Each check is a dict: the question ``id``, its ``status`` (``ok``
    when the values are those of the official result set, ``mismatch``,
    ``error`` or ``missing`` when there is no translation), the ``f1``
    and a ``detail`` of the differences.
    """
    from .engine import execute

    results = load_gold(dataset.gold_results)
    checks = []
    for question in dataset.questions:
        language = next(iter(question.text))
        expected = gold_values(
            results, question_key(dataset.set, question.source_id, language)
        )
        gold = question.gold_query()
        if gold is None:
            checks.append({"id": question.id, "status": "missing", "f1": 0.0})
            continue
        execution = execute(nl, gold[1], gold[0], timeout)
        if not execution.ok:
            checks.append({
                "id": question.id, "status": "error", "f1": 0.0,
                "detail": execution.error[:300],
            })
            continue
        predicted = values(execution.rows)
        scored = score_values(predicted, expected)
        missing = sorted(expected - predicted)[:3]
        extra = sorted(predicted - expected)[:3]
        checks.append({
            "id": question.id,
            "status": "ok" if scored.exact else "mismatch",
            "f1": scored.f1,
            "detail": "" if scored.exact else (
                f"{len(predicted)} values vs {len(expected)} gold; "
                f"missing {missing}; extra {extra}"
            ),
        })
    return checks


def load_gold(path: Path) -> dict:
    """Return the official gold result set at *path*."""
    return json.loads(Path(path).read_text(encoding="utf-8"))
