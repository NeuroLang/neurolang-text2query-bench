"""The forward closure of constraints_that_can_hold from the Stroop
instance, layer by layer: how many predicates each layer adds, and the
constraints that first fan out (the predicates with most heads)."""
import collections
from pathlib import Path

from nl_core.datalog import ontologies_rewriter as orw
from text2query_bench.engine import build_engine

nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
c = nl.program_ir.get_constraints()


def short(f):
    n = f.name
    return "aux" if n.startswith("fresh") else n.split("#")[-1][-24:]


holding = {next(s.consequent.functor for k, ss in c.items()
                if k.endswith("CAO_00872") for s in ss)}
holding = {f for f in holding}
layer = 0
while True:
    new = collections.defaultdict(set)
    for sigmas in c.values():
        for s in sigmas:
            body = [a.functor for a in orw.extract_logic_atoms(s.antecedent)]
            if all(b in holding for b in body) and \
                    s.consequent.functor not in holding:
                new[s.consequent.functor].add(tuple(map(short, body)))
    if not new:
        break
    layer += 1
    print("layer", layer, "adds", len(new), collections.Counter(
        short(h) == "aux" for h in new))
    src = collections.Counter(b for bs in new.values() for b in bs)
    print("   from", src.most_common(6)); print("   new", sorted(map(short, new))[:12] if layer < 7 else "")
    holding |= set(new)
