"""
Scores of runs on three subsets of questions, and how the models answer
the questions naming a cognitive concept (runs/nsv3d.md):

- concept: the questions whose gold moved to the Cognitive Atlas
  definition (or the question's words) with similar_study;
- about-term: golds still on mentions although the question does not
  say mention, term or word (anatomy, disorders, populations, stimuli);
- rest: the other questions.

For each concept question: whether a step searched cogat_term
(search_values over it), and whether the final query uses
cogat_definition with similar_study, similar_study alone, or mentions.
A vote run's steps are those of its three samples (and the fallback).

    python scripts/nsv3d_cogat_usage.py DATASET SPLIT LABEL=RUN ...
    (SPLIT '-' for all the questions of the run)
"""

import json
import re
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).parent))
from nsv2_overlap import jaccard  # noqa: E402

from text2query_bench.dataset import load_dataset  # noqa: E402

CONCEPT = {"p-038", "p-041", "dh-122", "f-030", "f-031", "f-048", "f-078",
           "f-102", "f-133"}
SAYS_TERM = re.compile(r"mention|term|word|vocab", re.I)


def subset(q):
    if q.id in CONCEPT:
        return "concept"
    if "mentions(" in q.gold_query()[1] and not SAYS_TERM.search(
            q.text["en"]):
        return "about-term"
    return "rest"


def form(query):
    query = query or ""
    if "cogat_definition" in query and "similar_study" in query:
        return "cogat+similar"
    if "similar_study" in query or "_given_similar" in query:
        return "similar(words)"
    if "mentions(" in query:
        return "mentions"
    return "other"


def looked_up(steps):
    """search: search_values over cogat_term; query: a query of a step
    (run, check, describe) on cogat_term or cogat_definition."""
    if any(
        s["action"] == "search_values" and (
            "cogat_term" in (s["arguments"].get("name"),
                             s["arguments"].get("predicate"))
            or "cogat_term(" in (s.get("observation") or ""))
        for s in steps
    ):
        return "search"
    if any(
        s["action"] in ("run_query", "check_query", "describe_predicate")
        and re.search(r"cogat_(term|definition)", json.dumps(s["arguments"]))
        for s in steps
    ):
        return "query"
    return "no"


def main():
    ds = load_dataset(sys.argv[1])
    split = sys.argv[2]
    questions = {q.id: q for q in ds.questions
                 if split == "-" or q.split == split}
    for spec in sys.argv[3:]:
        label, run = spec.split("=")
        results = {r["id"]: r for r in json.loads(
            Path(run, "results.json").read_text())["results"]
            if r["language"] == "en" and r["id"] in questions}
        answers = {a["id"]: a for a in json.loads(
            Path(run, "answers.json").read_text())
            if a["language"] == "en" and a["id"] in questions}
        parts = []
        for name in ("concept", "about-term", "rest", "all"):
            js = [jaccard(r) for i, r in results.items()
                  if name == "all" or subset(questions[i]) == name]
            if js:
                exact = sum(j == 1.0 for j in js)
                parts.append(f"{name} {mean(js):.3f} ({exact}/{len(js)})")
        print(f"{label}: " + "; ".join(parts))
        for i in sorted(results):
            if subset(questions[i]) != "concept":
                continue
            a = answers[i]
            print(f"  {i}: J={jaccard(results[i]):.2f} "
                  f"lookup={looked_up(a.get('steps', []))} "
                  f"final={form(a.get('query'))}")


if __name__ == "__main__":
    main()
