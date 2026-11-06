"""
Peak memory of queries in the assistant's forked child (validation._in_child),
to find why a query exceeds the 4 GB per-query limit.

    python scripts/memory_probe.py QUERYFILE... [--engine neurosynth]

For each file: the parent's RSS, then the child's RSS sampled every 0.2 s
while the query runs (no limit), and the row count.
"""
import argparse
import os
import sys
import threading
import time
import faulthandler

from text2query_bench.engine import build_engine


def rss_mb(pid):
    out = os.popen(f"ps -o rss= -p {pid}").read().strip()
    return int(out) / 1024 if out else 0.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("queries", nargs="+")
    parser.add_argument("--engine", default="neurosynth")
    parser.add_argument("--data-dir", default="neurolang_data")
    parser.add_argument("--in-process", action="store_true")
    parser.add_argument("--show-ra", action="store_true",
                        help="print the RA plans of each query instead")
    parser.add_argument("--save", metavar="DIR",
                        help="save each result as DIR/<query file>.pkl")
    parser.add_argument("--stacks", action="store_true",
                        help="print the RSS every 0.2 s and the stacks every 2 s (stderr)")
    args = parser.parse_args()
    from neurolang_apps.utils.llm import validation
    nl = build_engine(args.engine, args.data_dir)
    print(f"parent rss {rss_mb(os.getpid()):.0f} MB", flush=True)
    for path in args.queries:
        query = open(path).read()
        if args.show_ra:
            with nl.scope:
                nl.execute_datalog_program(query, show_ra=True)
            continue
        peak = {"child": 0.0, "parent": 0.0}
        done = threading.Event()
        parent = os.getpid()

        def watch():
            while not done.is_set():
                for line in os.popen(f"ps -A -o pid=,ppid= | awk '$2=={parent}{{print $1}}'").read().split():
                    peak["child"] = max(peak["child"], rss_mb(int(line)))
                now = rss_mb(parent)
                if args.stacks:
                    print(f"--- {time.time() - start:.1f}s {now:.0f} MB",
                          flush=True)
                peak["parent"] = max(peak["parent"], now)
                time.sleep(0.2)

        start = time.time()
        if args.stacks:  # the stacks every 2 s, to match the RSS growth
            faulthandler.dump_traceback_later(2, repeat=True)
        thread = threading.Thread(target=watch, daemon=True)
        thread.start()
        if args.in_process:
            preview = validation._preview(nl, query, "datalog", 3, args.engine)
        else:
            preview = validation.run_preview(
                nl, query, "datalog", 3, args.engine, timeout=600)
        done.set()
        if args.save and preview.frame is not None:
            name = os.path.basename(path) + ".pkl"
            preview.frame.to_pickle(os.path.join(args.save, name))
        faulthandler.cancel_dump_traceback_later()
        thread.join()
        print(f"{path}: {time.time() - start:.1f}s child peak "
              f"{peak['child']:.0f} MB parent peak {peak['parent']:.0f} MB "
              f"rows {preview.rows}\n{preview.text[:300]}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
