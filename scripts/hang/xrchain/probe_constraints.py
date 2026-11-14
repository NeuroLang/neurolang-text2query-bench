"""The constraints of the Cognitive Atlas that can hold with the Stroop
instance rule, and those deriving has_contrast / measures."""
import collections
from pathlib import Path

from nl_core.datalog import ontologies_rewriter as orw
from text2query_bench.engine import build_engine

nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
captured = {}
orig = orw.OntologyRewriter.__init__


def init(self, query, constraints, chased=False, holds=None):
    if holds is not None:
        captured["c"], captured["h"] = constraints, holds
    orig(self, query, constraints, chased, holds)


orw.OntologyRewriter.__init__ = init
with nl.scope:
    nl.execute_datalog_program(
        "cogat:CAO_00872(s) :- mentions(s, 'stroop task')\n"
        "ans(s) :- cogpo:has_contrast(s, x)")
c, h = captured["c"], captured["h"]
all_c = nl.program_ir.get_constraints()
print("all constraints", sum(map(len, all_c.values())),
      "can hold", sum(map(len, c.values())), "holds", len(h))
print("holds sample", sorted(str(s.name)[-30:] for s in h)[:40])
for p in ("has_contrast", "measures", "measured_by"):
    for k, sig in c.items():
        if k.endswith(p):
            kinds = collections.Counter(
                (bool(orw._existential_variables(s)),
                 tuple(sorted(a.functor.name.split("#")[-1][:12]
                              if not a.functor.name.startswith("fresh")
                              else "aux"
                              for a in orw.extract_logic_atoms(s.antecedent))))
                for s in sig)
            print(k, len(sig), kinds.most_common(6))
            print("  e.g.", [str(s) for s in list(sig)[:3] if
                             not str(s.antecedent.functor.name).startswith(
                                 "fresh")][:3])

# how the holding predicates grow from the one instance
heads = {sig.consequent.functor for sigs in c.values() for sig in sigs}
print("predicates that can hold", len(heads))
r = orw.OntologyRewriter(None, c, chased=True, holds=h)
for p, i in [("has_contrast", 1), ("has_contrast", 0), ("measures", 0),
             ("measures", 1)]:
    f = next(sig.consequent.functor for k, sigs in c.items()
             if k.endswith(p) for sig in sigs)
    b = r._backward(f, i)
    named = {q for q, _ in b if not q.name.startswith("fresh")}
    print(p, i, "backward", len(b), "named predicates", len(named),
          sorted(q.name.split("#")[-1] for q in named)[:12])
