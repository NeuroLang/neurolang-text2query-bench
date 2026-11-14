"""Time the engine build and atlas_coverage per atlas on real data."""
import resource, sys, time, tracemalloc
from pathlib import Path
from neurolang_apps.utils import engine_registry as er

data_dir, engine, use_cache = Path(sys.argv[1]), sys.argv[2], sys.argv[3] == "cache"
timings = []
import os; TRACE = bool(os.environ.get("TRACE"))
if hasattr(er, "atlas_coverage"):
    find = er.atlas_coverage
    def timed(img, names, *args, **kw):
        t = time.time(); tracemalloc.start() if TRACE else None
        rows = find(img, names, *args, **kw)
        peak = tracemalloc.get_traced_memory()[1] / 2**20 if TRACE else 0; tracemalloc.stop()
        timings.append((len(names), len(rows), time.time() - t, peak,
                        (rows.probability >= 1e-2).sum()))
        return rows
    er.atlas_coverage = timed
t0 = time.time()
nl = er.build_engine(engine, data_dir, None, use_cache=use_cache)
print(f"{engine} build use_cache={use_cache}: {time.time() - t0:.1f}s")
for n, rows, t, peak, rows2 in timings:
    print(f"  coverage of {n} regions: {rows} rows >= 1e-3 ({rows2} >= 1e-2), {t:.1f}s, peak traced {peak:.0f} MB")
for name in ["schaefer", "destrieux", "tian"]:
    if f"{name}_covered" in nl.symbol_table:
        print(f"  {name}_covered rows", len(nl.symbol_table[f"{name}_covered"].value.unwrap()))
    print(f"  {name}_activated rows", len(nl.symbol_table[f"{name}_activated"].value.unwrap()))
print("  maxrss MB", round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20))
