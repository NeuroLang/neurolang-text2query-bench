"""Run the Xrewrite of ``q(x) :- pred(x, y)`` on the neurosynth engine for
argv[1] seconds; print, every few seconds, the explored rules by body length,
and the constraints that fired most, to see whether the rewriting is merely
large or unbounded (bodies growing without end)."""
import collections
import signal
import sys
import time
from pathlib import Path

from nl_expr.expressions import Symbol
from nl_expr.logic import Implication, Union
from nl_core.datalog import ontologies_rewriter as orm
from text2query_bench.engine import build_engine

nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
cons = nl.program_ir.get_constraints()
print("constraint heads", len(cons),
      "constraints", sum(len(v) for v in cons.values()))
x, y = Symbol("x"), Symbol("y")
pred = sys.argv[2] if len(sys.argv) > 2 else "ro:has_part"
rule = Implication(Symbol("q")(x), Symbol(pred)(x, y))
orw = orm.OntologyRewriter(Union((rule,)), cons)
fired = collections.Counter()
lengths = collections.Counter()
orig = orw.rewriting_step


def size(r):
    return len(getattr(r.antecedent, "formulas", (r.antecedent,)))


def step(q0, sigma, rename_count):
    out = orig(q0, sigma, rename_count)
    if out:
        fired[str(sigma)[:160]] += len(out)
        for r in out:
            lengths[size(r)] += 1
    return out


orw.rewriting_step = step
start = time.time()


def report(*_):
    print(f"{time.time() - start:.0f}s by body length", sorted(lengths.items()),
          flush=True)


end = start + int(sys.argv[1])


def tick(*_):
    report()
    if time.time() > end:
        raise KeyboardInterrupt
    signal.alarm(10)


signal.signal(signal.SIGALRM, tick)
signal.alarm(10)
try:
    res = orw.Xrewrite()
    print("finished", len(res))
except KeyboardInterrupt:
    print("stopped")
signal.alarm(0)
report()
for s, n in fired.most_common(15):
    print(n, s)
