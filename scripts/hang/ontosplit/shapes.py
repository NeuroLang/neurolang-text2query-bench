"""Count the Cognitive Atlas constraints by shape: existential (a head
variable not in the body) or full, and the full ones by body/head arity."""
from collections import Counter
from pathlib import Path

from nl_core.datalog.expression_processing import extract_logic_atoms
from text2query_bench.engine import build_engine

nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
shapes = Counter()
for sigmas in nl.program_ir.get_constraints().values():
    for s in sigmas:
        body = list(extract_logic_atoms(s.antecedent))
        bv = set().union(*(a._symbols for a in body))
        hv = set(a for a in s.consequent.args)
        kind = "exist" if hv - bv else "full"
        shapes[(kind, tuple(len(a.args) for a in body), len(s.consequent.args),
                bool(set(a for a in body[0].args) - hv) if len(body) == 1 else "join")] += 1
for k, v in sorted(shapes.items(), key=str):
    print(k, v)
