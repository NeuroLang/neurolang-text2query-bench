"""
One row per nsv3e run (runs/nsv3e.md): mean Jaccard (exact), tool calls
per question, input/output tokens and $ per question (run_cost.py's
prices, the fallback's replies priced as Sonnet), fallback rate, invalid
answers, the misses (J < 1) by category, and the load average during the run.

    python scripts/nsv3e_table.py DATASET SPLIT LABEL=RUN ...   (SPLIT '-': all)
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from nsv2_overlap import jaccard  # noqa: E402
from run_cost import PRICES, PROVIDERS  # noqa: E402
from text2query_bench.dataset import load_dataset  # noqa: E402


def row(label, run, questions):
    results = {
        r["id"]: r for r in json.loads((run / "results.json").read_text())[
            "results"] if r["id"] in questions and r["language"] == "en"
    }
    answers = {a["id"]: a for a in json.loads(
        (run / "answers.json").read_text()) if a["language"] == "en"}
    js = {i: jaccard(r) for i, r in results.items()}
    key = next((k for k in PRICES if k in label.lower()), "deepseek")
    tin = tout = cost = 0
    for i in results:
        path = run / "trace" / f"{i}-en.jsonl"
        for e in map(json.loads, open(path)) if path.exists() else ():
            if e["event"] == "reply" and "usage" in e:
                fi, fo = PRICES[PROVIDERS[e["provider"]]] if (
                    "provider" in e) else PRICES[key]
                tin += e["usage"]["input"]
                tout += e["usage"]["output"]
                cost += e["usage"]["input"] * fi + e["usage"]["output"] * fo
    steps = [len([s for s in answers[i].get("steps", [])
                  if s["action"] != "fallback"]) for i in results]
    fallbacks = sum(any(s["action"] == "fallback"
                        for s in answers[i].get("steps", [])) for i in results)
    misses = defaultdict(list)
    for i, j in sorted(js.items()):
        if j < 1:
            misses[questions[i].tags[0]].append(f"{i}({j:.2f})")
    loads = [float(line.split()[2]) for line in open(run / "load.log")] if (
        run / "load.log").exists() else [0]
    n = len(results)
    return (
        f"| {label} | {n} | {sum(js.values()) / n:.3f} ({sum(j == 1 for j in js.values())}) "
        f"| {sum(steps) / n:.1f} | {tin / n / 1000:.1f}k / {tout / n / 1000:.2f}k "
        f"| {cost / 1e6 / n:.4f} | {fallbacks}/{n} "
        f"| {sum(not r['valid'] for r in results.values())} "
        f"| {max(loads):.0f} | "
        + "; ".join(f"{c}: {' '.join(v)}" for c, v in sorted(misses.items()))
        + " |"
    )


def main():
    dataset = load_dataset(sys.argv[1])
    split = sys.argv[2]
    questions = {q.id: q for q in dataset.questions
                 if split == "-" or q.split == split}
    print("| run | n | mean J (exact) | steps | tokens in/out per q | $/q "
          "| fallback | invalid | max load | misses by category |")
    print("|---|---:|---|---:|---|---:|---:|---:|---:|---|")
    for spec in sys.argv[3:]:
        label, run = spec.split("=")
        print(row(label, Path(run), questions))


if __name__ == "__main__":
    main()
