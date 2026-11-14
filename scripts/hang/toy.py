import sys, time
from nl_expr.expressions import Symbol
from nl_core.datalog import DatalogProgram
from nl_core.datalog.expression_processing import stratify
from nl_core.datalog.expressions import Implication, Conjunction
from nl_expr.expression_walker import ExpressionBasicEvaluator
from nl_expr.logic import Union
class Datalog(DatalogProgram, ExpressionBasicEvaluator):
    pass
n, m = int(sys.argv[1]), int(sys.argv[2])
x, y = Symbol('x'), Symbol('y')
E = Symbol('E')
Q = [Symbol(f'Q{j}') for j in range(m)]
P = [Symbol(f'P{i}') for i in range(n)]
rules = [Implication(Q[0](x), E(x, x))]
for j in range(m):
    rules.append(Implication(Q[j](x), Conjunction((E(x, y), Q[j](y)))))
    if j:
        rules.append(Implication(Q[j](x), Q[j - 1](x)))
rules.append(Implication(P[0](x), Conjunction((Q[-1](x), Symbol('U')(x)))))
for i in range(n):
    rules.append(Implication(P[i](x), P[(i + 1) % n](x)))
code = Union(tuple(rules))
d = Datalog(); d.walk(code); d.add_extensional_predicate_from_tuples(E, {(1, 1)})
t = time.perf_counter(); strata, ok = stratify(code, d); print(time.perf_counter() - t, len(strata), ok, [len(s) for s in strata][:5], len(strata[-1]))
