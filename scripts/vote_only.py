"""
The answers of a run with a fallback provider as the vote alone gave
them: each answer the fallback gave is replaced by the query the vote kept
(the ``voted`` argument of its ``fallback`` step, invalid when empty).

    python scripts/vote_only.py RUN OUT
    python scripts/reevaluate.py DATASET OUT
"""
import json
import sys
from pathlib import Path


def main():
    run, out = Path(sys.argv[1]), Path(sys.argv[2])
    answers = json.loads((run / "answers.json").read_text())
    for answer in answers:
        step = next(
            (s for s in answer.get("steps", []) if s["action"] == "fallback"),
            None,
        )
        if step is not None:
            voted = step["arguments"]["voted"]
            answer.update(query=voted, valid=bool(voted),
                          error="" if voted else "No valid answer to vote on.")
    out.mkdir(parents=True, exist_ok=True)
    (out / "answers.json").write_text(json.dumps(answers, indent=2))


if __name__ == "__main__":
    main()
