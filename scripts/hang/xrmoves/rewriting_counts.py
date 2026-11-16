"""The number of rewritings XRewrite returns for each rule it rewrites, for
the queries of doc/ontologies.rst (III) on ro:has_part and ro:part_of, on
the neurosynth engine: do the counts the docs give move?

    PYTHONPATH=<NeuroLang packages> .venv-dsparity/bin/python \\
        scripts/hang/xrmoves/rewriting_counts.py
"""
from pathlib import Path

from nl_core.datalog import ontologies_rewriter as orw
from text2query_bench.engine import build_engine

counts = []
xrewrite = orw.OntologyRewriter.Xrewrite


def counted(self):
    result = xrewrite(self)
    counts.append(len(result))
    return result


orw.OntologyRewriter.Xrewrite = counted
nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
for query in ["ans(x) :- ro:has_part(x, y)", "ans(x) :- ro:part_of(x, y)"]:
    counts.clear()
    with nl.scope:
        rows = nl.execute_datalog_program(query)
    print(query, len(rows), "rows; rewritings per rule:", sorted(counts),
          flush=True)
