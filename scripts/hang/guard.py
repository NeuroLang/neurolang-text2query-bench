import sys, time
from pathlib import Path
from text2query_bench.engine import build_engine
from neurolang_apps.utils.llm.validation import check_query, run_preview
nl = build_engine("neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data"))
q = sys.argv[1]
t = time.perf_counter(); c = check_query(nl, q, "datalog"); print(f"check {time.perf_counter()-t:.1f}s ok={c.ok}", file=sys.stderr)
t = time.perf_counter(); p = run_preview(nl, q, "datalog", 10, "neurosynth", 30.0, 4000); print(f"preview {time.perf_counter()-t:.1f}s ok={p.ok} {p.text[:200]!r}", file=sys.stderr)
