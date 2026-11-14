"""cProfile of one Cognitive Atlas query on the neurosynth engine with one
instance of CAO_01600 (second run): the top functions by cumulative time."""
import cProfile
import pstats
import sys
from pathlib import Path

from text2query_bench.engine import build_engine

COGAT = "http://www.cognitiveatlas.org/ontology/cogat.owl#"
QUERY = sys.argv[1] if len(sys.argv) > 1 else "ans(x) :- ro:has_part(x, y)"
nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
nl.add_tuple_set([("individual",)], name=COGAT + "CAO_01600")
with nl.scope:
    nl.execute_datalog_program(QUERY)
profile = cProfile.Profile()
profile.enable()
with nl.scope:
    nl.execute_datalog_program(QUERY)
profile.disable()
pstats.Stats(profile).sort_stats("cumulative").print_stats(35)
