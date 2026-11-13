"""
Step 1 of the judge cascade (plan "distil more Sonnet trajectories"): the
agreement gate over the round-2 teacher answers.

A question of data/distill/pool2.json is

    accepted       when Sonnet's query ran and returned rows, and at least
                   2 of the 3 DeepSeek answers return the same rows
                   (judge_cascade.same_rows: F1 = 1 both ways, columns
                   aligned, normalised values);
    disagreement   when Sonnet's query ran with rows but no such majority
                   (left to the judges, steps 2-3);
    sonnet_failed  when Sonnet gave no query, an invalid one, or no rows;
    unanswered     when Sonnet or a DeepSeek sample has no answer yet.

The third DeepSeek sample is only needed when the first two split
(scripts/distill.py answer --lazy skips the others).

    python scripts/agreement_gate.py [--round2 data/distill/round2]
    python scripts/agreement_gate.py --judge     # then the Sonnet judge

writes ROUND2/agreement.json: the counts per category and the status of
each question, and how many Sonnet answers met the assistant's query
guard (memory or time limit) on the way. ``--judge`` sends every
disagreement to Sonnet on OpenRouter, once, with judge_cascade.py's
prompt (VERDICT: yes/no; no DeepSeek judge: too weak in the calibration,
runs/nsv3d-step1.md), appending to ROUND2/judge.sonnet.jsonl, and counts
the outcome (kept = accepted + judged yes).
"""

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from judge_cascade import same_rows  # noqa: E402

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
    votes = [ran(a) and same_rows(a["rows"], teacher["rows"])
             for a in answers if a is not None]
    if sum(votes) >= 2:
        return "accepted", sum(votes)
    if len(votes) - sum(votes) >= 2:
        return "disagreement", sum(votes)
    return "unanswered", None


GUARD = ("The query was stopped: it used too much memory",
         "and was stopped: restrict it", "takes too long, they are")


def guarded(answer):
    """
    Whether *answer* met the engine's limits: a step stopped by the query
    guard (memory, time), the question given up as stuck in the engine
    (distill.py --question-timeout), or the final rows out of time.
    """
    return bool(answer.get("hung")) or "running the rows" in (
        answer.get("error") or "") or any(
        g in (step.get("observation") or "")
        for step in answer.get("steps", []) for g in GUARD)


def judge(directory, pool, sonnet, questions):
    """Ask Sonnet (OpenRouter) about each disagreement; return verdicts."""
    import httpx
    from judge_cascade import judge_context, judge_messages, verdict

    path = directory / "judge.sonnet.jsonl"
    done = {}
    for line in path.read_text().splitlines() if path.exists() else []:
        record = json.loads(line)
        done[record["id"]] = record["verdict"]
    system = judge_context()
    text = {item["id"]: item["question"] for item in pool}
    headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
    for qid, q in questions.items():
        if q["status"] != "disagreement" or qid in done:
            continue
        teacher = sonnet[qid]
        rows = teacher["rows"]
        preview = "\n".join([f"{len(rows)} rows"] + [
            "  ".join(str(v) for v in row) for row in rows[:10]])
        messages = judge_messages(system, text[qid], teacher["query"],
                                  preview, False)
        for attempt in range(4):
            try:
                response = httpx.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers, timeout=240, json={
                        "model": "anthropic/claude-sonnet-5.5",
                        "messages": messages, "temperature": 0.0,
                        "max_tokens": 2000})
                response.raise_for_status()
                data = response.json()
                reply = data["choices"][0]["message"]["content"] or ""
                break
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                print(f"{qid}: {type(exc).__name__}, retry", file=sys.stderr)
                time.sleep(10 * (attempt + 1))
        else:
            continue
        usage = data.get("usage", {})
        record = {"id": qid, "verdict": verdict(reply),
                  "in": usage.get("prompt_tokens", 0),
                  "out": usage.get("completion_tokens", 0),
                  "reason": " ".join(reply.split())[-500:]}
        with open(path, "a") as out:
            out.write(json.dumps(record) + "\n")
        done[qid] = record["verdict"]
        print(f"{qid}: {record['verdict']}", file=sys.stderr)
    return done


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--round2", default=str(ROOT / "data/distill/round2"))
    parser.add_argument("--pool", default=str(ROOT / "data/distill/pool2.json"))
    parser.add_argument("--judge", action="store_true",
                        help="ask Sonnet about the disagreements")
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
            "sonnet_guard": bool(sonnet.get(qid)) and guarded(sonnet[qid]),
        }
        if questions[qid]["sonnet_guard"]:
            counts[category]["sonnet_guard"] += 1
            counts["all"]["sonnet_guard"] += 1
            if verdict == "sonnet_failed":
                counts[category]["sonnet_failed_engine"] += 1
                counts["all"]["sonnet_failed_engine"] += 1
    if args.judge or (directory / "judge.sonnet.jsonl").exists():
        verdicts = judge(directory, pool, sonnet, questions) if args.judge else {
            r["id"]: r["verdict"] for r in map(
                json.loads,
                (directory / "judge.sonnet.jsonl").read_text().splitlines())}
        for qid, q in questions.items():
            if q["status"] == "disagreement" and qid in verdicts:
                q["sonnet_judge"] = verdicts[qid]
                key = "judge_yes" if verdicts[qid] else "judge_no"
                counts[q["category"]][key] += 1
                counts["all"][key] += 1
        for c in counts:
            counts[c]["kept"] = counts[c]["accepted"] + counts[c]["judge_yes"]
    order = ["accepted", "disagreement", "judge_yes", "judge_no", "kept",
             "sonnet_failed", "sonnet_failed_engine", "sonnet_guard",
             "unanswered"]
    table = {c: {s: counts[c][s] for s in order}
             for c in sorted(counts, key=lambda c: (c == "all", c))}
    # the teacher's answers, merged and small enough for git: every step,
    # the first 10 rows and the row count
    with open(directory / "react.sonnet.compact.jsonl", "w") as compact:
        for item in pool:
            if item["id"] in sonnet:
                answer = dict(sonnet[item["id"]], category=item["category"])
                answer["n_rows"] = len(answer["rows"])
                answer["rows"] = answer["rows"][:10]
                answer["gate"] = questions[item["id"]]
                compact.write(json.dumps(answer, default=str) + "\n")
    out = directory / "agreement.json"
    out.write_text(json.dumps({"counts": table, "questions": questions},
                              indent=1))
    print("| category | " + " | ".join(order) + " |")
    for c, row in table.items():
        print(f"| {c} | " + " | ".join(str(row[s]) for s in order) + " |")
    print(f"written {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
