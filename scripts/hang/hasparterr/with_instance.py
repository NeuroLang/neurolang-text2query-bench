"""Give one instance to a Cognitive Atlas class restricted by
``ro:has_part some D`` and time ``ans(x) :- ro:has_part(x, y)``: the
rewriting then uses the constraints this instance makes hold."""
import signal
import sys
import time
from pathlib import Path

from nl_core.datalog.expression_processing import extract_logic_atoms
from text2query_bench.engine import build_engine

nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
cons = nl.program_ir.get_constraints()
links = {next(iter(extract_logic_atoms(c.antecedent))).functor
         for c in cons["ro:has_part"]}
cls = next(
    a.functor for v in cons.values() for c in v
    for a in extract_logic_atoms(c.antecedent)
    if len(a.args) == 1 and c.consequent.functor in links
)
print("class", cls.name)
nl.add_tuple_set([("individual",)], name=cls.name)
holds = frozenset([cls])
print("constraints that can hold", sum(
    map(len, nl._constraints_that_can_hold(holds).values())), flush=True)


def stop(*_):
    raise KeyboardInterrupt


signal.signal(signal.SIGALRM, stop)
for q in sys.argv[2:] or ["ans(x, y) :- ro:has_part(x, y)", "ans(x) :- ro:has_part(x, y)"]:
    t = time.perf_counter()
    signal.alarm(int(sys.argv[1]) if len(sys.argv) > 1 else 120)
    try:
        with nl.scope:
            r = set(nl.execute_datalog_program(q))
    except KeyboardInterrupt:
        r = "stopped"
    signal.alarm(0)
    print(q, f"{time.perf_counter() - t:.1f}s", r, flush=True)
