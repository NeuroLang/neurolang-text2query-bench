import random, re, sys
from nl_core.datalog import expression_processing as ep
from nl_core.datalog.expressions import Implication, Conjunction
from nl_expr.expressions import Symbol, Constant
from nl_expr.logic import Union, Negation
import importlib.util
spec = importlib.util.spec_from_file_location("nl_core.datalog._ep_old", __import__("os").path.join(__import__("os").path.dirname(__file__), "expression_processing_old.py"))
old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
x = Symbol("x")
class P:
    def __init__(s, edb): s.edb = edb
    def extensional_database(s): return {e: None for e in s.edb}
    def builtins(s): return {}
for seed in range(int(sys.argv[1])):
    rng = random.Random(seed)
    n = rng.randint(1, 12)
    preds = [Symbol(f"p{i}") for i in range(n)]
    edb = [Symbol(f"e{i}") for i in range(3)]
    undefined = [Symbol(f"u{i}") for i in range(rng.choice([0, 0, 1, 2]))]
    rules = []
    for _ in range(rng.randint(1, 20)):
        h = rng.choice(preds)
        if rng.random() < 0.1:
            rules.append(Implication(h(x), Constant(True))); continue
        body = []
        for _ in range(rng.randint(1, 3)):
            a = rng.choice(preds + edb + undefined)(x)
            body.append(Negation(a) if rng.random() < 0.1 else a)
        rules.append(Implication(h(x), Conjunction(tuple(body))))
    code = Union(tuple(rules))
    a = ep.stratify(code, P(edb))
    b = old.stratify(code, P(edb))
    assert a == b, (seed, a, b)
print("identical on", sys.argv[1], "programs")
