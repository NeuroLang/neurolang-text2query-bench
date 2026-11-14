"""
Check similar_study with the query-level gate on the real engine
(NeuroLang #1225): rows against the old aggregation rules, and timings.

    HOME=/tmp/tf/home PYTHONPATH=<NeuroLang>/packages/... \\
      python scripts/similarity_gate_engine.py --data-dir neurolang_data
"""
import argparse
import time
import warnings
from pathlib import Path

OLD = """
old_cutoff(q, percentile(v, 95)) :- study_similarity(q, s, v)
old_similar_study(q, s) :- study_similarity(q, s, v) & old_cutoff(q, c) & (v >= c)
"""
TEXTS = [
    "def:memory", "def:working memory", "socially excluded",
    "being socially excluded in a ball-tossing game",
    "tapping fingers in sequence", "tasting bitter drinks",
    "imagining future events", "medieval castle architecture",
    "stock market crash", "golf handicap calculation",
]
SHAPES = {
    "Neuron per year, study_journal inline (slow shape)":
        "ans(y, count(s)) :- cogat_definition('memory', d), "
        "similar_study(d, s), study_journal(s, 'Neuron'), study_year(s, y)",
    "Neuron per year, neuron(s) rule":
        "neuron(s) :- study_journal(s, 'Neuron')\n"
        "ans(y, count(s)) :- cogat_definition('memory', d), "
        "similar_study(d, s), neuron(s), study_year(s, y)",
    "close(s) under PROB":
        "close(s) :- cogat_definition('memory', d), similar_study(d, s), "
        "selected_study(s)\n"
        "ans(s, p) :- PROB[close(s)] = p",
    "cogat_definition('memory', d), similar_study(d, s)":
        "ans(s) :- cogat_definition('memory', d), similar_study(d, s)",
}


def rows(nl, program):
    with nl.scope:
        res = nl.execute_datalog_program(program)
    return set() if res is None else set(res)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--data-dir", default="neurolang_data")
    p.add_argument("--runs", type=int, default=2)
    args = p.parse_args(argv)
    warnings.simplefilter("ignore")
    from neurolang_apps.utils import engine_registry

    nl = engine_registry.build_engine("neurosynth", Path(args.data_dir), None)
    for name, program in SHAPES.items():
        times = []
        for _ in range(args.runs):
            # A fresh engine cache per run is not needed: the query
            # embedding and the cutoff are cached after the first run.
            start = time.perf_counter()
            n = len(rows(nl, program))
            times.append(time.perf_counter() - start)
        print(f"| {name} | " + " / ".join(f"{t:.1f} s" for t in times)
              + f" | {n} |")
    print()
    # The free texts of the assistant's example bank, against the gate.
    import re

    import numpy as np
    import neurolang_apps

    bank = (Path(neurolang_apps.__file__).parent / "utils/engines"
            "/coordinate_meta_analysis/examples.yaml").read_text()
    index = nl.text_embedding_indexes["study_abstracts"]
    gate = engine_registry.get_engine_config("neurosynth")[
        "text_embeddings"]["study_abstracts"]["similarity_gate"]
    for text in sorted(set(re.findall(
            r"(?:similar_study|given_close)\('([^']+)'", bank))):
        v = index.scores(text)
        top = np.sort(v[v > 0])[-20:].mean()
        print(f"bank: {text}: top-20 mean {top:.4f}, "
              f"{'passes' if top >= gate else 'fails'} the gate {gate}")
    print()
    print("| text | old top 5% | similar_study | equal |")
    print("|---|---|---|---|")
    for text in TEXTS:
        if text.startswith("def:"):
            body = f"cogat_definition('{text[4:]}', q) & {{}}(q, s)"
        else:
            body = f"{{}}('{text}', s)"
        old = rows(nl, OLD + "ans(s) :- " + body.format("old_similar_study"))
        new = rows(nl, "ans(s) :- " + body.format("similar_study"))
        print(f"| {text} | {len(old)} | {len(new)} | "
              f"{'yes' if new == old else 'no'} |")


if __name__ == "__main__":
    main()
