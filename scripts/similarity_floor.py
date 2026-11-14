"""
Calibrate an absolute similarity floor for ``similar_study``.

``similar_study(q, s)`` keeps the studies whose cosine similarity to the
text q is in its top 5 % (``percentile(v, 95)``).  A text that no study
is about still gets its top 5 %.  An absolute floor, ``v >= FLOOR``,
would return nothing for such a text, if some value separates the
in-domain texts from the unrelated ones.

This script scores the studies of an engine against two lists of texts,
in-domain (neuroscience, Cognitive Atlas definitions) and unrelated, with
the engine's own text-embedding index (``EmbeddingIndex.scores``, the
values ``query_similarity`` returns), and prints for each text:
max, 95th percentile, mean and sd of the scores, the number of studies
at or above each floor, and how many of the top 5 % survive each floor.

    HOME=/tmp/tf/home PYTHONPATH=<NeuroLang>/packages/... \\
      python scripts/similarity_floor.py --engine neurosynth \\
        --data-dir neurolang_data [--index study_abstracts] \\
        [--floors 0.7 0.75 0.8 0.85 0.9]

Decision rule (see the summary it prints): a floor separates the two
lists if every in-domain text keeps at least --min-kept studies of its
top 5 % and every unrelated text keeps none; the script reports the
interval of such floors, if any, and otherwise says that no floor does.
"""
import argparse
import warnings
from pathlib import Path

import numpy as np

# Cognitive Atlas terms whose definitions are used as texts (what
# ``cogat_definition('<term>', d)`` gives the query assistant).
COGAT_TERMS = [
    "working memory", "response inhibition", "memory", "attention",
    "emotion regulation", "face perception",
]
# Free texts in the domain.
DOMAIN_TEXTS = [
    "visual word form area", "pain", "reward anticipation",
    "being socially excluded in a ball-tossing game",
    "tapping fingers in sequence",
]
# Texts no study of a neuroimaging database is about.
UNRELATED_TEXTS = [
    "chocolate cake recipe", "football match results", "stock market crash",
    "medieval castle architecture", "how to fix a bicycle tyre",
    "best beaches in Portugal for surfing", "tax return deadline extension",
    "knitting a wool scarf pattern", "the history of the Roman empire",
    "smartphone battery life comparison",
]


def cogat_definitions(nl, terms):
    """Return {term: definition} for the terms found in the engine."""
    from neurolang_apps.utils.cli import result_to_dataframe

    found = {}
    for term in terms:
        with nl.scope:
            rows = nl.execute_datalog_program(
                f"ans(d) :- cogat_definition('{term}', d)"
            )
        values = [] if rows is None else list(
            result_to_dataframe(rows).iloc[:, 0]
        )
        if values:
            found[term] = values[0]
    return found


def stats(scores, floors, top=95):
    valid = scores[np.isfinite(scores) & (scores > 0)]
    cut = np.percentile(valid, top)
    top_scores = valid[valid >= cut]
    row = {
        "max": valid.max(), "p95": cut, "mean": valid.mean(),
        "sd": valid.std(), "top": len(top_scores),
    }
    for f in floors:
        row[f"n>={f}"] = int((valid >= f).sum())
        row[f"top>={f}"] = int((top_scores >= f).sum())
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--engine", default="neurosynth")
    parser.add_argument("--data-dir", default="neurolang_data")
    parser.add_argument("--yaml", default=None, help="engines YAML file")
    parser.add_argument("--index", default=None,
                        help="text-embedding index (default: the first)")
    parser.add_argument("--floors", type=float, nargs="+",
                        default=[0.7, 0.75, 0.8, 0.85, 0.9])
    parser.add_argument("--min-kept", type=int, default=20,
                        help="studies an in-domain text must keep")
    args = parser.parse_args(argv)
    warnings.simplefilter("ignore")
    from neurolang_apps.utils import engine_registry

    nl = engine_registry.build_engine(
        args.engine, Path(args.data_dir), None,
        yaml_path=None if args.yaml is None else Path(args.yaml),
    )
    indexes = nl.text_embedding_indexes
    index = indexes[args.index or next(iter(indexes))]
    texts = [("cogat", f"def:{t}", d)
             for t, d in cogat_definitions(nl, COGAT_TERMS).items()]
    texts += [("domain", t, t) for t in DOMAIN_TEXTS]
    texts += [("unrelated", t, t) for t in UNRELATED_TEXTS]
    rows = []
    for kind, label, text in texts:
        rows.append((kind, label, stats(np.asarray(index.scores(text)),
                                        args.floors)))
    keys = list(rows[0][2])
    print("| kind | text | " + " | ".join(keys) + " |")
    print("|" + "---|" * (len(keys) + 2))
    for kind, label, r in rows:
        cells = [f"{r[k]:.3f}" if isinstance(r[k], (float, np.floating)) else str(r[k])
                 for k in keys]
        print(f"| {kind} | {label[:40]} | " + " | ".join(cells) + " |")
    # Separating floors: every in-domain text keeps >= min_kept of its top
    # 5 %, every unrelated text keeps none.  The kept count only falls as the
    # floor rises, so the separating floors form the interval
    # (max of the unrelated maxima, lowest top-5 %-min-kept-th score of the
    # in-domain texts].
    unrelated_max = max(r["max"] for k, _, r in rows if k == "unrelated")
    domain_ceiling = min(
        np.sort(np.asarray(index.scores(text)))[-args.min_kept]
        for (k, _, text) in texts if k != "unrelated"
    )
    print(f"\nhighest score of an unrelated text: {unrelated_max:.4f}")
    print(f"lowest {args.min_kept}-th best score of an in-domain text: "
          f"{domain_ceiling:.4f}")
    if unrelated_max < domain_ceiling:
        print(f"separating floors: ({unrelated_max:.4f}, {domain_ceiling:.4f}]"
              f"; midpoint {(unrelated_max + domain_ceiling) / 2:.3f}")
    else:
        print("no floor separates the in-domain texts from the unrelated ones")


if __name__ == "__main__":
    main()
