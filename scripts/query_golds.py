"""
Send the gold queries of a dataset to scripts/query_server.py and print
their row counts and first rows.

    python scripts/query_golds.py DATASET DIR [ID ...]
"""

import sys
import time
from pathlib import Path

from text2query_bench.dataset import load_dataset


def main(dataset, directory, *ids):
    directory = Path(directory)
    for q in load_dataset(dataset).questions:
        if ids and q.id not in ids:
            continue
        out = directory / f"{q.id}.out"
        out.unlink(missing_ok=True)
        tmp = directory / f"{q.id}.tmp"
        tmp.write_text(q.gold_query()[1], encoding="utf-8")
        tmp.rename(directory / f"{q.id}.dl")
        while not out.exists():
            time.sleep(0.5)
        lines = out.read_text(encoding="utf-8").splitlines()
        print(f"## {q.id} {q.text['en']}")
        print("\n".join(lines[:7]))


if __name__ == "__main__":
    main(*sys.argv[1:])
