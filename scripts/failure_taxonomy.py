"""
Scores and failure kinds of runs on a dataset with splits, as Markdown.

For each run directory (answers.json and results.json of ``t2q-bench
run``), per split: F1, exact, valid, runs, mean steps, calls, tokens and
seconds a question, then F1 per tag, then the kind of each answer that
is not exact:

- llm error: the generation failed (provider error, quota, 429);
- timeout: the query ran out of time on the engine;
- syntax/validation: the query did not run, or the agent did not
  accept it;
- out of steps: the agent never had a final answer accepted and used
  all its steps (its answer is then its last query with rows);
- empty answer: the query ran and returned no rows;
- no choice: the gold is a probability over selected_study and the
  query does not use it (PROB over stored relations, or a list or a
  count instead of a probability);
- wrong predicate: it reads other engine predicates than the gold;
- wrong value: the same predicates, other constants (terms, labels,
  texts, coordinates);
- wrong structure: the same predicates and constants, another shape
  (conditioning, grouping, columns).

    python scripts/failure_taxonomy.py datasets/neurosynth-v2.yaml \
        runs/nsv2-react-sonnet runs/nsv2-react-gemma-or-dev ...
"""

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from text2query_bench.dataset import load_dataset

KINDS = (
    "exact", "llm error", "timeout", "syntax/validation", "out of steps",
    "empty answer", "no choice", "wrong predicate", "wrong value",
    "wrong structure",
)
NOT_PREDICATES = {
    "PROB", "AGGREGATE", "count", "max", "min", "sum", "mean", "startswith",
    "euclidean", "EUCLIDEAN", "lcase", "exp", "log", "ans",
}
_ATOM = re.compile(r"([A-Za-z_][\w:]*)\s*\(")
_HEAD = re.compile(r"^\s*([A-Za-z_][\w:]*)\s*\(", re.M)
_STRING = re.compile(r"'([^']*)'")
_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?")


def engine_predicates(query: str) -> set:
    """Return the predicates *query* reads that it does not define."""
    defined = set(_HEAD.findall(query))
    return {
        name for name in _ATOM.findall(query)
        if name not in defined and name not in NOT_PREDICATES
    }


def constants(query: str) -> set:
    """Return the string and numeric constants of *query*."""
    strings = set(_STRING.findall(query))
    numbers = {
        float(n) for n in _NUMBER.findall(_STRING.sub("", query))
        if n not in ("0", "1")
    }
    return strings | numbers


def accepted(answer: dict) -> bool:
    return any(
        step["action"] == "final_answer"
        and step["observation"].startswith("Accepted")
        for step in answer.get("steps", [])
    )


def kind(answer: dict, result: dict, gold_query: str, max_steps: int) -> str:
    """Return the kind of *result*, the score of *answer*."""
    if result["f1"] == 1.0:
        return "exact"
    out_of_steps = (
        not accepted(answer) and len(answer.get("steps", [])) >= max_steps
    )
    if answer.get("error") and not answer.get("query"):
        return "out of steps" if out_of_steps else "llm error"
    error = result.get("error") or ""
    if "timeout" in error:
        return "timeout"
    if not answer.get("query") or not result["executed"]:
        return "out of steps" if out_of_steps else "syntax/validation"
    if out_of_steps:
        return "out of steps"
    if not result["valid"]:
        return "syntax/validation"
    if result["rows"] == 0:
        return "empty answer"
    query = answer["query"]
    if "selected_study" in gold_query and "selected_study" not in query:
        return "no choice"
    if engine_predicates(query) != engine_predicates(gold_query):
        return "wrong predicate"
    if constants(query) != constants(gold_query):
        return "wrong value"
    return "wrong structure"


def load_run(directory: Path):
    answers = json.loads((directory / "answers.json").read_text())
    results = json.loads((directory / "results.json").read_text())["results"]
    by_key = {(a["id"], a["language"]): a for a in answers}
    return [(by_key[(r["id"], r["language"])], r) for r in results]


def row(name, pairs, kinds):
    n = len(pairs)
    if not n:
        return None
    results = [r for _, r in pairs]
    answers = [a for a, _ in pairs]
    return (
        f"| {name} | {n} | {mean(r['f1'] for r in results):.3f} "
        f"| {mean(r['f1'] == 1.0 for r in results):.0%} "
        f"| {mean(bool(r['valid']) for r in results):.0%} "
        f"| {mean(bool(r['executed']) for r in results):.0%} "
        f"| {mean(len(a.get('steps', [])) for a in answers):.1f} "
        f"| {mean(r['calls'] for r in results):.1f} "
        f"| {mean(r['tokens'] for r in results) / 1000:.0f}k "
        f"| {mean(r['generation_seconds'] for r in results):.0f} |"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset")
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--examples", type=int, default=0,
                        help="list this many failures per run")
    parser.add_argument("--split", help="keep the questions of this split")
    args = parser.parse_args()
    dataset = load_dataset(args.dataset)
    questions = {q.id: q for q in dataset.questions}
    runs = {}
    for directory in args.runs:
        pairs = [
            p for p in load_run(directory)
            if not args.split or questions[p[1]["id"]].split == args.split
        ]
        for answer, result in pairs:
            q = questions[result["id"]]
            result["kind"] = kind(
                answer, result, q.gold_query()[1], args.max_steps
            )
        runs[directory.name] = pairs

    print("| run | n | F1 | exact | valid | runs | steps | calls | "
          "tokens | s/q |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name, pairs in runs.items():
        for split in ("dev", "test", ""):
            selected = [
                p for p in pairs
                if not split or questions[p[1]["id"]].split == split
            ]
            if split and len(selected) == len(pairs):
                continue
            line = row(f"{name} {split or 'all'}", selected, None)
            if line:
                print(line)

    tags = sorted({t for q in dataset.questions for t in q.tags})
    print("\n| run | " + " | ".join(tags) + " |")
    print("|---|" + "---:|" * len(tags))
    for name, pairs in runs.items():
        by_tag = defaultdict(list)
        for _, r in pairs:
            for tag in questions[r["id"]].tags:
                by_tag[tag].append(r["f1"])
        print(f"| {name} | " + " | ".join(
            f"{mean(by_tag[t]):.2f}" if by_tag[t] else "" for t in tags
        ) + " |")

    print("\n| run | " + " | ".join(KINDS) + " |")
    print("|---|" + "---:|" * len(KINDS))
    for name, pairs in runs.items():
        counts = Counter(r["kind"] for _, r in pairs)
        print(f"| {name} | " + " | ".join(
            str(counts[k]) for k in KINDS
        ) + " |")

    if args.examples:
        for name, pairs in runs.items():
            print(f"\n### {name}\n")
            failures = [p for p in pairs if p[1]["kind"] != "exact"]
            for answer, r in failures[: args.examples]:
                query = " ".join(answer.get("query", "").split())
                print(f"- {r['id']} [{r['language']}] {r['kind']}, F1 "
                      f"{r['f1']:.2f}, {len(answer.get('steps', []))} "
                      f"steps: `{query[:300]}`"
                      + (f" ({(r.get('error') or answer.get('error'))[:150]})"
                         if (r.get('error') or answer.get('error')) else ""))


if __name__ == "__main__":
    main()
