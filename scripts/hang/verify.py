import sys, time, faulthandler
from pathlib import Path
from text2query_bench.engine import build_engine, execute
from neurolang_apps.utils.llm.validation import check_query
import neurolang
print(neurolang.__file__, file=sys.stderr)
ROOT = Path("/Users/bot/neurolang-text2query-bench")
nl = build_engine("neurosynth", ROOT / "neurolang_data")
for q in sys.argv[1:]:
    faulthandler.dump_traceback_later(400, exit=True)
    t = time.perf_counter(); r = check_query(nl, q, "datalog")
    print(f"check {time.perf_counter()-t:.1f}s ok={r.ok} {r.message[:200]!r} :: {q}", file=sys.stderr, flush=True)
    t = time.perf_counter()
    ex = execute(nl, q, "datalog", 300)
    print(f"  run {time.perf_counter()-t:.1f}s rows={len(ex.rows)} err={str(ex.error)[:300]!r} {ex.rows[:5]}", file=sys.stderr, flush=True)
    faulthandler.cancel_dump_traceback_later()
