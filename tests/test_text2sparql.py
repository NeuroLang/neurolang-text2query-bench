import json

import pytest
import yaml

from text2query_bench import text2sparql
from text2query_bench.dataset import load_dataset
from text2query_bench.dbpedia_subgraph import (
    _body,
    construct_query,
    labels_query,
    mentioned_entities,
)
from text2query_bench.runner import evaluate, gold_answers, summary

QUESTIONS = """
dataset:
  id: https://text2sparql.aksw.org/2026/corporate/
  prefix: ck26
questions:
- id: 1
  question: {en: "Who manages Ann?", de: "Wer leitet Ann?"}
  features: [SELECT]
  query:
    sparql: "SELECT ?m WHERE { <http://x.org/ann> <http://x.org/manager> ?m }"
- id: 2
  question: {en: "Is Ann a manager?"}
  features: [ASK]
  query:
    sparql: "ASK { <http://x.org/ann> a <http://x.org/Manager> }"
"""

GOLD = {
    "ck26:1-en": {"http://x.org/bob": 1, "3.0": 1},
    "ck26:1-de": {"http://x.org/bob": 1, "3.0": 1},
    "ck26:2-en": {"true": 0},
}


@pytest.mark.parametrize("value, expected", [
    (3, "3"), (3.0, "3"), ("3.0", "3"), ("-0.20", "-0.2"), (0.123456, "0.1235"),
    (True, "true"), ("http://x.org/a", "http://x.org/a"), ("nan", "nan"),
    (-0.9999999999, "-1"), (-0.0, "0"),
])
def test_canonical(value, expected):
    assert text2sparql.canonical(value) == expected


def test_values_flatten_rows_and_columns():
    assert text2sparql.values([("a", 1), ("b", 1.0)]) == {"a", "b", "1"}


def test_gold_values():
    assert text2sparql.gold_values(GOLD, "ck26:1-en") == {
        "http://x.org/bob", "3"
    }
    assert text2sparql.gold_values(GOLD, "ck26:2-en") == {"false"}
    assert text2sparql.gold_values({"q": {"true": 1}}, "q") == {"true"}


@pytest.fixture
def imported(tmp_path, monkeypatch):
    """A ck26-like set imported in a temporary benchmark directory."""
    monkeypatch.chdir(tmp_path)
    raw = tmp_path / "datasets" / "text2sparql"
    raw.mkdir(parents=True)
    questions, gold = text2sparql.raw_paths("ck26", raw)
    questions.write_text(QUESTIONS)
    gold.write_text(json.dumps(GOLD))
    translations = tmp_path / "datasets" / "translations"
    translations.mkdir()
    (translations / "ck26.yaml").write_text(
        "translations:\n"
        "  1:\n"
        "    datalog: ans(m) :- manager(<http://x.org/ann>, m)\n"
    )
    text2sparql.download = lambda name, raw_dir=raw: None
    return text2sparql.write_dataset("ck26", raw)


def test_import_set(imported):
    data = yaml.safe_load(imported.read_text())
    assert data["metric"] == "text2sparql" and data["set"] == "ck26"
    first, second = data["questions"]
    assert first["id"] == "ck26-1" and first["source_id"] == "1"
    assert first["question"] == {"en": "Who manages Ann?", "de": "Wer leitet Ann?"}
    assert first["gold"]["datalog"].startswith("ans(m)")
    assert "datalog" not in second["gold"] and second["tags"] == ["ask"]
    dataset = load_dataset(imported)
    assert dataset.question("ck26-2").gold_query() is None


def test_official_scoring(imported):
    from neurolang.frontend import NeurolangPDL

    dataset = load_dataset(imported)
    gold = gold_answers(None, dataset)
    assert gold["ck26-1"]["values"]["de"] == ["3", "http://x.org/bob"]
    nl = NeurolangPDL()
    nl.add_tuple_set([("http://x.org/ann", "http://x.org/bob", 3.0)],
                     name="manager")
    answers = [
        {"id": "ck26-1", "language": "en", "system": "s",
         "query": "ans(m, k) :- manager(<http://x.org/ann>, m, k)",
         "query_language": "datalog", "valid": True},
        {"id": "ck26-2", "language": "en", "system": "s",
         "query": "ans() :- manager(<http://x.org/ann>, m, k), (k > 5)",
         "query_language": "datalog", "valid": True},
    ]
    results = evaluate(nl, dataset, answers, gold)
    assert [r.f1 for r in results] == [1.0, 1.0]
    assert summary(dataset, results)["overall"]["exact"] == 1.0


SELECT = """PREFIX dbo: <http://dbpedia.org/ontology/>
SELECT DISTINCT (COUNT(?a) AS ?n) WHERE {
  ?x dbo:genre <http://dbpedia.org/resource/Rock_music> .
  { ?x dbo:author ?a } UNION { ?x dbo:writer ?a }
  FILTER (?a != "}")
} ORDER BY ?n"""


def test_body_skips_braces_in_iris_and_strings():
    prologue, body = _body(SELECT)
    assert prologue.startswith("PREFIX dbo:")
    assert 'FILTER (?a != "}")' in body and "ORDER BY" not in body
    _, body = _body("SELECT ?x { ?x ?p <http://a.org/b{c}> }")
    assert body == " ?x ?p <http://a.org/b{c}> "


def test_construct_query():
    query = construct_query(SELECT)
    assert query.startswith("PREFIX dbo:")
    assert "?x <http://dbpedia.org/ontology/author> ?a ." in query
    assert "?x <http://dbpedia.org/ontology/writer> ?a ." in query
    assert "CONSTRUCT {" in query and "WHERE {" in query
    assert "COUNT" not in query


def test_mentioned_entities_and_labels():
    assert mentioned_entities(SELECT) == {
        "http://dbpedia.org/resource/Rock_music"
    }
    query = labels_query(["http://dbpedia.org/resource/A"])
    assert "VALUES ?e { <http://dbpedia.org/resource/A> }" in query


def test_construct_projects_all_variables_of_subselects():
    query = construct_query(
        "PREFIX dbo: <http://dbpedia.org/ontology/>\n"
        "SELECT ?a WHERE { { SELECT ?a ((?y + 1) AS ?z) WHERE {"
        " ?f dbo:starring ?a ; dbo:releaseDate ?y } } } "
        "GROUP BY ?a LIMIT 1"
    )
    assert "SELECT * WHERE" in query and "AS ?z" not in query
    grouped = construct_query(
        "SELECT ?a WHERE { { SELECT ?a (COUNT(?f) AS ?n) WHERE {"
        " ?f <http://x.org/p> ?a } GROUP BY ?a } }"
    )
    assert "COUNT(?f)" in grouped
