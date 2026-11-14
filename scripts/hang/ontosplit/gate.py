"""Xrewrite of ``q(x) :- ro:has_part(x, y)`` (or ``sys.argv[2:]`` bodies)
with the constraints that can hold given one instance of the Cognitive
Atlas class ``sys.argv[1]``, the full ones only on atoms with a variable
out of the head (``chased=True``)."""
import sys
import time
from pathlib import Path

from nl_core.datalog.ontologies_rewriter import OntologyRewriter
from nl_expr.expressions import Symbol
from nl_expr.logic import Implication, Union
from text2query_bench.engine import build_engine

nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
cls = "http://www.cognitiveatlas.org/ontology/cogat.owl#" + sys.argv[1]
held = nl._constraints_that_can_hold(frozenset([Symbol(cls)]))
print("held", sum(map(len, held.values())), flush=True)
x, y, q = Symbol("x"), Symbol("y"), Symbol("q")
for prop in ["ro:has_part", "ro:part_of"]:
    query = Union((Implication(q(x), Symbol(prop)(x, y)),))
    t = time.perf_counter()
    out = OntologyRewriter(query, held, chased=True).Xrewrite()
    print(prop, "xrewrite", len(out), f"{time.perf_counter() - t:.1f}s", flush=True)
