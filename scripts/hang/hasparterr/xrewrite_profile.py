"""Profile the ontology rewriting (Xrewrite) of ``q(x) :- ro:has_part(x, y)``
on the neurosynth engine, stopping after argv[1] seconds."""
import cProfile
import pstats
import signal
import sys
from pathlib import Path

from nl_expr.expressions import Symbol
from nl_expr.logic import Implication, Union
from nl_core.datalog.ontologies_rewriter import OntologyRewriter
from text2query_bench.engine import build_engine

nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
x, y = Symbol("x"), Symbol("y")
pred = sys.argv[2] if len(sys.argv) > 2 else "ro:has_part"
rule = Implication(Symbol("q")(x), Symbol(pred)(x, y))
orw = OntologyRewriter(Union((rule,)), nl.program_ir.get_constraints())
print("constraints", sum(len(v) for v in orw.union_of_constraints.values()))


def stop(*_):
    raise KeyboardInterrupt


signal.signal(signal.SIGALRM, stop)
signal.alarm(int(sys.argv[1]))
prof = cProfile.Profile()
try:
    prof.runcall(orw.Xrewrite)
    print("finished")
except KeyboardInterrupt:
    print("stopped")
pstats.Stats(prof).sort_stats("cumulative").print_stats(25)
