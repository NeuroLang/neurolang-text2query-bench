"""Whether the Cognitive Atlas constraints are recursive: strongly connected
components of the predicate graph (antecedent predicate -> consequent
predicate), and how many hold a constraint with a several-atom antecedent
(``C(x) & p(x, y) -> D(y)``), whose recursion makes the UCQ rewriting of
Xrewrite infinite."""
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from nl_core.datalog.expression_processing import extract_logic_atoms
from text2query_bench.engine import build_engine

nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
cons = [c for v in nl.program_ir.get_constraints().values() for c in v]
index = {}
edges = []
for c in cons:
    head = index.setdefault(c.consequent.functor, len(index))
    for a in extract_logic_atoms(c.antecedent):
        edges.append((index.setdefault(a.functor, len(index)), head, c))
n = len(index)
rows, cols = zip(*((a, b) for a, b, _ in edges))
graph = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
_, comp = connected_components(graph, connection="strong")
sizes = np.bincount(comp)
print("predicates", n, "non-trivial SCCs", int((sizes > 1).sum()),
      "largest", int(sizes.max()))
recursive_nonlinear = {
    id(c) for a, b, c in edges
    if comp[a] == comp[b] and sizes[comp[a]] > 1
    and len(extract_logic_atoms(c.antecedent)) > 1
}
print("several-atom constraints inside an SCC", len(recursive_nonlinear))
