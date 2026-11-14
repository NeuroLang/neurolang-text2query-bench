import faulthandler, sys, time
from pathlib import Path
from text2query_bench.engine import build_engine
from neurolang_apps.utils.llm.validation import check_query
ROOT = Path("/Users/bot/neurolang-text2query-bench")
t = time.perf_counter()
nl = build_engine("neurosynth", ROOT / "neurolang_data")
print(f"engine {time.perf_counter()-t:.1f}s", flush=True)
for q in sys.argv[1:]:
    faulthandler.dump_traceback_later(float(__import__('os').environ.get('DUMP', 60)), exit=True)
    t = time.perf_counter()
    r = check_query(nl, q, "datalog")
    faulthandler.cancel_dump_traceback_later()
    print(f"{time.perf_counter()-t:.1f}s ok={r.ok} {r.message[:200]!r} :: {q}", flush=True)
