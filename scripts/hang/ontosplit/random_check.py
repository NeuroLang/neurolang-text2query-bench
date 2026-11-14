"""Random Horn ontologies, data and queries: NeuroLang vs the bounded chase
with labelled nulls of the NeuroLang test module; argv: rng seed, cases.
Prints the queries whose answers differ or that take more than 3 s."""
import io, random, signal, sys, time
from neurolang.frontend import NeurolangPDL
from neurolang.frontend.tests.test_ontologies_frontend import (
    _random_horn_ontology, _turtle, _certain_answers)

def stop(*_): raise KeyboardInterrupt
signal.signal(signal.SIGALRM, stop)
rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
constants = ("a", "b", "c")
bad = 0
for case in range(int(sys.argv[2]) if len(sys.argv) > 2 else 40):
    classes, axioms = _random_horn_ontology(rng)
    facts = {(rng.choice(classes), rng.choice(constants)) for _ in range(rng.randint(1, 3))}
    facts |= {(rng.choice(("p", "r")),) + tuple(rng.sample(constants, 2)) for _ in range(rng.randint(0, 3))}
    predicates = {f[0] for f in facts} | {q for k, _, p, d in axioms for q in ((d,) if k in ("sub", "all") else (p, d))} | {"r" for k, *_ in axioms if k == "and"}
    nl = NeurolangPDL()
    nl.load_ontology(io.StringIO(_turtle(axioms)), format="turtle")
    for name in {f[0] for f in facts}:
        nl.add_tuple_set([f[1:] for f in facts if f[0] == name], name=name)
    for _ in range(3):
        body = []
        for _ in range(rng.randint(1, 3)):
            name = rng.choice(sorted(predicates))
            arity = 2 if name in ("p", "r") else 1
            body.append((name,) + tuple(rng.choices("xyz", k=arity)))
        variables = sorted({v for atom in body for v in atom[1:]})
        head = rng.sample(variables, rng.randint(1, len(variables)))
        program = "ans({}) :- {}".format(", ".join(head), ", ".join(f"{a[0]}({', '.join(a[1:])})" for a in body))
        signal.alarm(30)
        try:
            expected = _certain_answers(axioms, facts, head, body)
        except KeyboardInterrupt:
            print(case, "oracle timeout", axioms, sorted(facts), program,
                  flush=True)
            continue
        finally:
            signal.alarm(0)
        t = time.perf_counter(); signal.alarm(20)
        try:
            res = set(nl.execute_datalog_program(program))
        except KeyboardInterrupt:
            res = "TIMEOUT"
        except Exception as e:
            res = f"ERR {type(e).__name__}"
        signal.alarm(0)
        dt = time.perf_counter() - t
        if res != expected or dt > 3:
            bad += 1
            print(case, f"{dt:.1f}s", axioms, sorted(facts), program, "got", res, "want", expected, flush=True)
print("bad", bad)
