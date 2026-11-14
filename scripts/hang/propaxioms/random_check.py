"""Random Horn ontologies (non-recursive class axioms, as in #1238's test)
with 1 to 3 property axioms, random data and queries of up to 3 atoms:
NeuroLang vs the bounded chase with labelled nulls of the test module.
argv: rng seed, cases, kinds ('all' or a comma list, e.g.
'subp,eqp,inv,dom,rng,sym'). Prints the cases that are not 'ok' and the
counts of ok / incomplete / unsound / timeout (10 s) / error; every query
also prints a line 'case n kind time'. The bounded chase is run at depths 3
and 5, and a query whose two answers differ is counted as 'depth'."""
import io
import random
import signal
import sys
import time
import traceback

from neurolang.frontend import NeurolangPDL
from neurolang.frontend.tests import test_ontologies_frontend as t

seed, cases, kinds = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
# argv[4], optional: the only cases to run, as "3,17".
only = (
    {int(c) for c in sys.argv[4].split(",") if c}
    if len(sys.argv) > 4 and sys.argv[4] != "-v" else None
)
kinds = None if kinds == "all" else kinds.split(",")
rng = random.Random(seed)
constants = ("a", "b", "c")


def stop(*_):
    raise KeyboardInterrupt


signal.signal(signal.SIGALRM, stop)
counts = {"ok": 0, "incomplete": 0, "unsound": 0, "timeout": 0, "error": 0,
          "depth": 0, "oracle": 0}
for case in range(cases):
    classes, axioms = t._random_horn_ontology(rng)
    axioms = sorted(
        set(axioms) | t._random_property_axioms(rng, classes, kinds=kinds),
        key=str,
    )
    facts = {(rng.choice(classes), rng.choice(constants))
             for _ in range(rng.randint(1, 3))}
    facts |= {(rng.choice(("p", "r")),) + tuple(rng.sample(constants, 2))
              for _ in range(rng.randint(0, 3))}
    predicates = {f[0] for f in facts} | t._derived_predicates(axioms)
    skip = only is not None and case not in only
    if not skip:
        nl = NeurolangPDL()
        nl.load_ontology(io.StringIO(t._turtle(axioms)), format="turtle")
        for name in {f[0] for f in facts}:
            nl.add_tuple_set(
                [f[1:] for f in facts if f[0] == name], name=name
            )
    for _ in range(3):
        body = []
        for _ in range(rng.randint(1, 3)):
            name = rng.choice(sorted(predicates))
            arity = 2 if name in ("p", "r") else 1
            body.append((name,) + tuple(rng.choices("xyz", k=arity)))
        variables = sorted({v for atom in body for v in atom[1:]})
        head = rng.sample(variables, rng.randint(1, len(variables)))
        program = "ans({}) :- {}".format(", ".join(head), ", ".join(
            f"{a[0]}({', '.join(a[1:])})" for a in body))
        if skip:
            continue
        signal.alarm(30)
        try:
            expected = t._certain_answers(axioms, facts, head, body, depth=5)
            shallow = t._certain_answers(axioms, facts, head, body, depth=3)
        except KeyboardInterrupt:
            counts["oracle"] += 1
            print("case", case, "oracle timeout", program, flush=True)
            continue
        signal.alarm(0)
        if shallow != expected:
            counts["depth"] += 1
            print("case", case, "depth", program, flush=True)
        start = time.perf_counter()
        signal.alarm(10)
        try:
            res = {tuple(r) for r in nl.execute_datalog_program(program)}
            kind = ("ok" if res == expected else
                    "incomplete" if res <= expected else "unsound")
        except KeyboardInterrupt:
            kind = "timeout"
        except Exception as e:
            kind, res = "error", f"{type(e).__name__}: {e}"[:300]
            if "-v" in sys.argv:
                traceback.print_exc()
        signal.alarm(0)
        counts[kind] += 1
        print("case", case, kind, f"{time.perf_counter() - start:.1f}s",
              flush=True)
        if kind != "ok":
            print(case, kind, f"{time.perf_counter() - start:.1f}s", axioms,
                  sorted(facts), program, "got", res, "want", expected,
                  flush=True)
print(counts, flush=True)
