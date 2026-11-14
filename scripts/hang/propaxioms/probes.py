"""Small property-axiom ontologies over Dean ⊑ ∃headOf.Dept: each query's
answers, time, or 'stopped' after 15 s."""
import io
import signal
import time

from neurolang.frontend import NeurolangPDL

HEAD = """@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix : <http://ex.org/> .
:Dean a owl:Class ; rdfs:subClassOf [
    a owl:Restriction ; owl:onProperty :headOf ; owl:someValuesFrom :Dept
] .
"""
CASES = [
    (":headOf rdfs:subPropertyOf :worksFor . :worksFor rdfs:range :Org .",
     ["ans(x) :- worksFor(x, y), Org(y)", "ans(y) :- Org(y)"]),
    (":headOf rdfs:domain :Manager .", ["ans(x) :- Manager(x)"]),
    (":headOf owl:inverseOf :headedBy .",
     ["ans(x) :- headedBy(y, x)", "ans(y) :- headedBy(x, y)"]),
    (":headedBy owl:inverseOf :headOf . :headedBy rdfs:range :Boss .",
     ["ans(x) :- Boss(x)"]),
    (":headOf a owl:SymmetricProperty .",
     ["ans(x) :- headOf(y, x)", "ans(x) :- headOf(x, y)"]),
    (":headOf a owl:SymmetricProperty ; rdfs:range :R .",
     ["ans(x) :- R(x)"]),
    (":headOf a owl:TransitiveProperty .",
     ["ans(x) :- headOf(x, y)", "ans(x, y) :- headOf(x, y)"]),
    (":headOf a owl:TransitiveProperty, owl:SymmetricProperty .",
     ["ans(x) :- headOf(x, x)"]),
    (":headOf owl:equivalentProperty :leads .",
     ["ans(x) :- leads(x, y)"]),
]


def stop(*_):
    raise KeyboardInterrupt


signal.signal(signal.SIGALRM, stop)
for axioms, queries in CASES:
    nl = NeurolangPDL()
    nl.load_ontology(io.StringIO(HEAD + axioms), format="turtle")
    nl.add_tuple_set([("Juan",)], name="Dean")
    nl.add_tuple_set([("Ana", "Physics"), ("Physics", "Lab")], name="headOf")
    for q in queries:
        t = time.perf_counter()
        signal.alarm(15)
        try:
            out = sorted(nl.execute_datalog_program(q))
        except KeyboardInterrupt:
            out = "stopped"
        except Exception as e:
            out = f"{type(e).__name__}: {e}"[:200]
        signal.alarm(0)
        print(f"{time.perf_counter() - t:5.1f}s", axioms, "|", q, "->", out,
              flush=True)
