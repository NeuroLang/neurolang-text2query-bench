"""Build time of the neurosynth engine, then the Cognitive Atlas queries of
NeuroLang #1228/#1238 (second, warm run of each) and those over the classes
of cogat's six domain/range axioms, without and with one instance of each
class in ``sys.argv[2:]``; ``sys.argv[1]`` is the timeout (s). Run it with
PYTHONPATH on the NeuroLang worktree under test."""
import signal
import sys
import time
from pathlib import Path

import neurolang
from text2query_bench.engine import build_engine

print("neurolang from", neurolang.__file__, flush=True)
COGAT = "http://www.cognitiveatlas.org/ontology/cogat.owl#"
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
UNARY = ["MentalConcept", "COGPO_00049"]
BINARY = ["measured_by", "measures", "descended_from"]


def stop(*_):
    raise KeyboardInterrupt


signal.signal(signal.SIGALRM, stop)
t = time.perf_counter()
nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
print(f"build {time.perf_counter() - t:.1f}s", flush=True)
names = {
    suffix: name for name in map(str, (
        s.name for s in nl.program_ir.symbol_table
    )) for suffix in UNARY + BINARY
    if name.endswith(("#" + suffix, ":" + suffix))
}
print("predicates", names, flush=True)


def timed(label, text, query):
    for _ in range(2):
        t = time.perf_counter()
        signal.alarm(int(sys.argv[1]))
        try:
            with nl.scope:
                r = set(query())
            out = f"{len(r)} rows {sorted(r)[:3]}"
        except KeyboardInterrupt:
            out = "stopped"
            break
        except Exception as e:
            out = f"{type(e).__name__}: {e}"[:200]
            break
        finally:
            signal.alarm(0)
    print(label, f"{time.perf_counter() - t:6.1f}s", text, "->", out,
          flush=True)


def run(label):
    for q in QUERIES:
        timed(label, q, lambda: nl.execute_datalog_program(q))
    for suffix in UNARY + BINARY:
        if suffix not in names:
            print(label, "no predicate", suffix, flush=True)
            continue
        name = names[suffix]
        args = ("x",) if suffix in UNARY else ("x", "y")

        def query():
            with nl.environment as e:
                symbols = tuple(getattr(e, a) for a in args)
                return nl.query(symbols[:1], nl.symbols[name](*symbols))
        timed(label, f"{name}({', '.join(args)})", query)


run("none")
for cls in sys.argv[2:]:
    nl.add_tuple_set([("individual",)], name=COGAT + cls)
    run(cls)
