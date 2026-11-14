"""Run the new bank examples on an engine and print their row counts and top rows."""
import sys
from pathlib import Path
from neurolang_apps.utils import engine_registry as er
from neurolang_apps.utils.llm.examples import load_examples
nl = er.build_engine(sys.argv[2], Path(sys.argv[1]), None)
for ex in load_examples(sys.argv[2]):
    if "_covered" not in ex.queries.get("datalog", ""):
        continue
    with nl.scope:
        res = nl.execute_datalog_program(ex.queries["datalog"])
        frame = res.as_pandas_dataframe()
    top = frame.sort_values(frame.columns[-1], ascending=False).head(3)
    print(sys.argv[2], len(frame), "rows |", ex.question, "|", top.to_dict("records"))
