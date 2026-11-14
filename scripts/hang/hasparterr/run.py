"""Run datalog queries on the neurosynth engine, printing answer sizes,
a sample, or the error."""
import sys
import time
import traceback
from pathlib import Path

from text2query_bench.engine import build_engine

nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
for q in sys.argv[1:]:
    t = time.perf_counter()
    print("==", q, flush=True)
    try:
        with nl.scope:
            r = nl.execute_datalog_program(q)
        df = r.as_pandas_dataframe() if hasattr(r, "as_pandas_dataframe") else r
        print(f"OK {time.perf_counter() - t:.1f}s rows={len(df)}")
        print(df.head(8))
    except Exception:
        traceback.print_exc(limit=-2)
