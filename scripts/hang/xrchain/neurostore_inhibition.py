"""The open-world inhibition_study query on the neurostore engine, with an
instance rule for each inhibition task of the Cognitive Atlas whose name is
in the vocabulary: rows, time, and the cross-check with the union of the
mentions.  argv: timeout (s)."""
import signal
import sys
import time
from pathlib import Path

from neurolang_apps.utils.engine_registry import build_engine

TASKS = {  # the terms of scripts/ontology_example/neurostore_terms.py
    "CAO_00707": "color word stroop", "CAO_00810": "choice reaction time",
    "CAO_00827": "nogo task", "CAO_00864": "simon task",
    "CAO_00872": "stroop task",
}


def stop(*_):
    raise KeyboardInterrupt


signal.signal(signal.SIGALRM, stop)
t = time.perf_counter()
nl = build_engine(
    "neurostore", Path("/Users/bot/neurolang-text2query-bench/neurolang_data"),
    2.0,
)
print(f"build {time.perf_counter() - t:.1f}s", flush=True)
rules, expected = "", set()
for cao, name in TASKS.items():
    with nl.scope:
        rows = {r[0] for r in nl.execute_datalog_program(
            f"ans(s) :- mentions(s, '{name}')")}
    print(cao, name, len(rows), flush=True)
    if rows:
        rules += f"cogat:{cao}(s) :- mentions(s, '{name}')\n"
        expected |= rows
program = rules + (
    "inhibition_study(s) :- cogpo:has_contrast(s, x), "
    "cogat:measures(x, c), cogat:CAO_00487(c)\n"
    "ans(s) :- inhibition_study(s)")
for run in range(2):
    t = time.perf_counter()
    signal.alarm(int(sys.argv[1]))
    try:
        with nl.scope:
            got = {r[0] for r in nl.execute_datalog_program(program)}
        out = f"{len(got)} rows, equal to the mentions: {got == expected}"
    except KeyboardInterrupt:
        out = "stopped"
    finally:
        signal.alarm(0)
    print(f"run {run}: {time.perf_counter() - t:.1f}s {out}",
          len(expected), flush=True)
