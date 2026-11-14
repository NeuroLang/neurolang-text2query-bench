"""For the two-atom prefix query, the explored rewritings with an aux atom
and has_contrast, and why the aux atom is not rewritten eagerly."""
import collections
from pathlib import Path

from nl_core.datalog import ontologies_rewriter as orw
from text2query_bench.engine import build_engine

seen = []
orig = orw.OntologyRewriter._get_related_sigmas


def related(self, q0, c):
    r = orig(self, q0, c)
    if self.holds is not None:
        seen.append((self, q0, len(r)))
    return r


orw.OntologyRewriter._get_related_sigmas = related
nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
with nl.scope:
    nl.execute_datalog_program(
        "cogat:CAO_00872(s) :- mentions(s, 'stroop task')\n"
        "ans(s) :- cogpo:has_contrast(s, x), cogat:measures(x, c)")
why = collections.Counter()
for n, (self, q, k) in enumerate(seen):
    fs = getattr(q.antecedent, "formulas", (q.antecedent,))
    aux = [f for f in fs if getattr(f.functor, "name", "").startswith("fresh")]
    if len(fs) != 2 or not aux:
        continue
    a = aux[0]
    sig = self.union_of_constraints.get(a.functor, ())
    key = (len(sig), tuple(sorted(self._null_positions(a.functor))),
           tuple(bool(self._get_applicable(s, q)) for s in sig)[:3],
           tuple(type(x).__name__ for x in a.args), k)
    why[key] += 1
    if why[key] == 1 and k > 400:
        print(key, q, [str(s) for s in list(sig)[:2]])
print(why.most_common(10))
