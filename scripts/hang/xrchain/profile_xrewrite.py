"""Profile XRewrite on an open-world Cognitive Atlas query (neurosynth
engine, Stroop instance rule): rewritings built / dead / duplicate /
explored, the constraints that fire, and the time in the rewriting vs the
rest of the query.

    source scripts/nsv3c_env.sh  # NL_TREE=worktree under test
    .venv-dsparity/bin/python scripts/hang/xrchain/profile_xrewrite.py \
        TIMEOUT QUERY_NAME
"""
import collections
import cProfile
import os
import pstats
import signal
import sys
import time
from pathlib import Path

from nl_core.datalog import ontologies_rewriter as orw
from text2query_bench.engine import build_engine

STROOP = "cogat:CAO_00872(s) :- mentions(s, 'stroop task')\n"
STOP = "cogat:CAO_00871(s) :- mentions(s, 'stop signal')\n"
INHIBITION = ("inhibition_study(s) :- cogpo:has_contrast(s, x), "
              "cogat:measures(x, c), cogat:CAO_00487(c)\n")
QUERIES = {
    "has_contrast": STROOP + "ans(s) :- cogpo:has_contrast(s, x)",
    "two": STROOP + "ans(s) :- cogpo:has_contrast(s, x), "
    "cogat:measures(x, c)",
    "three": STROOP + INHIBITION + "ans(s) :- inhibition_study(s)",
    "three_c": STROOP + "ans(s, c) :- cogpo:has_contrast(s, x), "
    "cogat:measures(x, c), cogat:CAO_00487(c)",
    "stop": STOP + INHIBITION + "ans(s) :- inhibition_study(s)",
}

stats = collections.Counter()
fired = collections.Counter()
T = {"xrewrite": 0.0}

orig_step = orw.OntologyRewriter.rewriting_step
orig_dead = orw.OntologyRewriter._dead
orig_x = orw.OntologyRewriter.Xrewrite
orig_new = orw.OntologyRewriter._is_new_rewriting


def step(self, q0, sigma, rc):
    out = orig_step(self, q0, sigma, rc)
    stats["built"] += len(out)
    if out:
        kind = "exist" if orw._existential_variables(sigma) else "full"
        fired[(kind, sigma.consequent.functor.name.split("#")[-1][-20:])] += len(out)
    return out


def dead(self, q):
    d = orig_dead(self, q)
    stats["dead"] += d
    return d


def new(self, q, a, b):
    n = orig_new(self, q, a, b)
    stats["dup"] += not n
    return n


def xrewrite(self):
    t = time.perf_counter()
    try:
        r = orig_x(self)
        stats["explored"] += len(r)
        return r
    finally:
        T["xrewrite"] += time.perf_counter() - t


orig_rel = orw.OntologyRewriter._get_related_sigmas
seen = []


def related(self, q0, c):
    seen.append(q0)
    r = orig_rel(self, q0, c)
    stats["sigmas_tried"] += len(r)
    return r


orw.OntologyRewriter._get_related_sigmas = related
orw.OntologyRewriter.rewriting_step = step
orw.OntologyRewriter._dead = dead
orw.OntologyRewriter.Xrewrite = xrewrite
orw.OntologyRewriter._is_new_rewriting = new


def short(f):
    n = getattr(f, "name", None)
    if n is None:
        return str(f)[:10]
    return "aux" if n.startswith("fresh") else n.split("#")[-1][-12:]


def stop(*_):
    raise KeyboardInterrupt


signal.signal(signal.SIGALRM, stop)
nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
for name in sys.argv[2:]:
    stats.clear(), fired.clear()
    T["xrewrite"] = 0.0
    t = time.perf_counter()
    signal.alarm(int(sys.argv[1]))
    profile = cProfile.Profile() if os.environ.get("CPROFILE") else None
    if profile:
        profile.enable()
    try:
        with nl.scope:
            rows = {tuple(r) for r in nl.execute_datalog_program(
                QUERIES[name])}
        out = f"{len(rows)} rows"
    except KeyboardInterrupt:
        out = "stopped"
    finally:
        signal.alarm(0)
        if profile:
            profile.disable()
            pstats.Stats(profile).sort_stats(os.environ.get("SORT", "cumulative")).print_stats(os.environ["CPROFILE"], 30)
    total = time.perf_counter() - t
    print(f"{name}: {total:.1f}s {out}; xrewrite {T['xrewrite']:.1f}s;",
          dict(stats), flush=True)
    shapes = collections.Counter(
        tuple(sorted(short(getattr(a, "functor", None)) for a in getattr(q.antecedent, "formulas",
                                      (q.antecedent,))))
        for q in seen)
    print("   explored", len(seen), shapes.most_common(10))
    seen.clear()
    for k, v in fired.most_common(8):
        print("   fired", k, v)
