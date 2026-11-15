"""The queries of (IV) in NeuroLang's doc/ontologies.rst, with rdf:type:
our experiments and the Stroop studies of Neurosynth made instances of
Cognitive Atlas tasks by the task's name, and the classes of the questions
named by their labels. Open world, then closed world (the constraints
removed), on the neurosynth engine.

    PYTHONPATH=<NeuroLang packages> .venv-dsparity/bin/python \\
        scripts/ontology_example/run_rdf_type.py TIMEOUT [NAME...]
"""
import signal
import sys
import time
from pathlib import Path

import pandas as pd
from nl_expr.expressions import Symbol
from text2query_bench.engine import build_engine

EXPERIMENTS = """our_experiment('e1', 'stroop task')
our_experiment('e2', 'stop signal task')
our_experiment('e3', 'go-no-go task')
rdf:type(e, t) :- our_experiment(e, n), cogat_term(t, n)
"""
STROOP = ("rdf:type(s, t) :- mentions(s, 'stroop task'), "
          "cogat_term(t, 'stroop task')\n")
STOP = ("rdf:type(s, t) :- mentions(s, 'stop signal'), "
        "cogat_term(t, 'stop signal task')\n")
INHIBITION = ("inhibition_study(s) :- exists(x, c, k; cogpo:has_contrast(s, x),"
              " cogat:measures(x, c), rdf:type(c, k), "
              "cogat_term(k, 'response inhibition'))\n")
QUERIES = {
    "experiment_task": EXPERIMENTS
    + "ans(e, t) :- rdf:type(e, t), our_experiment(e, n)",
    "experiment_contrast": EXPERIMENTS
    + "ans(e) :- exists(x; cogpo:has_contrast(e, x))",
    "experiment_inhibition": EXPERIMENTS
    + "ans(e) :- exists(x, c, k; cogpo:has_contrast(e, x), "
    "cogat:measures(x, c), rdf:type(c, k), "
    "cogat_term(k, 'response inhibition'))",
    "experiment_which_contrast": EXPERIMENTS
    + "ans(e, x) :- cogpo:has_contrast(e, x)",
    "study_contrast": STROOP + "ans(s) :- exists(x; cogpo:has_contrast(s, x))",
    "study_incongruent": STROOP
    + "ans(s) :- exists(x, k; cogpo:has_contrast(s, x), rdf:type(x, k), "
    "cogat_term(k, 'stroop_task-incongruent_minus_congruent'))",
    "study_inhibition": STROOP + INHIBITION + "ans(s) :- inhibition_study(s)",
    "study_which_form": STROOP
    + "ans(s, c) :- exists(x, k; cogpo:has_contrast(s, x), "
    "cogat:measures(x, c), rdf:type(c, k), "
    "cogat_term(k, 'response inhibition'))",
    "p_active_given_inhibition": STROOP + INHIBITION
    + "p_active_given_inhibition(i, j, k, PROB) :- (activated(i, j, k, s) & "
    "selected_study(s)) // (inhibition_study(s) & selected_study(s))\n"
    "ans(i, j, k, p) :- p_active_given_inhibition(i, j, k, p)",
    "stop_inhibition": STOP + INHIBITION + "ans(s) :- inhibition_study(s)",
}


def stop(*_):
    raise KeyboardInterrupt


signal.signal(signal.SIGALRM, stop)
nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
names = sys.argv[2:] or list(QUERIES)


def run(world):
    for name in names:
        t = time.perf_counter()
        signal.alarm(int(sys.argv[1]))
        try:
            with nl.scope:
                rows = sorted(map(tuple, nl.execute_datalog_program(
                    QUERIES[name])))
            out = f"{len(rows)} rows" + (f" {rows}" if len(rows) < 5 else "")
            if name.startswith("p_active") and rows:
                out += f", max p {max(r[-1] for r in rows):.3f}"
        except KeyboardInterrupt:
            out = "stopped"
        except Exception as error:
            out = f"{type(error).__name__}: {error}"[:300]
        finally:
            signal.alarm(0)
        print(f"{world} {name}: {time.perf_counter() - t:.1f}s {out}",
              flush=True)


run("open")
del nl.program_ir.symbol_table[Symbol("__constraints__")]
nl.program_ir.categorized_constraints = {}
for predicate in ("cogpo:has_contrast", "cogat:measures"):
    nl.add_tuple_set(pd.DataFrame(columns=range(2)), name=predicate)
run("closed")
