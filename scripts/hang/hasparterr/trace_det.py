"""Run queries on the neurosynth engine, printing for each deterministic
stratum the rules in det_idb, the constraints the rewriting uses, and the
rules Xrewrite returns."""
import sys
import time
from pathlib import Path

from neurolang.frontend import probabilistic_frontend as pf
from text2query_bench.engine import build_engine

orig = pf.NeurolangPDL._rewrite_program_with_ontology


def traced(self, det_idb, *args):
    t = time.perf_counter()
    out = orig(self, det_idb, *args)
    used = getattr(pf, "constraints_that_can_hold", None)
    n_used = (
        sum(map(len, used(self.program_ir.get_constraints(), *args).values()))
        if used and args else "all"
    )
    print(f"  det_idb {len(det_idb.formulas)} rules, constraints used "
          f"{n_used}, Xrewrite -> {len(out.formulas)} rules in "
          f"{time.perf_counter() - t:.2f}s")
    for r in det_idb.formulas[:4]:
        print("    ", str(r)[:150])
    return out


pf.NeurolangPDL._rewrite_program_with_ontology = traced
nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
for q in sys.argv[1:]:
    print("==", q, flush=True)
    t = time.perf_counter()
    with nl.scope:
        r = nl.execute_datalog_program(q)
    print(f"  {time.perf_counter() - t:.1f}s rows={len(r)}")
