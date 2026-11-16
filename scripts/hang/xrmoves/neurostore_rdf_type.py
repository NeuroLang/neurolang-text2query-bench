"""neurostore_inhibition.py with the syntax of doc/ontologies.rst (IV):
the studies typed with rdf:type by the Atlas name of each of the five
inhibition tasks whose name is a NeuroStore term, and the open-world
inhibition_study(s) with exists, against each single mentions query and
their union: rows and time of each, one at a time.
argv: timeout (s), applied to the build and to each query."""
import cProfile
import os
import pstats
import signal
import subprocess
import sys
import time
from pathlib import Path

import neurolang
from neurolang_apps.utils.engine_registry import build_engine

TASKS = {  # Atlas name (cogat_term): NeuroStore term
    "stroop task": "stroop task",
    "color-word stroop task": "color word stroop",
    "simon task": "simon task",
    "go-no-go task": "nogo task",
    "choice reaction time task": "choice reaction time",
}
CAO = {"CAO_00872", "CAO_00707", "CAO_00864", "CAO_00827", "CAO_00810"}
TERMS = "".join(f"task_term('{n}', '{m}')\n" for n, m in TASKS.items())
TYPES = TERMS + ("rdf:type(s, t) :- task_term(n, m), mentions(s, m), "
                 "cogat_term(t, n)\n")
INHIBITION = ("inhibition_study(s) :- exists(x, c, k; cogpo:has_contrast(s, x),"
              " cogat:measures(x, c), rdf:type(c, k), "
              "cogat_term(k, 'response inhibition'))\n")


def stop(*_):
    raise KeyboardInterrupt


signal.signal(signal.SIGALRM, stop)
tree = Path(neurolang.__file__).parents[3]
print("commit", subprocess.run(
    ["git", "-C", str(tree), "log", "-1", "--format=%H %cI %s"],
    capture_output=True, text=True).stdout.strip(), flush=True)
t = time.perf_counter()
signal.alarm(int(sys.argv[1]))
nl = build_engine(
    "neurostore", Path("/Users/bot/neurolang-text2query-bench/neurolang_data"),
    2.0,
)
signal.alarm(0)
print(f"build {time.perf_counter() - t:.1f}s", flush=True)


def timed(name, program):
    t = time.perf_counter()
    signal.alarm(int(sys.argv[1]))
    try:
        with nl.scope:
            rows = {r[0] if len(r) == 1 else tuple(r)
                    for r in nl.execute_datalog_program(program)}
        out = f"{len(rows)} rows"
    except KeyboardInterrupt:
        rows, out = None, "stopped"
    finally:
        signal.alarm(0)
    print(f"{name}: {time.perf_counter() - t:.1f}s {out}", flush=True)
    return rows


classes = timed("Atlas classes of the names",
                TERMS + "ans(n, t) :- task_term(n, m), cogat_term(t, n)")
print("  the five CAO ids:",
      {t.split("#")[-1] for _, t in classes} == CAO, flush=True)
single = {}
for name, term in TASKS.items():
    single[name] = timed(f"mentions '{term}'",
                         f"ans(s) :- mentions(s, '{term}')")
union = timed("union of the mentions", TERMS
              + "ans(s) :- task_term(n, m), mentions(s, m)")
got = timed("open world inhibition_study", TYPES + INHIBITION
            + "ans(s) :- inhibition_study(s)")
# the second time, without the preparation of the constraints; with
# PROFILE=N in the environment, under cProfile, its N top functions
if os.environ.get("PROFILE"):
    profile = cProfile.Profile()
    profile.enable()
timed("open world inhibition_study, again", TYPES + INHIBITION
      + "ans(s) :- inhibition_study(s)")
if os.environ.get("PROFILE"):
    profile.disable()
    pstats.Stats(profile).sort_stats("cumulative").print_stats(
        int(os.environ["PROFILE"]))
if got is not None and union is not None:
    print("open world = union:", got == union,
          "| more than 'stroop task' alone:",
          len(got - single["stroop task"]), flush=True)
