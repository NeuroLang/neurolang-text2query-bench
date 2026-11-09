"""
Compare two gold caches (DATASET.gold.json) of the same questions: the
questions whose rows changed, with the row counts and the Jaccard of the
two row sets (floats rounded to 6 digits).

    python scripts/gold_diff.py OLD.gold.json NEW.gold.json
"""
import json
import sys


def rows(entry):
    return {
        tuple(round(v, 6) if isinstance(v, float) else v for v in row)
        for row in entry["rows"]
    }


def main():
    old, new = (json.load(open(p)) for p in sys.argv[1:3])
    changed = 0
    for qid in new:
        if qid not in old:
            print(f"new  {qid}")
            continue
        a, b = rows(old[qid]), rows(new[qid])
        if a != b or old[qid].get("query") != new[qid].get("query"):
            changed += 1
            jac = len(a & b) / len(a | b) if a | b else 1.0
            print(f"diff {qid}: {len(a)} -> {len(b)} rows, Jaccard {jac:.3f}"
                  + ("" if old[qid].get("query") == new[qid].get("query")
                     else " (query changed)"))
    print(f"{changed} of {len(new)} changed")


if __name__ == "__main__":
    main()
