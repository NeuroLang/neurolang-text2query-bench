"""
Write a ``split`` (dev or test) for each question of a dataset, balanced
across the tags: each question goes, in order, to the split where its
tags are the rarest so far (ties: the smaller split, then dev). The
YAML is edited in place, a ``split:`` line after each ``tags:`` line.

    python scripts/assign_splits.py datasets/neurosynth-v2.yaml
"""

import re
import sys
from collections import Counter
from pathlib import Path

from text2query_bench.dataset import load_dataset


def assign(questions):
    counts = {"dev": Counter(), "test": Counter()}
    sizes = Counter()
    splits = {}
    for q in questions:
        def cost(split):
            return (sum(counts[split][t] for t in q.tags), sizes[split])
        split = min(("dev", "test"), key=cost)
        splits[q.id] = split
        counts[split].update(q.tags)
        sizes[split] += 1
    return splits, counts


def main(path):
    path = Path(path)
    splits, counts = assign(load_dataset(path).questions)
    text = re.sub(r"\n    split: \w+", "", path.read_text())
    out, current = [], None
    for line in text.splitlines():
        match = re.match(r"  - id: (\S+)", line)
        if match:
            current = match.group(1)
        out.append(line)
        if current and line.startswith("    tags:"):
            out.append(f"    split: {splits[current]}")
    path.write_text("\n".join(out) + "\n")
    tags = sorted(set(counts["dev"]) | set(counts["test"]))
    for tag in tags:
        print(f"{tag:<14} dev {counts['dev'][tag]:>2}  test {counts['test'][tag]:>2}")
    print("questions", Counter(splits.values()))


if __name__ == "__main__":
    main(sys.argv[1])
