import faulthandler, sys, time, collections, pickle
from pathlib import Path
from text2query_bench.engine import build_engine
import neurolang.frontend.query_resolution_datalog as qrd
from nl_core.datalog import expression_processing as ep
from nl_core.datalog.magic_sets import _strongly_connected_components
ROOT = Path("/Users/bot/neurolang-text2query-bench")
nl = build_engine("neurosynth", ROOT / "neurolang_data")
def rc(rules):
    heads = {r.consequent.functor for r in rules}
    depends_on = {head: set() for head in heads}
    for r in rules:
        depends_on[r.consequent.functor] |= ep._body_predicates(r) & heads
    component = _strongly_connected_components(depends_on)
    members = collections.defaultdict(set)
    for p, c in component.items(): members[c].add(p)
    for head in dict.fromkeys(r.consequent.functor for r in rules):
        yield members[component[head]]
if sys.argv[1] == "new": ep._recursive_components = rc
orig = qrd.stratify
calls = collections.Counter()
orig_rec = ep.stratify_obtain_recursive_stratum
def rec(tp, seen):
    calls['rec'] += 1
    t = time.perf_counter(); out = orig_rec(tp, seen)
    if calls['rec'] % 20 == 1: print("rec call", calls['rec'], len(tp), len(out[0]), f"{time.perf_counter()-t:.2f}s", file=sys.stderr, flush=True)
    return out
ep.stratify_obtain_recursive_stratum = rec
def strat(rules, prog):
    t=time.perf_counter(); out = orig(rules, prog)
    print("stratify", len(rules.formulas), f"{time.perf_counter()-t:.2f}s strata", len(out[0]), "rec calls", calls['rec'], file=sys.stderr, flush=True); return out
qrd.stratify = strat
faulthandler.dump_traceback_later(600, exit=True)
from neurolang_apps.utils.llm.validation import check_query
for q in sys.argv[2:]:
    t=time.perf_counter(); r = check_query(nl, q, "datalog"); print(f"check {time.perf_counter()-t:.1f}s", r.ok, r.message[:200], file=sys.stderr)
