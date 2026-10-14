import json
import threading

import httpx
import pytest

from text2query_bench.dataset import DatasetError, load_dataset
from text2query_bench.engine import execute, run_with_timeout, QueryTimeout
from text2query_bench.metrics import score
from text2query_bench.report import comparison_report, run_report
from text2query_bench.runner import ask, evaluate, gold_answers, summary
from text2query_bench.server import make_server
from text2query_bench.systems import EndpointSystem, Generation, System

DATASET = """
dataset: https://example.org/small/
engine: small
questions:
  - id: q1
    tags: [simple]
    question: {en: "Which studies mention pain?", fr: "Quelles études ?"}
    gold: {datalog: "ans(s) :- mentions(s, 'pain')"}
  - id: q2
    tags: [join]
    question: {en: "Which terms do pain studies mention?"}
    gold: {datalog: "ans(t) :- mentions(s, 'pain'), mentions2(s, t)"}
"""


@pytest.fixture
def dataset(tmp_path):
    path = tmp_path / "small.yaml"
    path.write_text(DATASET)
    return load_dataset(path)


@pytest.fixture
def nl():
    from neurolang.frontend import NeurolangPDL

    engine = NeurolangPDL()
    engine.add_tuple_set([(1, "pain"), (2, "pain"), (3, "fear")],
                         name="mentions")
    engine.add_tuple_set([(1, "pain"), (1, "fear"), (2, "pain")],
                         name="mentions2")
    return engine


class Scripted(System):
    name = "scripted"

    def __init__(self, queries):
        self.queries = queries

    def generate(self, question, language):
        query = self.queries.get(question, "")
        return Generation(query, "datalog", bool(query), calls=1, tokens=7)


def test_score_aligns_columns():
    gold = [(1,), (2,)]
    assert score([(1,), (2,)], gold).exact
    assert score([("x", 1), ("y", 2)], gold).exact
    partial = score([(1,), (3,)], gold)
    assert (partial.precision, partial.recall, partial.f1) == (0.5, 0.5, 0.5)
    assert score([(2, "b"), (1, "a")], [("a", 1), ("b", 2)]).exact
    assert score([], []).exact
    assert score([(1,)], []).f1 == 0
    assert score([(1,)], [(1, 2)]).f1 == 0


def test_score_normalises_values():
    import numpy as np

    assert score([(np.int64(1), 0.123401)], [(1, 0.12340004)]).exact
    assert score([(1.0,)], [(1,)]).exact


def test_dataset(dataset):
    assert dataset.engine == "small"
    assert dataset.languages == ["en", "fr"]
    assert dataset.question("q1").gold_query()[0] == "datalog"
    assert [q.id for q in dataset.select(tags=["join"])] == ["q2"]
    assert [q.id for q in dataset.select(ids=["q1"])] == ["q1"]


@pytest.mark.parametrize("text, message", [
    ("engine: x\nquestions: [{id: a, question: q}]", "gold query"),
    ("questions: [{id: a, question: q, gold: {datalog: x}}]", "no engine"),
    ("engine: x\nquestions: [{id: a, question: q, gold: {datalog: x}},"
     " {id: a, question: q, gold: {datalog: x}}]", "Duplicate"),
])
def test_invalid_datasets(tmp_path, text, message):
    path = tmp_path / "bad.yaml"
    path.write_text(text)
    with pytest.raises(DatasetError, match=message):
        load_dataset(path)


def test_execute(nl):
    execution = execute(nl, "ans(s) :- mentions(s, 'pain')", "datalog")
    assert execution.ok and sorted(execution.rows) == [(1,), (2,)]
    squall = execute(nl, "obtain every Mentions (?s; ?t).", "squall")
    assert len(squall.rows) == 3
    error = execute(nl, "ans(s) :- mentions(s, 'pain'", "datalog")
    assert not error.ok and "Error" in error.error
    assert not any(
        getattr(s, "name", "") == "ans" for s in nl.symbol_table
    )


def test_run_with_timeout():
    import time

    def slow():
        while True:
            time.sleep(0.01)

    with pytest.raises(QueryTimeout):
        run_with_timeout(slow, 0.1)
    assert run_with_timeout(lambda: 3, 1) == 3


def test_ask_and_evaluate(nl, dataset):
    system = Scripted({
        "Which studies mention pain?": "ans(s) :- mentions(s, 'pain')",
        "Quelles études ?": "ans(s) :- mentions(s, t)",
        "Which terms do pain studies mention?": "",
    })
    answers = ask(system, dataset, ["en", "fr"])
    assert [(a["id"], a["language"]) for a in answers] == [
        ("q1", "en"), ("q1", "fr"), ("q2", "en")
    ]
    assert answers[0]["query_language"] == "datalog"
    gold = gold_answers(nl, dataset)
    assert sorted(gold["q2"]["rows"]) == [("fear",), ("pain",)]
    results = evaluate(nl, dataset, answers, gold)
    assert [r.f1 for r in results] == [1.0, pytest.approx(0.8), 0.0]
    assert not results[2].executed
    scores = summary(dataset, results)
    assert scores["overall"]["questions"] == 3
    assert scores["overall"]["exact"] == pytest.approx(1 / 3)
    assert scores["languages"]["fr"]["f1"] == pytest.approx(0.8)
    assert scores["tags"]["join"]["f1"] == 0.0
    report = run_report("scripted", scores)
    assert "| all | 3 |" in report and "| fr | 1 |" in report
    assert "| scripted | 3 |" in comparison_report({"scripted": scores})
    json.dumps(scores)


def test_endpoint_protocol(dataset):
    system = Scripted({"Which studies?": "ans(s) :- study(s)"})
    server = make_server(system, [dataset.uri], port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    try:
        response = httpx.get(
            url, params={"question": "Which studies?", "dataset": dataset.uri}
        )
        assert response.json() == {
            "dataset": dataset.uri, "question": "Which studies?",
            "query": "ans(s) :- study(s)", "language": "datalog",
            "explanation": "", "valid": True, "error": "", "calls": 1,
            "tokens": 7,
        }
        missing = httpx.get(url, params={"question": "q"})
        assert missing.status_code == 400
        unknown = httpx.get(url, params={"question": "q", "dataset": "x"})
        assert unknown.status_code == 404
        endpoint = EndpointSystem(url, dataset.uri, "remote")
        generation = endpoint.generate("Which studies?", "en")
        assert generation.query == "ans(s) :- study(s)" and generation.valid
        assert generation.tokens == 7
        broken = EndpointSystem(url, "x").generate("q", "en")
        assert not broken.valid and "404" in broken.error
    finally:
        server.shutdown()


def test_unknown_predicates_can_give_no_rows(nl):
    from neurolang.exceptions import SymbolNotFoundError

    def unknown(query):
        raise SymbolNotFoundError("Symbol not found dbo:launchDate")

    nl.execute_datalog_program = unknown
    failed = execute(nl, "ans(x) :- dbo:launchDate(x)", "datalog")
    assert not failed.ok and "SymbolNotFoundError" in failed.error
    empty = execute(nl, "ans(x) :- dbo:launchDate(x)", "datalog",
                    unknown_is_empty=True)
    assert empty.ok and empty.rows == []
