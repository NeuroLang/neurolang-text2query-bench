"""
Run Datalog queries on a NeuroLang engine built once, for writing gold
queries by hand.

    python scripts/query_server.py DIR [--engine neurosynth] [--timeout 120]

Every ``DIR/NAME.dl`` file put in the directory is run and removed; its
row count, columns and first rows go to ``DIR/NAME.out``. Stop with
Ctrl-C.
"""

import argparse
import sys
import time
from pathlib import Path

from text2query_bench.engine import build_engine, execute


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory")
    parser.add_argument("--engine", default="neurosynth")
    parser.add_argument("--data-dir", default="neurolang_data")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--rows", type=int, default=25)
    args = parser.parse_args()
    directory = Path(args.directory)
    directory.mkdir(parents=True, exist_ok=True)
    nl = build_engine(args.engine, args.data_dir)
    print("ready", flush=True)
    while True:
        for path in sorted(directory.glob("*.dl")):
            query = path.read_text(encoding="utf-8")
            path.unlink()
            result = execute(nl, query, "datalog", args.timeout)
            lines = [f"seconds {result.seconds:.1f}"]
            if result.error:
                lines.append(f"ERROR {result.error}")
            else:
                rows = sorted(result.rows, key=str)
                lines.append(f"rows {len(rows)} columns {result.columns}")
                lines += [repr(tuple(r)) for r in rows[: args.rows]]
            path.with_suffix(".out").write_text(
                "\n".join(lines) + "\n", encoding="utf-8"
            )
            print(path.stem, lines[1][:80], flush=True)
        time.sleep(0.5)


if __name__ == "__main__":
    sys.exit(main())
