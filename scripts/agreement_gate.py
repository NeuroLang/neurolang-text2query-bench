"""
Step 1 of the judge cascade (plan "distil more Sonnet trajectories"): the
agreement gate over the round-2 teacher answers.

A question of data/distill/pool2.json is

    accepted       when Sonnet's query ran and returned rows, and at least
                   2 of the 3 DeepSeek answers return the same rows (the
                   bench metric: normalised values, columns aligned,
                   F1 = 1 against Sonnet's rows);
    disagreement   when Sonnet's query ran with rows but no such majority
                   (left to the judges, steps 2-3);
    sonnet_failed  when Sonnet gave no query, an invalid one, or no rows;
    unanswered     when Sonnet or a DeepSeek sample has no answer yet.

The third DeepSeek sample is only needed when the first two split
(scripts/distill.py answer --lazy skips the others).

    python scripts/agreement_gate.py [--round2 data/distill/round2]

writes ROUND2/agreement.json: the counts per category and the status of
each question.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from text2query_bench.metrics import score

ROOT = Path(__file__).resolve().parent.parent


def load(directory, tag):
    """Return {id: answer} of the answer files of *tag* (all workers)."""
    answers = {}
    for path in sorted(directory.glob(f"{tag}.*jsonl")):
        for line in path.read_text().splitlines():
            entry = json.loads(line)
            answers[entry["id"]] = entry
    return answers


def ran(answer):
    return bool(answer and answer.get("query") and answer.get("valid")
                and not answer.get("error") and answer.get("rows"))


def status(teacher, answers):
    """
    Return the status of a question (see the module) from Sonnet's answer
    *teacher* and the DeepSeek *answers* (None when missing), and the
    number of DeepSeek answers agreeing. Two answers decide when they
    agree with each other on Sonnet: the third is then not needed.
    """
    if teacher is None:
        return "unanswered", None
    if not ran(teacher):
        return "sonnet_failed", None
    votes = [ran(a) and score(a["rows"], teacher["rows"]).exact
             for a in answers if a is not None]
    if sum(votes) >= 2:
        return "accepted", sum(votes)
    if len(votes) - sum(votes) >= 2:
        return "disagreement", sum(votes)
    return "unanswered", None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--round2", default=str(ROOT / "data/distill/round2"))
    parser.add_argument("--pool", default=str(ROOT / "data/distill/pool2.json"))
    args = parser.parse_args()
    directory = Path(args.round2)
    pool = json.loads(Path(args.pool).read_text())
    sonnet = load(directory, "react.sonnet")
    samples = [load(directory, f"deepseek.{i}") for i in range(3)]
    counts = defaultdict(Counter)
    questions = {}
    for item in pool:
        qid, category = item["id"], item["category"]
        answers = [s.get(qid) for s in samples]
        verdict, agree = status(sonnet.get(qid), answers)
        counts[category][verdict] += 1
        counts["all"][verdict] += 1
        questions[qid] = {
            "category": category, "status": verdict,
            "deepseek_agreeing": agree,
            "deepseek_answers": sum(a is not None for a in answers),
        }
    order = ["accepted", "disagreement", "sonnet_failed", "unanswered"]
    table = {c: {s: counts[c][s] for s in order}
             for c in sorted(counts, key=lambda c: (c == "all", c))}
    out = directory / "agreement.json"
    out.write_text(json.dumps({"counts": table, "questions": questions},
                              indent=1))
    print(f"{'category':16} " + " ".join(f"{s:>13}" for s in order))
    for c, row in table.items():
        print(f"{c:16} " + " ".join(f"{row[s]:>13}" for s in order))
    print(f"written {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
