"""
Where the search-loop notice (NeuroLang PR, Toolbox.call: after two
search_values calls finding no new value, the observation asks for a query
with the values found) would have fired in past runs, replaying their
recorded steps.

    python scripts/search_loop_replay.py RUN...

Per answer with a notice: the step it would fire at, the search calls, the
steps, and whether the answer was exact (results.json).
"""
import json
import sys
from pathlib import Path

REPEATED = "You already called search_values"


def first_notice(steps):
    """Return the index of the step the notice fires at, or None."""
    found, stale, seen = set(), 0, {}
    for n, step in enumerate(steps):
        if step["action"] != "search_values":
            continue
        key = json.dumps(step["arguments"], sort_keys=True)
        observation = step["observation"]
        if observation.startswith(REPEATED) or key in seen:
            values = set()  # a repeated call finds nothing new
        else:
            seen[key] = observation
            values = set(observation.splitlines()[1:])
        new = not values <= found
        stale += not new
        found |= values
        if not new and stale >= 2:
            return n
    return None


def main():
    total = fired = 0
    for run in map(Path, sys.argv[1:]):
        answers = json.loads((run / "answers.json").read_text())
        results = run / "results.json"
        exact = {
            r["id"] for r in json.loads(results.read_text())["results"]
            if r.get("f1") == 1.0
        } if results.exists() else set()
        for a in answers:
            total += 1
            steps = a.get("steps", [])
            n = first_notice(steps)
            if n is None:
                continue
            fired += 1
            searches = sum(s["action"] == "search_values" for s in steps)
            print(f"{run.name} {a['id']}: notice at step {n + 1} of "
                  f"{len(steps)}, {searches} searches, "
                  f"{'exact' if a['id'] in exact else 'MISS'}"
                  f"{' (out of steps)' if 'after' in (a.get('error') or '') or 'last query' in (a.get('explanation') or '') else ''}")
    print(f"{fired} of {total} answers")


if __name__ == "__main__":
    main()
