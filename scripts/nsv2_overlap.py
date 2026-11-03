"""
Per-question overlap of the predicted rows with the gold rows, per model,
and its change against an earlier run of the same model.

The overlap is the Jaccard index |pred ∩ gold| / |pred ∪ gold| of the
bench's normalised rows, under the column alignment it scores (the one
with the best F1). From the precision p and recall r of results.json,
J = p·r / (p + r − p·r) = F1 / (2 − F1): ``rows`` there is the raw row
count, before the projection on the gold columns and its duplicates, so
p·rows is not |∩| when the projection merges rows.

    python scripts/nsv2_overlap.py datasets/neurosynth-v2.yaml --split test \\
        Sonnet=runs/nsv2-test-master-sonnet,runs/nsv2-test-int-sonnet ...

Each model is LABEL=RUN[,EARLIER_RUN]. Verifier steps (NeuroLang #973)
are not counted as steps; a rejection is a verify step answering "no".
"""

import argparse
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).parent))
from failure_taxonomy import kind, load_run, rejected, tool_steps  # noqa: E402

from text2query_bench.dataset import load_dataset  # noqa: E402


def jaccard(result: dict) -> float:
    p, r = result["precision"], result["recall"]
    if result["f1"] == 1.0:
        return 1.0
    return 0.0 if p == 0 or r == 0 else p * r / (p + r - p * r)


def load(directory, questions, split, lang, max_steps):
    out = {}
    for answer, result in load_run(Path(directory)):
        q = questions[result["id"]]
        if q.split != split or result["language"] != lang:
            continue
        steps = answer.get("steps", [])
        out[result["id"]] = {
            "j": jaccard(result), "rows": result["rows"],
            "gold": result["gold_rows"],
            "kind": kind(answer, result, q.gold_query()[1], max_steps),
            "steps": len(tool_steps(answer)),
            "verifies": sum(s["action"] == "verify" for s in steps),
            "rejections": sum(rejected(s) for s in steps),
            "verify_failed": sum(
                s["action"] == "verify"
                and s["observation"].startswith("The verification failed")
                for s in steps
            ),
            "tokens": result["tokens"], "seconds": result["generation_seconds"],
            "reasons": [
                " ".join(s["observation"].split("Answers the question: no", 1)
                         [1].split())[:200]
                for s in steps if rejected(s)
            ],
        }
    return out


def cell(x):
    if x is None:
        return "–"
    mark = f" R{x['rejections']}" if x["rejections"] else ""
    return f"{x['j']:.2f} ({x['rows']}/{x['gold']}){mark}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset")
    parser.add_argument("models", nargs="+")
    parser.add_argument("--split", required=True)
    parser.add_argument("--lang", default="en")
    parser.add_argument("--max-steps", type=int, default=8)
    args = parser.parse_args()
    dataset = load_dataset(args.dataset)
    questions = {q.id: q for q in dataset.questions}
    ids = [q.id for q in dataset.select(split=args.split)]
    models = {}
    for spec in args.models:
        label, runs = spec.split("=", 1)
        runs = runs.split(",")
        models[label] = [
            load(r, questions, args.split, args.lang, args.max_steps)
            for r in runs
        ]

    labels = list(models)
    print("| question | " + " | ".join(labels) + " |")
    print("|---|" + "---|" * len(labels))
    for i in ids:
        cur = [models[m][0].get(i) for m in labels]
        if all(x is not None and x["j"] == 1.0 for x in cur):
            continue
        print(f"| {i} | " + " | ".join(
            cell(x) + ("" if x is None or x["j"] == 1.0 else f" {x['kind']}")
            for x in cur
        ) + " |")

    print("\n| model | n | mean J | exact | steps | verify calls "
          "| rejections | verify errors | tokens/q | s/q |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for m in labels:
        for k, run in enumerate(models[m]):
            xs = [run[i] for i in ids if i in run]
            if not xs:
                continue
            name = m if k == 0 else f"{m} (earlier)"
            print(
                f"| {name} | {len(xs)} | {mean(x['j'] for x in xs):.3f} "
                f"| {sum(x['j'] == 1.0 for x in xs)} "
                f"| {mean(x['steps'] for x in xs):.1f} "
                f"| {sum(x['verifies'] for x in xs)} "
                f"| {sum(x['rejections'] for x in xs)} "
                f"| {sum(x['verify_failed'] for x in xs)} "
                f"| {mean(x['tokens'] for x in xs) / 1000:.0f}k "
                f"| {mean(x['seconds'] for x in xs):.0f} |"
            )

    print("\nChanged outcome (exact or not) against the earlier run:\n")
    for m in labels:
        if len(models[m]) < 2:
            continue
        new, old = models[m][0], models[m][1]
        for i in ids:
            a, b = old.get(i), new.get(i)
            if a is None or b is None:
                continue
            if (a["j"] == 1.0) != (b["j"] == 1.0) or (
                a["j"] < 1.0 and abs(a["j"] - b["j"]) > 1e-9
            ):
                print(f"- {m} {i}: {cell(a)} {a['kind']} → {cell(b)} "
                      f"{b['kind']}")


    print("\nVerifier rejections (final J of the question, reason):\n")
    for m in labels:
        run = models[m][0]
        for i in ids:
            x = run.get(i)
            for reason in (x or {}).get("reasons", []):
                print(f"- {m} {i} (J {x['j']:.2f}, {x['kind']}): {reason}")


if __name__ == "__main__":
    main()
