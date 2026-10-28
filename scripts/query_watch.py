"""
Build an engine once and run the Datalog queries dropped in a directory.

Writing gold queries by hand needs many trial runs, and the neurosynth
engine takes minutes to build: this keeps it built. Each ``*.dl`` file
put in *directory* is run (with the bench's time limit) and its rows,
or its error, written next to it as ``*.out``.

    python scripts/query_watch.py --data-dir neurolang_data /tmp/q
    echo "ans(t) :- term(t)" > /tmp/q/terms.dl; cat /tmp/q/terms.out
"""

import argparse
import time
from pathlib import Path

from text2query_bench.engine import build_engine, execute


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--engine", default="neurosynth")
    parser.add_argument("--data-dir", default="neurolang_data")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--rows", type=int, default=2000)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    nl = build_engine(args.engine, args.data_dir)
    print(f"built in {time.perf_counter() - start:.0f} s", flush=True)
    while True:
        for path in sorted(args.directory.glob("*.dl")):
            query = path.read_text()
            path.unlink()
            result = execute(nl, query, "datalog", args.timeout)
            lines = [f"seconds {result.seconds:.1f}"]
            if result.error:
                lines.append(f"ERROR {result.error}")
            else:
                lines.append(f"{len(result.rows)} rows, columns {result.columns}")
                lines += [repr(r) for r in result.rows[: args.rows]]
            path.with_suffix(".out").write_text("\n".join(lines) + "\n")
            print(path.name, lines[:2], flush=True)
        time.sleep(0.5)


if __name__ == "__main__":
    main()
