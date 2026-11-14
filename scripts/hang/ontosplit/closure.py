"""Size of the constraints Xrewrite would need under the chase/rewrite
split: the existential ones and the full ones whose body has a predicate
derivable after an existential step (closure R), among those that can hold
with one instance of ``sys.argv[1]``; then time Xrewrite of the query."""
import sys
import time
from pathlib import Path

from nl_core.datalog.expression_processing import extract_logic_atoms
from nl_core.datalog.ontologies_rewriter import OntologyRewriter
from nl_expr.expressions import Symbol
from nl_expr.logic import Implication, Union
from text2query_bench.engine import build_engine

nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
cls = "http://www.cognitiveatlas.org/ontology/cogat.owl#" + sys.argv[1]
held = nl._constraints_that_can_hold(frozenset([Symbol(cls)]))
sigmas = [s for v in held.values() for s in v]


def existential(s):
    body = set().union(*(a._symbols for a in extract_logic_atoms(s.antecedent)))
    return bool(set(s.consequent.args) - body)


ex = [s for s in sigmas if existential(s)]
full = [s for s in sigmas if not existential(s)]
R = {s.consequent.functor for s in ex}
while True:
    new = {s.consequent.functor for s in full
           if any(a.functor in R for a in extract_logic_atoms(s.antecedent))}
    if new <= R:
        break
    R |= new
touch = [s for s in full
         if any(a.functor in R for a in extract_logic_atoms(s.antecedent))]
print("held", len(sigmas), "exist", len(ex), "full", len(full),
      "R", len(R), "full touching R", len(touch), flush=True)
cons = {}
for s in ex + touch:
    cons.setdefault(s.consequent.functor.name, set()).add(s)
x, y, q = Symbol("x"), Symbol("y"), Symbol("q")
query = Union((Implication(q(x), Symbol("ro:has_part")(x, y)),))
t = time.perf_counter()
out = OntologyRewriter(query, cons).Xrewrite()
print("xrewrite", len(out), f"{time.perf_counter() - t:.1f}s")
