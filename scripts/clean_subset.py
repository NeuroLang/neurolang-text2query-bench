"""
Score runs on the questions none of whose LLM requests failed (e.g. the
OpenRouter key limit hit mid-run), against earlier runs on the same
questions: mean Jaccard (exact) and the questions that changed.

    python scripts/clean_subset.py DATASET SPLIT NEW=OLD ...
    (SPLIT '-' for all the questions; English answers)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from nsv2_overlap import jaccard  # noqa: E402

from text2query_bench.dataset import load_dataset  # noqa: E402


def failed(run):
    return {
        f.name[:-len("-en.jsonl")] for f in Path(run, "trace").glob("*-en.jsonl")
        if any('"event": "reply"' in line and '"error"' in line
               and "HTTP 4" in line for line in open(f))
    }


def scores(run):
    results = json.loads(Path(run, "results.json").read_text())["results"]
    return {r["id"]: jaccard(r) for r in results if r["language"] == "en"}


def main():
    ds = load_dataset(sys.argv[1])
    split = sys.argv[2]
    ids = {q.id for q in ds.questions if split == "-" or q.split == split}
    for spec in sys.argv[3:]:
        new, old = spec.split("=")
        a, b = scores(new), scores(old)
        clean = sorted((set(a) & set(b) & ids) - failed(new))
        if not clean:
            print(f"{new}: no clean question")
            continue
        ma = sum(a[i] for i in clean) / len(clean)
        mb = sum(b[i] for i in clean) / len(clean)
        ea = sum(a[i] == 1 for i in clean)
        eb = sum(b[i] == 1 for i in clean)
        print(f"{new}: {len(clean)} clean of {len(ids & set(a))}; "
              f"{ma:.3f} ({ea}) vs {old} {mb:.3f} ({eb})")
        for i in clean:
            if abs(a[i] - b[i]) > 1e-9:
                print(f"    {i}: {b[i]:.2f} -> {a[i]:.2f}")


if __name__ == "__main__":
    main()
