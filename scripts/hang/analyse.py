import pickle, sys, time, collections
from nl_core.datalog import expression_processing as ep
from nl_core.datalog.magic_sets import _strongly_connected_components
from nl_core.datalog.expressions import Implication, Conjunction
from nl_expr.expressions import Symbol, Constant
simple, seen_names = pickle.load(open(sys.argv[1], "rb"))
print(len(simple), "rules", collections.Counter(t for *_, t in simple))
heads = {h for h, *_ in simple}
dep = {h: set() for h in heads}
for h, b, f, t in simple: dep[h] |= set(b) & heads
comp = _strongly_connected_components(dep)
sizes = collections.Counter(collections.Counter(comp.values()).values())
print("heads", len(heads), "SCC sizes", sorted(sizes.items()))
print("self loops", sum(1 for h in heads if h in dep[h]))
undefined = {p for _, b, *_ in simple for p in b} - heads - seen_names
print("undefined body preds", len(undefined), list(undefined)[:5])
big = [c for c, n in collections.Counter(comp.values()).items() if n > 1]
for c in big[:3]:
    print("SCC", [h for h in heads if comp[h] == c][:10])
x = Symbol("x")
S = {}
def sym(n): return S.setdefault(n, Symbol(n))
rules = [Implication(sym(h)(x), Constant(True) if f else Conjunction(tuple(sym(p)(x) for p in b))) for h, b, f, t in simple]
class P:
    def extensional_database(self): return {sym(n): None for n in seen_names}
    def builtins(self): return {}
import nl_core.datalog.expressions as de
if len(sys.argv) > 2 and sys.argv[2] == "old":
    from nl_expr.logic import Union
    t = time.perf_counter(); strata, ok = ep.stratify(Union(tuple(rules)), P()); print("stratify", time.perf_counter() - t, len(strata), ok)

def rc(rules):
    heads = {r.consequent.functor for r in rules}
    depends_on = {head: set() for head in heads}
    for r in rules:
        depends_on[r.consequent.functor] |= ep._body_predicates(r) & heads
    component = _strongly_connected_components(depends_on)
    members = collections.defaultdict(set)
    for p, c in component.items(): members[c].add(p)
    for c in dict.fromkeys(component[r.consequent.functor] for r in rules):
        yield members[c]
CALLS = collections.Counter()
def rec(to_process, seen):
    CALLS['rec'] += 1
    t = time.perf_counter()
    for component in rc(to_process):
        rules = [r for r in to_process if r.consequent.functor in component]
        allowed = seen | component
        if all(ep.all_body_preds_in_set(r, allowed) for r in rules):
            rest = [r for r in to_process if r.consequent.functor not in component]
            CALLS['t'] += time.perf_counter() - t
            return rules, rest
    CALLS['t'] += time.perf_counter() - t
    return list(to_process), []
if len(sys.argv) > 2 and sys.argv[2] == "new":
    ep.stratify_obtain_recursive_stratum = rec
    from nl_expr.logic import Union
    t = time.perf_counter(); strata, ok = ep.stratify(Union(tuple(rules)), P()); print("stratify new", time.perf_counter() - t, len(strata), ok, dict(CALLS))
    print([len(s) for s in strata][:50])
