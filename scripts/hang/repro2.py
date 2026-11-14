import faulthandler, sys, time, collections
from pathlib import Path
from text2query_bench.engine import build_engine
import neurolang.frontend.query_resolution_datalog as qrd
from nl_core.datalog import expression_processing as ep
ROOT = Path("/Users/bot/neurolang-text2query-bench")
nl = build_engine("neurosynth", ROOT / "neurolang_data")
orig = qrd.stratify
calls = collections.Counter()
def strat(rules, prog):
    fs = rules.formulas
    print("stratify on", len(fs), "rules; heads", len({r.consequent.functor for r in fs}), flush=True, file=sys.stderr)
    for r in fs[:5]: print("  ", r, file=sys.stderr)
    orig_rec = ep.stratify_obtain_recursive_stratum
    def rec(tp, seen):
        calls['rec'] += 1
        if calls['rec'] % 50 == 0: print("rec call", calls['rec'], len(tp), flush=True, file=sys.stderr)
        return orig_rec(tp, seen)
    ep.stratify_obtain_recursive_stratum = rec
    t=time.perf_counter(); out = orig(rules, prog); print("stratify", time.perf_counter()-t, len(out[0]), flush=True, file=sys.stderr); return out
qrd.stratify = strat
faulthandler.dump_traceback_later(60, exit=True)
from neurolang_apps.utils.llm.validation import check_query
print(check_query(nl, sys.argv[1], "datalog"))
