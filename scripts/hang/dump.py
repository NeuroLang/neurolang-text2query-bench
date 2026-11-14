import sys, pickle, os
from pathlib import Path
from text2query_bench.engine import build_engine
import neurolang.frontend.query_resolution_datalog as qrd
ROOT = Path("/Users/bot/neurolang-text2query-bench")
nl = build_engine("neurosynth", ROOT / "neurolang_data")
def strat(rules, prog):
    seen = set(prog.extensional_database().keys()) | set(prog.builtins())
    import traceback
    sys.setrecursionlimit(100000)
    try:
        with open(sys.argv[1], "wb") as f:
            from nl_core.datalog import expression_processing as ep
            from nl_expr.expressions import Constant
            simple = [(r.consequent.functor.name, [a.functor.name for a in ep.extract_logic_atoms(r.antecedent) if hasattr(a.functor, "name")], r.antecedent == Constant(True), type(r).__name__) for r in rules.formulas]
            pickle.dump((simple, {getattr(k, "name", str(k)) for k in seen}), f)
    except BaseException:
        traceback.print_exc()
    print("dumped", len(rules.formulas), file=sys.stderr, flush=True)
    os._exit(0)
qrd.stratify = strat
from neurolang_apps.utils.llm.validation import check_query
check_query(nl, sys.argv[2], "datalog")
