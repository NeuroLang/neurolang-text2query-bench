"""
Score the answers of several runs again, building the engine once (as
``t2q-bench evaluate`` does for one run), e.g. after a gold query
changed.

    python scripts/reevaluate.py datasets/neurosynth-v2.yaml runs/nsv2-*
"""

import argparse
import json
from pathlib import Path

from text2query_bench.cli import _engine, _evaluate_and_write
from text2query_bench.dataset import load_dataset


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset")
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--data-dir", default="neurolang_data")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()
    dataset = load_dataset(args.dataset)
    nl = _engine(args, dataset)
    for run in args.runs:
        answers = json.loads((run / "answers.json").read_text())
        print(f"== {run}")
        _evaluate_and_write(args, nl, dataset, answers, run)


if __name__ == "__main__":
    main()
