"""Print the ontology constraints of the neurosynth engine whose head is
argv[1] (default ro:has_part), and those whose body has a fresh predicate
(anonymous OWL restriction) together with a count by shape."""
import collections
import sys
from pathlib import Path

from text2query_bench.engine import build_engine

nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
cons = nl.program_ir.get_constraints()
pred = sys.argv[1] if len(sys.argv) > 1 else "ro:has_part"
for k, v in cons.items():
    if str(k) == pred or str(k).endswith(pred):
        for c in v:
            print("HEAD", c)
shapes = collections.Counter()
examples = {}
for k, v in cons.items():
    for c in v:
        ant = getattr(c.antecedent, "formulas", (c.antecedent,))
        con = getattr(c.consequent, "formulas", (c.consequent,))
        shape = (
            tuple(("F" if a.functor.name.startswith("fresh") else "N",
                   len(a.args)) for a in ant),
            tuple(("F" if a.functor.name.startswith("fresh") else "N",
                   len(a.args)) for a in con),
            str(k).startswith("fresh"),
        )
        shapes[shape] += 1
        examples.setdefault(shape, c)
for s, n in shapes.most_common():
    print(n, s, "\n   ", examples[s])
