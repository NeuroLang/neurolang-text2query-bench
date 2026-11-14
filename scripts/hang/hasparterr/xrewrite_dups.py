"""Run the Xrewrite of ``q(x) :- pred(x, y)`` on the neurosynth engine for
argv[1] seconds and count its rules against their bodies' predicates, to see
whether variable renaming defeats the duplicate check."""
import collections
import signal
import sys
from pathlib import Path

from nl_expr.expressions import Symbol
from nl_expr.logic import Implication, Union
from nl_core.datalog import ontologies_rewriter as orm
from text2query_bench.engine import build_engine

nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
x, y = Symbol("x"), Symbol("y")
pred = sys.argv[2] if len(sys.argv) > 2 else "ro:has_part"
rule = Implication(Symbol("q")(x), Symbol(pred)(x, y))
orw = orm.OntologyRewriter(Union((rule,)), nl.program_ir.get_constraints())
seen = []
orig = orw._is_new_rewriting


def is_new(new_q0, q_rew, q_explored):
    seen.append(new_q0)
    return orig(new_q0, q_rew, q_explored)


orw._is_new_rewriting = is_new


def stop(*_):
    raise KeyboardInterrupt


signal.signal(signal.SIGALRM, stop)
signal.alarm(int(sys.argv[1]))
try:
    orw.Xrewrite()
    print("finished")
except KeyboardInterrupt:
    print("stopped")
print("rewritings", len(seen), "distinct", len(set(seen)))
shapes = collections.Counter(
    (str(r.consequent), str(r.antecedent)[:0] or tuple(sorted(
        str(getattr(f, "functor", f)) for f in getattr(
            r.antecedent, "formulas", (r.antecedent,))
    ))) for r in seen
)
print("distinct (head, body predicates)", len(shapes))
for r in seen[:3] + seen[-3:]:
    print(r)
