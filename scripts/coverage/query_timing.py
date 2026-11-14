"""Time forward inference over the Schaefer parcels for a term: covered vs activated."""
import sys, time
from pathlib import Path
from neurolang_apps.utils import engine_registry as er
from neurolang.probabilistic import dalvi_suciu_lift, small_dichotomy_theorem_based_solver as sd

nl = er.build_engine("neurosynth", Path(sys.argv[1]), None)
# lifted solvers only: a query that would need WMC fails
nl.probabilistic_solvers = (sd.solve_succ_query, dalvi_suciu_lift.solve_succ_query)
nl.probabilistic_marg_solvers = (sd.solve_marg_query, dalvi_suciu_lift.solve_marg_query)
for relation in ["schaefer_activated", "schaefer_covered", "destrieux_covered", "tian_covered"]:
    query = f"""
    active(l, s) :- {relation}(l, s), selected_study(s)
    topic(s) :- mentions(s, 'pain'), selected_study(s)
    ans(l, p) :- PROB[active(l, s) // topic(s)] = p"""
    for rep in range(2):
        with nl.scope:
            t = time.time()
            res = nl.execute_datalog_program(query)
            frame = res.as_pandas_dataframe() if hasattr(res, "as_pandas_dataframe") else res
            took = time.time() - t
    top = frame.sort_values(frame.columns[-1], ascending=False).head(3)
    print(f"{relation}: {took:.2f}s (2nd run), {len(frame)} rows; top: "
          + "; ".join(f"{r[0]} {r[1]:.3f}" for r in top.itertuples(index=False)))
