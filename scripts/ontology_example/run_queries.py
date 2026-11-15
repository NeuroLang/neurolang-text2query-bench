"""The queries of the Stroop / response inhibition example of NeuroLang's
doc/ontologies.rst ("Open and closed worlds on the Cognitive Atlas") on
the neurosynth engine: for each, the number of rows, the first rows (with
the study titles for study answers) and the time.

    source scripts/nsv3c_env.sh   # with NL_TREE on the worktree under test
    .venv-dsparity/bin/python scripts/ontology_example/run_queries.py \
        TIMEOUT [NAME...]

TIMEOUT is in seconds per query; NAMEs select queries (default: all);
``closed:NAME`` runs NAME without the constraints, after the others. With
DUMP=SECONDS, the stacks are dumped once, SECONDS after the start.
"""
import faulthandler
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import neurolang
from text2query_bench.engine import build_engine

COGAT = "http://www.cognitiveatlas.org/ontology/cogat.owl#"
COGPO = "http://www.cogpo.org/ontologies/working/CogPOver2011.owl#"
# The programs as doc/ontologies.rst shows them, comments included.
STROOP = ("% cogat:CAO_00872 (Stroop task), cogat:CAO_00487 (response "
          "inhibition)\ncogat:CAO_00872(s) :- mentions(s, 'stroop task')\n")
STOP = ("% cogat:CAO_00871 (stop signal task), cogat:CAO_00487 (response "
        "inhibition)\ncogat:CAO_00871(s) :- mentions(s, 'stop signal')\n")
INHIBITION = ("inhibition_study(s) :- cogpo:has_contrast(s, x), "
              "cogat:measures(x, c), cogat:CAO_00487(c)\n")
CLASS_LEVEL = (
    "has_contrast_class(t, k) :- rdfs:subClassOf(t, r), "
    f"owl:onProperty(r, <{COGPO}has_contrast>), owl:someValuesFrom(r, k)\n"
    "inhibition(c) :- cogat_term(c, 'response inhibition')\n"
    "inhibition(c) :- cogat_subclass_of(c, d), "
    "cogat_term(d, 'response inhibition')\n"
    "inhibition_task(t, c) :- has_contrast_class(t, k), "
    "cogat_measures(k, c), inhibition(c)\n"
)
QUERIES = {
    # closed world, on the data alone
    "mentions_stroop": "ans(s) :- mentions(s, 'stroop task')",
    "mentions_stop": "ans(s) :- mentions(s, 'stop signal')",
    # the instances the rule gives the class
    "stroop_instances": STROOP + "ans(s) :- cogat:CAO_00872(s)",
    # open world
    "inhibition_study": STROOP + INHIBITION + "ans(s) :- inhibition_study(s)",
    "inhibition_with_concept": STROOP + "ans(s, c) :- cogpo:has_contrast(s, x),"
    " cogat:measures(x, c), cogat:CAO_00487(c)",
    "p_active_given_inhibition": STROOP + INHIBITION
    + "p_active_given_inhibition(i, j, k, PROB) :- (activated(i, j, k, s) & "
    "selected_study(s)) // (inhibition_study(s) & selected_study(s))\n"
    "ans(i, j, k, p) :- p_active_given_inhibition(i, j, k, p)",
    "stop_inhibition_study": STOP + INHIBITION
    + "ans(s) :- inhibition_study(s)",
    "stop_instances": STOP + "ans(s) :- cogat:CAO_00871(s)",
    # closed world at the class level
    "class_inhibition_tasks": CLASS_LEVEL
    + "ans(t, n, m) :- inhibition_task(t, c), cogat_term(t, n), "
    "cogat_term(c, m)",
    "class_inhibition_studies": CLASS_LEVEL
    + "ans(s, n) :- inhibition_task(t, c), cogat_term(t, n), mentions(s, n)",
    "class_inhibition_terms": CLASS_LEVEL
    + "ans(n, count(s)) :- inhibition_task(t, c), cogat_term(t, n), "
    "mentions(s, n)",
    # the conditional of p_active_given_inhibition, on the data alone
    "p_active_given_stroop": "p_active_given_stroop(i, j, k, PROB) :- "
    "(activated(i, j, k, s) & selected_study(s)) // "
    "(mentions(s, 'stroop task') & selected_study(s))\n"
    "ans(i, j, k, p) :- p_active_given_stroop(i, j, k, p)",
    # the prefixes of the open-world query
    "has_contrast": STROOP + "ans(s) :- cogpo:has_contrast(s, x)",
    "has_contrast_01515": STROOP + "ans(s) :- cogpo:has_contrast(s, x), "
    "cogat:CAO_01515(x)",
    "study_count": "ans(count(s)) :- study(s)",
    "has_contrast_measures": STROOP + "ans(s) :- cogpo:has_contrast(s, x), "
    "cogat:measures(x, c)",
}
# the same queries without the constraints of the ontology: plain Datalog
CLOSED = ["stroop_instances", "has_contrast", "has_contrast_01515",
          "inhibition_study", "inhibition_with_concept",
          "p_active_given_inhibition"]


def stop(*_):
    raise KeyboardInterrupt


signal.signal(signal.SIGALRM, stop)
if os.environ.get("DUMP"):
    # where a query that does not end spends its time
    faulthandler.dump_traceback_later(int(os.environ["DUMP"]), exit=False)
tree = Path(neurolang.__file__).parents[3]
print("neurolang from", neurolang.__file__, flush=True)
print("commit", subprocess.run(
    ["git", "-C", str(tree), "log", "-1", "--format=%H %cI %s"],
    capture_output=True, text=True).stdout.strip(), flush=True)
t = time.perf_counter()
nl = build_engine(
    "neurosynth", Path("/Users/bot/neurolang-text2query-bench/neurolang_data")
)
print(f"build {time.perf_counter() - t:.1f}s", flush=True)
titles = dict(nl.execute_datalog_program(
    "ans(s, t) :- study_title(s, t)").as_pandas_dataframe().itertuples(
        index=False, name=None))


def show(rows):
    rows = sorted(rows, key=lambda r: (-r[-1],) if isinstance(
        r[-1], float) else r)
    for r in rows[:8]:
        extra = f"  | {titles.get(r[0], '')[:90]}" if r and r[0] in titles \
            else ""
        print("    ", r, extra, flush=True)


def regions(rows, top=6):
    """The Destrieux regions with the highest p, each with the MNI (mm)
    of its voxel of highest p, and the number of voxels with p > 0."""
    import numpy as np
    from neurolang_apps.utils.engine_registry import atlas_label_values
    names = {v: n for n, vs in atlas_label_values(nl, "destrieux").items()
             for v in vs}
    data = np.asarray(nl.grids["destrieux"].dataobj)
    affine = nl.template.affine
    best = {}
    positive = 0
    for i, j, k, p in rows:
        positive += p > 0
        label = names.get(int(data[i, j, k]))
        if label is not None and p > best.get(label, (0,))[0]:
            best[label] = (p, (i, j, k))
    print("    voxels with p > 0:", positive, "max p:",
          max(r[-1] for r in rows), flush=True)
    for label, (p, ijk) in sorted(best.items(), key=lambda x: -x[1][0])[:top]:
        mm = tuple(round(float(x)) for x in affine @ (*ijk, 1))[:3]
        print(f"    {label}: p={p:.3f} at {ijk} = MNI {mm}", flush=True)


def timed(name, program):
    t = time.perf_counter()
    signal.alarm(int(sys.argv[1]))
    try:
        with nl.scope:
            rows = {tuple(r) for r in nl.execute_datalog_program(program)}
        out = f"{len(rows)} rows"
    except KeyboardInterrupt:
        rows, out = (), "stopped"
    except Exception as e:
        rows, out = (), f"{type(e).__name__}: {e}"[:400]
    finally:
        signal.alarm(0)
    print(f"{name}: {time.perf_counter() - t:.1f}s {out}", flush=True)
    show(rows)
    if rows and name.endswith(("p_active_given_inhibition",
                               "p_active_given_stroop")):
        regions(rows)


selected = sys.argv[2:] or list(QUERIES) + [f"closed:{n}" for n in CLOSED]
for name in selected:
    if name.startswith("closed:"):
        continue
    print("\n#", name, "\n", QUERIES[name], flush=True)
    timed(name, QUERIES[name])
closed = [n[len("closed:"):] for n in selected if n.startswith("closed:")]
if closed:
    # Plain Datalog: the same facts and rules, without the constraints.
    from nl_expr.expressions import Symbol
    del nl.program_ir.symbol_table[Symbol("__constraints__")]
    nl.program_ir.categorized_constraints = {}
    print("\nwithout constraints:", len(nl.program_ir.get_constraints()))
    # The Atlas has no fact of these (verify_atlas.py): empty relations.
    import pandas as pd
    for pred, arity in [("cogpo:has_contrast", 2), ("cogat:measures", 2),
                        ("cogat:CAO_00487", 1), ("cogat:CAO_01515", 1)]:
        nl.add_tuple_set(pd.DataFrame(columns=range(arity)), name=pred)
    for name in closed:
        print("\n# closed:", name, "\n", QUERIES[name], flush=True)
        timed("closed:" + name, QUERIES[name])
