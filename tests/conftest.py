import pytest

from text2query_bench.dataset import load_dataset

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
