"""
Calibrate a per-query gate for ``similar_study`` against a null of
off-domain texts.

SPECTER2 cosine similarities have a query-dependent baseline: against
the whole corpus a text's median similarity is about 0.7 and varies with
the text.  A raw floor (``v >= 0.75``) measures how neuroscience-like a
text is.  This script standardises each text's scores against its own
distribution over all the studies and asks which query-level statistic
separates in-domain texts from a null of off-domain ones.

Texts:
  * null: scripts/similarity_gate_texts/null.txt (off-domain, short to
    definition-length);
  * cogat: every Cognitive Atlas definition, cogat_definition(t, d);
  * bench: the topics of the benchmark golds using similar_study
    (similar_study('...'), close('...'), p_*_given_close('...')) and the
    definitions of the cogat_definition('<term>', d) they use;
  * phrase: scripts/similarity_gate_texts/domain_phrases.txt.

Each set is split in half at random (fit / check).  For each candidate
statistic: ROC AUC in-domain vs null on the fit half, thresholds at the
null's 95th and 99th percentiles on the fit half, and on the check half
the null false-positive rate and the share of in-domain texts kept.

    HOME=/tmp/tf/home PYTHONPATH=<NeuroLang>/packages/neurolang:... \\
      python scripts/similarity_gate.py --data-dir neurolang_data \\
        [--cache runs/similarity_gate_scores.npz]
"""
import argparse
import re
import warnings
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
TEXTS = HERE / "similarity_gate_texts"
BENCH = ["neurosynth-v2", "neurosynth-v3-heldout", "neurosynth-v3-fresh"]
SHORT = ["tapping fingers in sequence", "socially excluded",
         "tasting bitter drinks"]
TOP = 20


def read_lines(path):
    return [line.strip() for line in path.read_text().splitlines()
            if line.strip() and not line.startswith("#")]


def bench_topics(root):
    """Free-text topics and Cognitive Atlas terms of the bench golds."""
    import yaml

    topics, terms = set(), set()
    for name in BENCH:
        data = yaml.safe_load((root / "datasets" / f"{name}.yaml").read_text())
        for q in data["questions"]:
            dl = q["gold"]["datalog"]
            if "similar_study" not in dl:
                continue
            topics |= set(re.findall(
                r"(?:similar_study|close|given_close)\('([^']+)'", dl))
            terms |= set(re.findall(r"cogat_definition\('([^']+)'", dl))
    return sorted(topics), sorted(terms)


def statistics(scores):
    v = scores[np.isfinite(scores) & (scores > 0)]
    top = np.sort(v)[-TOP:]
    med = np.median(v)
    mad = 1.4826 * np.median(np.abs(v - med))
    mean, sd = v.mean(), v.std()
    zr = (v - med) / mad
    row = {
        "max": v.max(),
        f"top{TOP}": top.mean(),
        "median": med,
        f"top{TOP}-median": top.mean() - med,
        "zmax_mad": (v.max() - med) / mad,
        "zmax_sd": (v.max() - mean) / sd,
        f"ztop{TOP}_mad": (top.mean() - med) / mad,
        f"ztop{TOP}_sd": (top.mean() - mean) / sd,
    }
    for k in (3, 4, 5, 6):
        row[f"n(zmad>={k})"] = int((zr >= k).sum())
        row[f"n(zsd>={k})"] = int(((v - mean) / sd >= k).sum())
    cut = np.percentile(v, 95)
    row["old floor: top5%>=0.75"] = int(((v >= cut) & (v >= 0.75)).sum())
    return row


def auc(pos, neg):
    """P(pos > neg) + P(tie)/2, the Mann-Whitney AUC."""
    from scipy.stats import rankdata

    r = rankdata(np.concatenate([pos, neg]))
    return (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (
        len(pos) * len(neg))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--engine", default="neurosynth")
    p.add_argument("--data-dir", default="neurolang_data")
    p.add_argument("--cache", default="runs/similarity_gate_scores.npz",
                   help="scores of every text (recomputed if absent)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--gate", type=float, default=0.75,
                   help="top-20 mean threshold to report on the check half")
    args = p.parse_args(argv)
    warnings.simplefilter("ignore")
    root = HERE.parent

    from neurolang_apps.utils import engine_registry
    from neurolang_apps.utils.cli import result_to_dataframe

    nl = engine_registry.build_engine(args.engine, Path(args.data_dir), None)
    index = nl.text_embedding_indexes["study_abstracts"]
    with nl.scope:
        defs = result_to_dataframe(nl.execute_datalog_program(
            "ans(t, d) :- cogat_definition(t, d)"))
    pairs = sorted(set(zip(defs.iloc[:, 0], defs.iloc[:, 1])))
    defs = {}
    for t, d in pairs:
        defs.setdefault(t, d)
    topics, terms = bench_topics(root)
    texts = {}  # text -> (kind, label)
    for t in read_lines(TEXTS / "null.txt"):
        texts[t] = ("null", t)
    for t, d in pairs:
        texts.setdefault(d, ("cogat", f"def:{t}"))
    for t in terms:
        if t in defs:
            texts[defs[t]] = ("bench", f"def:{t}")
    for t in topics:
        texts[t] = ("bench", t)
    for t in read_lines(TEXTS / "domain_phrases.txt"):
        texts.setdefault(t, ("phrase", t))
    keys = list(texts)

    cache = Path(args.cache)
    scores = None
    if cache.exists():
        with np.load(cache, allow_pickle=True) as data:
            if list(data["texts"]) == keys:
                scores = data["scores"]
    if scores is None:
        scores = np.stack([np.asarray(index.scores(t), dtype=np.float32)
                           for t in keys])
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez(cache, texts=np.array(keys, dtype=object), scores=scores)

    kinds = np.array([texts[t][0] for t in keys])
    rows = [statistics(s) for s in scores]
    names = list(rows[0])
    stat = {n: np.array([r[n] for r in rows], dtype=float) for n in names}
    rng = np.random.default_rng(args.seed)
    fit = np.zeros(len(keys), bool)
    for kind in ("null", "cogat", "bench", "phrase"):
        idx = np.flatnonzero(kinds == kind)
        fit[rng.permutation(idx)[: len(idx) // 2]] = True
    null = kinds == "null"
    print(f"texts: " + ", ".join(
        f"{k} {np.sum(kinds == k)}" for k in ("null", "cogat", "bench", "phrase")
    ) + f"; studies {scores.shape[1]}")
    print(f"median score: null {np.median(stat['median'][null]):.3f}, "
          f"in-domain {np.median(stat['median'][~null]):.3f}; "
          f"range of medians {stat['median'].min():.3f}-"
          f"{stat['median'].max():.3f}\n")

    typed = np.isin(kinds, ["bench", "phrase"])
    print("| statistic | AUC fit | AUC fit typed | null p95 | null p99 | "
          "check FPR@p99 | "
          "check keep@p99 (cogat/bench/phrase) | check FPR@p95 | "
          "check keep@p95 |")
    print("|---|---|---|---|---|---|---|---|---|")
    thresholds, thresholds95 = {}, {}
    for n in names:
        x = stat[n]
        a = auc(x[fit & ~null], x[fit & null])
        a_typed = auc(x[fit & typed], x[fit & null])
        t95, t99 = np.percentile(x[fit & null], [95, 99])
        thresholds[n] = t99
        thresholds95[n] = t95

        def keep(t, mask):
            return np.mean(x[mask] > t)

        chk = ~fit
        per = "/".join(f"{keep(t99, chk & (kinds == k)):.2f}"
                       for k in ("cogat", "bench", "phrase"))
        print(f"| {n} | {a:.3f} | {a_typed:.3f} | {t95:.4f} | {t99:.4f} | "
              f"{keep(t99, chk & null):.3f} | {keep(t99, chk & ~null):.3f} "
              f"({per}) | {keep(t95, chk & null):.3f} | "
              f"{keep(t95, chk & ~null):.3f} |")

    show = ["max", f"top{TOP}", "median", "zmax_mad", f"ztop{TOP}_mad",
            f"ztop{TOP}_sd", "n(zmad>=5)", "old floor: top5%>=0.75"]
    print("\nShort phrases, bench topics and the null's highest "
          f"(gate at the fit null's 99th percentile):\n")
    print("| kind | text | " + " | ".join(show) + " |")
    print("|---|---|" + "---|" * len(show))
    order = [keys.index(t) for t in SHORT]
    order += [i for i in range(len(keys)) if kinds[i] == "bench"]
    order += list(np.argsort(-np.where(null, stat[f"top{TOP}"], -1))[:8])
    for i in order:
        cells = []
        for n in show:
            v = stat[n][i]
            mark = "" if n in ("median", "max", f"top{TOP}") else (
                "+" if v > thresholds[n] else "-")
            cells.append(f"{v:.3f}{mark}" if not float(v).is_integer()
                         else f"{int(v)}{mark}")
        print(f"| {kinds[i]} | {texts[keys[i]][1][:45]} | "
              + " | ".join(cells) + " |")

    g = f"top{TOP}"
    print(f"\nGate {g} > {thresholds95[g]:.4f} (null p95) or > "
          f"{thresholds[g]:.4f} (null p99): studies of similar_study\n")
    print(f"| kind | text | {g} | old floor 0.75 | gate p95 | gate p99 |")
    print("|---|---|---|---|---|---|")
    for i in order:
        n5 = int(np.sum(scores[i] >= np.percentile(
            scores[i][scores[i] > 0], 95)))
        print(f"| {kinds[i]} | {texts[keys[i]][1][:45]} | {stat[g][i]:.4f} "
              f"| {int(stat['old floor: top5%>=0.75'][i])} "
              f"| {n5 if stat[g][i] > thresholds95[g] else 0} "
              f"| {n5 if stat[g][i] > thresholds[g] else 0} |")

    chk = ~fit
    print(f"\ngate {g} >= {args.gate}: check half, null FPR "
          f"{np.mean(stat[g][chk & null] >= args.gate):.3f}; kept "
          + ", ".join(f"{k} {np.mean(stat[g][chk & (kinds == k)] >= args.gate):.2f}"
                      for k in ("cogat", "bench", "phrase"))
          + f"; all in-domain {np.mean(stat[g][chk & ~null] >= args.gate):.3f}"
          f"; whole null {np.mean(stat[g][null] >= args.gate):.3f}")
    mx = stat["max"]
    print(f"\nold floor as a gate (max >= 0.75, some study kept): null "
          f"{np.mean(mx[null] >= 0.75):.3f}, in-domain "
          f"{np.mean(mx[~null] >= 0.75):.3f}")
    words = np.array([len(t.split()) for t in keys])
    for lo, hi in [(1, 4), (5, 9), (10, 25), (26, 10 ** 4)]:
        m = (words >= lo) & (words <= hi)
        print(f"{lo}-{hi} words: null {np.sum(m & null)}, in-domain "
              f"{np.sum(m & ~null)}, median {g} {np.median(stat[g][m & null]):.3f}"
              f" / {np.median(stat[g][m & ~null]):.3f}, AUC "
              f"{auc(stat[g][m & ~null], stat[g][m & null]):.3f}")
    # Per-study centring (CSLS-like): subtract each study's mean score over
    # the fit half of the null, then the top-20 mean.
    valid = np.where(scores > 0, scores, np.nan)
    centred = valid - np.nanmean(valid[fit & null], 0)
    c20 = np.sort(np.nan_to_num(centred, nan=-9), 1)[:, -TOP:].mean(1)
    print(f"centred {g}: AUC on the check half "
          f"{auc(c20[~fit & ~null], c20[~fit & null]):.3f} (raw "
          f"{auc(stat[g][~fit & ~null], stat[g][~fit & null]):.3f})")

    for n in (f"ztop{TOP}_mad", "zmax_mad", "max"):
        miss = [texts[keys[i]][1] for i in np.flatnonzero(typed)
                if stat[n][i] <= thresholds[n]]
        print(f"\ntyped in-domain texts failing {n} > {thresholds[n]:.3f} "
              f"({len(miss)}): " + "; ".join(m[:40] for m in miss[:40]))

    # Hubness: how often each study is in the top 5% of an in-domain text.
    dom = scores[~null]
    cut = np.nanpercentile(np.where(dom > 0, dom, np.nan), 95, axis=1)
    hits = (dom >= cut[:, None]).sum(0)
    share = np.sort(hits)[::-1] / dom.shape[0]
    print(f"\nhubness: share of the {dom.shape[0]} in-domain texts whose top "
          f"5% holds a study: max {share[0]:.2f}, 10th {share[9]:.2f}, "
          f"100th {share[99]:.2f}, median {np.median(share):.3f}; "
          f"studies in >= 50%: {(share >= 0.5).sum()}, "
          f"in >= 30%: {(share >= 0.3).sum()}, in none: {(hits == 0).sum()}")


if __name__ == "__main__":
    main()
