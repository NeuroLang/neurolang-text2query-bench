import sys, threading, time, traceback, os, collections
from pathlib import Path
from text2query_bench.engine import build_engine
nl = build_engine("neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data"))
main = threading.main_thread().ident
def sampler():
    counts = collections.Counter()
    for i in range(int(sys.argv[2])):
        time.sleep(1)
        st = traceback.extract_stack(sys._current_frames()[main])
        key = tuple(f"{Path(f.filename).name}:{f.lineno}:{f.name}" for f in st if "pattern_matching" not in f.filename and "expression_walker" not in f.filename and "expressions.py" not in f.filename)[-12:]
        counts[key] += 1
    with open("/tmp/where2.txt", "w") as out:
        for k, c in counts.most_common(4):
            out.write(f"--- {c}\n" + "\n".join(k) + "\n")
    os._exit(0)
threading.Thread(target=sampler, daemon=True).start()
nl.execute_datalog_program(sys.argv[1])
open("/tmp/where2.txt", "a").write("finished\n")
