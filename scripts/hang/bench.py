import pickle, time, sys, collections
from nl_core.datalog import expression_processing as ep
from nl_core.datalog.expressions import Implication, Conjunction
from nl_expr.expressions import Symbol, Constant
from nl_expr.logic import Union
x = Symbol("x"); S = {}
def sym(n): return S.setdefault(n, Symbol(n))
def load(f):
    simple, seen_names = pickle.load(open(f, 'rb'))
    rules = [Implication(sym(h)(x), Constant(True) if fl else Conjunction(tuple(sym(p)(x) for p in b))) for h, b, fl, t in simple]
    class P2:
        def extensional_database(self): return {sym(n): None for n in seen_names}
        def builtins(self): return {}
    return Union(tuple(rules)), P2()
if __name__ == "__main__":
    for f in sys.argv[1:]:
        u, p = load(f)
        t = time.perf_counter(); s, ok = ep.stratify(u, p); print(f, "stratify", round(time.perf_counter()-t, 1), "s", len(s), ok, flush=True)
