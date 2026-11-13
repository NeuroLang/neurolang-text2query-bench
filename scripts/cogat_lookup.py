"""
What the assistant's search_values over cogat_term returns for topics,
and whether each topic is a Cognitive Atlas label with a definition: the
"found" of the Cognitive-Atlas-first rule (runs/nsv3d.md).

    python scripts/cogat_lookup.py TOPIC ...
"""

import sys

from neurolang_apps.utils.llm.context import EngineContext
from text2query_bench.engine import build_engine, execute


def main(topics):
    nl = build_engine("neurosynth", "neurolang_data")
    context = EngineContext(nl, "neurosynth")
    for topic in topics:
        rows = execute(
            nl, f"ans(d) :- cogat_definition('{topic}', d)", "datalog"
        )
        print(f"=== {topic!r}: label with definition: {bool(rows.rows)}")
        print(context.search_values(topic, "cogat_term"))


if __name__ == "__main__":
    main(sys.argv[1:])
