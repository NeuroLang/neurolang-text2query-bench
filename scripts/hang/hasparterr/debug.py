"""Show the query rule and the rules of its predicate when the magic-sets
rewrite of a query on the neurosynth engine raises."""
import sys
import traceback
from pathlib import Path

from text2query_bench.engine import build_engine
from nl_core.datalog import magic_sets

orig = magic_sets.adorn_code


def adorn_code(query, datalog, sips):
    print("QUERY", query)
    idb = datalog.intensional_database()
    for f in idb.get(query.functor, magic_sets.Union(())).formulas:
        print("  RULE", type(f).__name__, f)
        for a in getattr(f.antecedent, "formulas", (f.antecedent,)):
            for r in idb.get(getattr(a, "functor", None), magic_sets.Union(())).formulas[:3]:
                print("     SUB", type(r).__name__, r)
    res = orig(query, datalog, sips)
    print("ADORNED", len(res[0].formulas))
    return res


magic_sets.adorn_code = adorn_code
nl = build_engine("neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data"))
for q in sys.argv[1:]:
    try:
        with nl.scope:
            nl.execute_datalog_program(q)
            r = nl.solve_all()
        print("OK", {k: len(v) for k, v in r.items()})
    except Exception:
        traceback.print_exc(limit=-3)
