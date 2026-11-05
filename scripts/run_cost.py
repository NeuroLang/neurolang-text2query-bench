"""
Cost per question of runs, from the input/output tokens of the traces
(trace/<id>-<lang>.jsonl, 'reply' events) and the OpenRouter prices
(USD per million tokens, https://openrouter.ai/api/v1/models, 2026-11-05).

    python scripts/run_cost.py datasets/neurosynth-v2.yaml dev nemotron=runs/nsv2-dev-nemotron-before ...
    (SPLIT '-' for all the questions of the run)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from text2query_bench.dataset import load_dataset  # noqa: E402

PRICES = {  # input, output
    "nemotron": (0.07, 0.20), "gemma": (0.20, 0.40),
    "deepseek": (0.0434, 0.30), "sonnet": (2.0, 10.0),
}


def main():
    ds = load_dataset(sys.argv[1])
    split = sys.argv[2]
    ids = {q.id for q in ds.questions if split == "-" or q.split == split}
    for spec in sys.argv[3:]:
        label, run = spec.split("=")
        key = next(k for k in PRICES if label.lower().startswith(k))
        pi, po = PRICES[key]
        n = tin = tout = 0
        for f in sorted(Path(run, "trace").glob("*-en.jsonl")):
            if f.name[:-len("-en.jsonl")] not in ids:
                continue
            n += 1
            for line in open(f):
                e = json.loads(line)
                if e["event"] == "reply":
                    tin += e["usage"]["input"]
                    tout += e["usage"]["output"]
        print(f"{label}: n={n} in/q={tin/n/1000:.1f}k out/q={tout/n/1000:.2f}k "
              f"cost/q=${(tin*pi + tout*po)/1e6/n:.5f}")


if __name__ == "__main__":
    main()
