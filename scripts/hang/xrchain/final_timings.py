"""Time the open-world Cognitive Atlas queries of the Stroop example on the
neurosynth engine, in one process and a fixed order, and check the study
answers, as sets, against mentions(s, 'stroop task'), the instances of the
only class (CAO_00872, Stroop task) with a chain to response inhibition
(scripts/ontology_example/inhibition_tasks.py, rdflib).
argv: timeout (s), query names (default: all, in order)."""
import signal
import sys
import time
from pathlib import Path

from text2query_bench.engine import build_engine

STROOP = "cogat:CAO_00872(s) :- mentions(s, 'stroop task')\n"
STOP = "cogat:CAO_00871(s) :- mentions(s, 'stop signal')\n"
INHIBITION = ("inhibition_study(s) :- cogpo:has_contrast(s, x), "
              "cogat:measures(x, c), cogat:CAO_00487(c)\n")
QUERIES = {
    "has_contrast": STROOP + "ans(s) :- cogpo:has_contrast(s, x)",
    "has_contrast_01515": STROOP + "ans(s) :- cogpo:has_contrast(s, x), "
    "cogat:CAO_01515(x)",
    "has_contrast_measures": STROOP + "ans(s) :- cogpo:has_contrast(s, x), "
    "cogat:measures(x, c)",
    "inhibition_study": STROOP + INHIBITION + "ans(s) :- inhibition_study(s)",
    "inhibition_with_concept": STROOP + "ans(s, c) :- cogpo:has_contrast(s, x),"
    " cogat:measures(x, c), cogat:CAO_00487(c)",
    "stop_inhibition_study": STOP + INHIBITION
    + "ans(s) :- inhibition_study(s)",
    "p_active_given_inhibition": STROOP + INHIBITION
    + "p_active_given_inhibition(i, j, k, PROB) :- (activated(i, j, k, s) & "
    "selected_study(s)) // (inhibition_study(s) & selected_study(s))\n"
    "ans(i, j, k, p) :- p_active_given_inhibition(i, j, k, p)",
    # doc/ontologies.rst: one instance of N-back 2-back, measuring some
    # working memory
    "measures_working_memory": "cogat:CAO_01210('n_back')\n"
    "ans(s) :- cogat:measures(s, c), cogat:CAO_00587(c)",
}
STUDY_ANSWERS = {"has_contrast", "has_contrast_01515",
                 "has_contrast_measures", "inhibition_study"}


def stop(*_):
    raise KeyboardInterrupt


signal.signal(signal.SIGALRM, stop)
nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
with nl.scope:
    stroop = {r[0] for r in nl.execute_datalog_program(
        "ans(s) :- mentions(s, 'stroop task')")}
print("mentions stroop task:", len(stroop), flush=True)
for name in sys.argv[2:] or QUERIES:
    t = time.perf_counter()
    signal.alarm(int(sys.argv[1]))
    try:
        with nl.scope:
            rows = {tuple(r) for r in nl.execute_datalog_program(
                QUERIES[name])}
        out = f"{len(rows)} rows"
        if name in STUDY_ANSWERS:
            same = {r[0] for r in rows} == stroop
            out += f", = the Stroop studies: {same}"
        if len(rows) < 3:
            out += f" {sorted(rows)}"
        if name.startswith("p_active") and rows:
            out += f", max p {max(r[-1] for r in rows):.3f}"
    except KeyboardInterrupt:
        out = "stopped"
    finally:
        signal.alarm(0)
    print(f"{name}: {time.perf_counter() - t:.1f}s {out}", flush=True)
