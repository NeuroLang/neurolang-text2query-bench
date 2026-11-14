import sys, faulthandler
from pathlib import Path
from text2query_bench.engine import build_engine
nl = build_engine("neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data"))
faulthandler.dump_traceback_later(float(sys.argv[2]), exit=True, file=open("/tmp/where.txt", "w"))
nl.execute_datalog_program(sys.argv[1])
