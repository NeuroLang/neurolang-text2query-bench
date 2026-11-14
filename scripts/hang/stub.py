import sys, time, traceback, faulthandler
from pathlib import Path
from text2query_bench.engine import build_engine, execute
import neurolang.frontend.query_resolution_datalog as qrd
import nl_core.datalog.chase.general as cg
ROOT = Path("/Users/bot/neurolang-text2query-bench")
nl = build_engine("neurosynth", ROOT / "neurolang_data")
orig = qrd.stratify
def stub(rules, prog):
    if len(rules.formulas) > 1000:
        print("STUB stratify", len(rules.formulas), file=sys.stderr, flush=True)
        return [list(rules.formulas)], True
    return orig(rules, prog)
qrd.stratify = stub
cg.stratify = stub
from neurolang_apps.utils.llm.validation import check_query
for q in sys.argv[1:]:
    faulthandler.dump_traceback_later(240, exit=True)
    t = time.perf_counter(); r = check_query(nl, q, "datalog")
    print(f"check {time.perf_counter()-t:.1f}s ok={r.ok} {r.message[:300]!r}", file=sys.stderr, flush=True)
    t = time.perf_counter()
    try:
        ex = execute(nl, q, "datalog", 200)
        print(f"run {time.perf_counter()-t:.1f}s rows={len(ex.rows)} err={str(ex.error)[:1500]} {ex.rows[:5]}", file=sys.stderr, flush=True)
    except Exception:
        traceback.print_exc()
    faulthandler.cancel_dump_traceback_later()
