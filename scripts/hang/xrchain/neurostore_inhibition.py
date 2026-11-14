"""The open-world inhibition_study query on the neurostore engine, with an
instance rule for each inhibition task of the Cognitive Atlas whose name is
in the vocabulary (CAO ids checked with scripts/ontology_example/
inhibition_tasks.py, terms with neurostore_terms.py), against each single
mentions query and their union: rows and time of each, one at a time.
argv: timeout (s), applied to the build and to each query."""
import signal
import subprocess
import sys
import time
from pathlib import Path

import neurolang
from neurolang_apps.utils.engine_registry import build_engine

TASKS = {  # the terms of scripts/ontology_example/neurostore_terms.py
    "CAO_00872": "stroop task", "CAO_00707": "color word stroop",
    "CAO_00864": "simon task", "CAO_00827": "nogo task",
    "CAO_00810": "choice reaction time",
}
INHIBITION = ("inhibition_study(s) :- cogpo:has_contrast(s, x), "
              "cogat:measures(x, c), cogat:CAO_00487(c)\n")


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
            rows = {r[0] for r in nl.execute_datalog_program(program)}
        out = f"{len(rows)} rows"
    except KeyboardInterrupt:
        rows, out = None, "stopped"
    finally:
        signal.alarm(0)
    print(f"{name}: {time.perf_counter() - t:.1f}s {out}", flush=True)
    return rows


timed("study_count", "ans(count(s)) :- study(s)")
single = {}
for cao, term in TASKS.items():
    single[cao] = timed(f"mentions '{term}'",
                        f"ans(s) :- mentions(s, '{term}')")
union = timed("union of the mentions", "".join(
    f"task_study(s) :- mentions(s, '{term}')\n" for term in TASKS.values())
    + "ans(s) :- task_study(s)")
rules = "".join(f"cogat:{cao}(s) :- mentions(s, '{term}')\n"
                for cao, term in TASKS.items())
got = timed("open world inhibition_study", rules + INHIBITION
            + "ans(s) :- inhibition_study(s)")
if got is not None and union is not None:
    print("open world = union:", got == union,
          "| more than 'stroop task' alone:",
          len(got - single["CAO_00872"]), flush=True)
