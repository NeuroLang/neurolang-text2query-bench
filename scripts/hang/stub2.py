import sys, time, traceback, faulthandler
from pathlib import Path
from text2query_bench.engine import build_engine
import neurolang.frontend.query_resolution_datalog as qrd
ROOT = Path("/Users/bot/neurolang-text2query-bench")
nl = build_engine("neurosynth", ROOT / "neurolang_data")
orig = qrd.stratify
def stub(rules, prog):
    if len(rules.formulas) > 1000:
        return [list(rules.formulas)], True
    return orig(rules, prog)
qrd.stratify = stub
for q in sys.argv[1:]:
    faulthandler.dump_traceback_later(90, exit=True)
    try:
        t=time.perf_counter(); r = nl.execute_datalog_program(q); print("OK", time.perf_counter()-t, r, file=sys.stderr)
    except Exception:
        traceback.print_exc()
