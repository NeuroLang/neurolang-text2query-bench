"""Profile the open-world query of doc/ontologies.rst (IV),
``ans(s) :- inhibition_study(s)`` with the rdf:type rule of the Stroop
studies, on the neurosynth engine: time of a warm-up query, then the query
under cProfile, top functions by cumulative and own time.

    PYTHONPATH=<NeuroLang packages> .venv-dsparity/bin/python \\
        scripts/hang/xrmoves/profile_inhibition.py [N]
"""
import cProfile
import pstats
import sys
import time
from pathlib import Path

from text2query_bench.engine import build_engine

STROOP = ("rdf:type(s, t) :- mentions(s, 'stroop task'), "
          "cogat_term(t, 'stroop task')\n")
INHIBITION = ("inhibition_study(s) :- exists(x, c, k; cogpo:has_contrast(s, x),"
              " cogat:measures(x, c), rdf:type(c, k), "
              "cogat_term(k, 'response inhibition'))\n")
nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
t = time.perf_counter()
with nl.scope:
    nl.execute_datalog_program(
        STROOP + "ans(s) :- exists(x; cogpo:has_contrast(s, x))")
print(f"warm-up {time.perf_counter() - t:.1f}s", flush=True)
profile = cProfile.Profile()
t = time.perf_counter()
profile.enable()
with nl.scope:
    rows = nl.execute_datalog_program(
        STROOP + INHIBITION + "ans(s) :- inhibition_study(s)")
profile.disable()
print(f"inhibition_study {time.perf_counter() - t:.1f}s {len(rows)} rows")
n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
pstats.Stats(profile).sort_stats("cumulative").print_stats(n)
pstats.Stats(profile).sort_stats("tottime").print_stats(n)
