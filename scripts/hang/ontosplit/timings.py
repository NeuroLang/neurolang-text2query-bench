"""Time the Cognitive Atlas queries of NeuroLang #1228 on the neurosynth
engine (second, warm run of each), then again after giving one instance
to each class in ``sys.argv[2:]``; ``sys.argv[1]`` is the timeout (s)."""
import signal
import sys
import time
from pathlib import Path

from text2query_bench.engine import build_engine

QUERIES = [
    "ans(x) :- ro:has_part(x, y)",
    "ans(x, y) :- ro:part_of(x, y)",
    "ans(x) :- ro:part_of(x, y)",
    "ans(t) :- cogat_term(c, 'language comprehension'), ro:has_part(c, x),"
    " cogat_term(x, t)",
    "ans(n) :- AGGREGATE[](skos:Concept(c) @ count(c)) = n",
    "ans(c, d) :- rdfs:subClassOf(c, r), owl:onProperty(r, "
    "<http://www.obofoundry.org/ro/ro.owl#has_part>), "
    "owl:someValuesFrom(r, d)",
    "ans(count(c)) :- rdfs:label(c, l)",
]
COGAT = "http://www.cognitiveatlas.org/ontology/cogat.owl#"


def stop(*_):
    raise KeyboardInterrupt


signal.signal(signal.SIGALRM, stop)
nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)


def run(label):
    for q in QUERIES:
        for _ in range(2):
            t = time.perf_counter()
            signal.alarm(int(sys.argv[1]))
            try:
                with nl.scope:
                    r = set(nl.execute_datalog_program(q))
                out = f"{len(r)} rows {sorted(r)[:3]}"
            except KeyboardInterrupt:
                out = "stopped"
                break
            finally:
                signal.alarm(0)
        print(label, f"{time.perf_counter() - t:6.1f}s", q, "->", out,
              flush=True)


run("none")
for cls in sys.argv[2:]:
    nl.add_tuple_set([("individual",)], name=COGAT + cls)
    run(cls)
