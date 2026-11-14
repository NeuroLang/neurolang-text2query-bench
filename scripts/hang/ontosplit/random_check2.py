"""Random Horn ontologies with hasValue and recursive full constraints, and
queries of up to ``MAX_ATOMS`` atoms: NeuroLang's answers must be sound
(a subset of the bounded chase's certain answers); report the incomplete
ones and timeouts. argv: rng seed, cases, max atoms, 'recursive' or 'acyclic'."""
import io
import random
import signal
import sys
import time

from neurolang.frontend import NeurolangPDL
from neurolang.frontend.tests import test_ontologies_frontend as t

seed, cases, max_atoms, mode = (
    int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
)
rng = random.Random(seed)
classes = [f"C{i}" for i in range(4)]
constants = ("a", "b", "c", "v")


def ontology():
    axioms = set()
    for _ in range(rng.randint(2, 6)):
        kind = rng.choice(("sub", "some", "all", "and", "has"))
        if mode == "recursive":
            c, d = rng.choice(classes), rng.choice(classes)
        else:
            c, d = sorted(rng.sample(classes, 2))
            if kind == "some":
                c, d = rng.choice(classes), rng.choice(classes)
        p = rng.choice(("p", "r"))
        if kind == "and":
            c, p = (rng.sample(classes, 2) if mode == "recursive"
                    else sorted(rng.sample(classes, 2)))
        if kind == "has":
            d = "v"
        axioms.add((kind, c, None if kind == "sub" else p, d))
    return sorted(axioms, key=str)


def turtle(axioms):
    text = t._turtle([a for a in axioms if a[0] != "has"])
    for _, c, p, v in (a for a in axioms if a[0] == "has"):
        text += (f"\n:{c} a owl:Class ; rdfs:subClassOf [ a owl:Restriction"
                 f" ; owl:onProperty :{p} ; owl:hasValue :{v} ] .")
    return text


def certain(axioms, facts, head, body):
    return t._certain_answers(axioms, facts, head, body)


def stop(*_):
    raise KeyboardInterrupt


signal.signal(signal.SIGALRM, stop)
counts = {"ok": 0, "incomplete": 0, "unsound": 0, "timeout": 0, "error": 0,
          "oracle": 0}
for case in range(cases):
    axioms = ontology()
    facts = {(rng.choice(classes), rng.choice(constants[:3]))
             for _ in range(rng.randint(1, 3))}
    facts |= {(rng.choice(("p", "r")),) + tuple(rng.sample(constants[:3], 2))
              for _ in range(rng.randint(0, 3))}
    predicates = {f[0] for f in facts} | {
        q for k, _, p, d in axioms
        for q in ((d,) if k in ("sub", "all") else (p,) if k == "has"
                  else (p, d))
    } | {"r" for k, *_ in axioms if k == "and"}
    nl = NeurolangPDL()
    nl.load_ontology(io.StringIO(turtle(axioms)), format="turtle")
    for name in {f[0] for f in facts}:
        nl.add_tuple_set([f[1:] for f in facts if f[0] == name], name=name)
    for _ in range(3):
        body = []
        for _ in range(rng.randint(1, max_atoms)):
            name = rng.choice(sorted(predicates))
            arity = 2 if name in ("p", "r") else 1
            body.append((name,) + tuple(rng.choices("xyzw", k=arity)))
        variables = sorted({v for atom in body for v in atom[1:]})
        head = rng.sample(variables, rng.randint(1, len(variables)))
        program = "ans({}) :- {}".format(", ".join(head), ", ".join(
            f"{a[0]}({', '.join(a[1:])})" for a in body))
        signal.alarm(30)
        try:
            expected = certain(axioms, facts, head, body)
        except KeyboardInterrupt:
            counts["oracle"] += 1
            print("case", case, "oracle timeout", axioms, sorted(facts),
                  program, flush=True)
            continue
        finally:
            signal.alarm(0)
        start = time.perf_counter()
        signal.alarm(10)
        try:
            res = set(nl.execute_datalog_program(program))
            kind = ("ok" if res == expected else
                    "incomplete" if res <= expected else "unsound")
        except KeyboardInterrupt:
            kind = "timeout"
        except Exception as e:
            kind, res = "error", type(e).__name__
        signal.alarm(0)
        counts[kind] += 1
        if kind != "ok":
            print("case", case, kind, f"{time.perf_counter() - start:.1f}s", axioms,
                  sorted(facts), program, "got", res, "want", expected,
                  flush=True)
print(counts)
