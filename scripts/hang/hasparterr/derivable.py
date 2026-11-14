"""Count, on the neurosynth engine, the ontology constraints whose
antecedent can hold: forward fixpoint from the predicates with facts or
rules, through the constraints. Prints how many constraints survive."""
from pathlib import Path

from nl_core.datalog.expression_processing import extract_logic_predicates
from text2query_bench.engine import build_engine

nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
p = nl.program_ir
cons = [c for v in p.get_constraints().values() for c in v]
from nl_core.datalog.constraints_representation import (
    RightImplication, iter_implications)
known = {k for k, v in p.extensional_database().items()
         if len(getattr(v.value, "__len__", lambda: 1) and v.value)}
known |= {k for k, v in p.intensional_database().items() if any(
    not isinstance(r, RightImplication) for r in iter_implications(v))}
known |= set(p.builtins())
print("EDB+IDB predicates", len(known))
derivable = set(known)
changed = True
while changed:
    changed = False
    for c in cons:
        if all(a.functor in derivable
               for a in extract_logic_predicates(c.antecedent)):
            for h in extract_logic_predicates(c.consequent):
                if h.functor not in derivable:
                    derivable.add(h.functor)
                    changed = True
alive = [c for c in cons if all(
    a.functor in derivable for a in extract_logic_predicates(c.antecedent))]
print("constraints", len(cons), "with a derivable antecedent", len(alive))
heads = {a.functor for c in cons for a in extract_logic_predicates(c.antecedent)}
print("antecedent predicates", len(heads), "with facts/rules",
      len(heads & known), sorted(str(h) for h in heads & known)[:20])
for c in alive[:20]:
    print("  ", c)
