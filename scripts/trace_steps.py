"""
Print the steps of answers of a run, one line per tool call, for reading
why an answer missed.

    python scripts/trace_steps.py RUN [ID ...]

Each step shows its action and arguments, and the start of its
observation; replies the agent could not parse show the model's text
(empty for a reply cut by reasoning at max_tokens). The output tokens of
each reply come from the trace.
"""

import json
import sys
from pathlib import Path


def replies(run: Path, qid: str):
    """Return the (text, output tokens) of the replies of question *qid*."""
    path = next(iter(sorted((run / "trace").glob(f"{qid}-*.jsonl"))), None)
    if path is None:
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["event"] == "reply":
            out.append(
                (event.get("text") or "", (event.get("usage") or {}).get(
                    "output", 0))
            )
    return out


def main(run, *ids):
    run = Path(run)
    answers = json.loads((run / "answers.json").read_text(encoding="utf-8"))
    for answer in answers:
        if ids and answer["id"] not in ids:
            continue
        texts = replies(run, answer["id"])
        print(f"===== {answer['id']} {answer.get('error') or ''}")
        print("final:", " | ".join((answer.get("query") or "").splitlines()))
        for n, step in enumerate(answer.get("steps", [])):
            text, tokens = texts[n] if n < len(texts) else ("", 0)
            arguments = json.dumps(step.get("arguments", {}),
                                   ensure_ascii=False)
            print(f"-- {step['action'] or '(unparsed)'} {arguments[:400]}"
                  f" [{tokens} out]")
            if not step["action"]:
                print("   reply:", repr(text[:300]))
            observation = " | ".join(step["observation"].splitlines())
            print("   obs:", observation[:300])


if __name__ == "__main__":
    main(*sys.argv[1:])
