import io, signal, time
from neurolang.frontend import NeurolangPDL
from neurolang.frontend.tests.test_ontologies_frontend import _turtle
axioms = [('all', 'C1', 'r', 'C2'), ('all', 'C2', 'r', 'C3'), ('and', 'C0', 'C1', 'C1'), ('and', 'C0', 'C3', 'C3'), ('and', 'C2', 'C3', 'C3'), ('sub', 'C1', None, 'C2')]
facts = [('C0', 'a'), ('C2', 'c'), ('C3', 'a'), ('p', 'a', 'c'), ('r', 'b', 'a'), ('r', 'b', 'c')]
nl = NeurolangPDL()
nl.load_ontology(io.StringIO(_turtle(axioms)), format="turtle")
for name in {f[0] for f in facts}:
    nl.add_tuple_set([f[1:] for f in facts if f[0] == name], name=name)
for q in ["ans(y) :- C0(y), C3(z)", "ans(z) :- C3(y), C1(z), C2(x)"]:
    t = time.perf_counter(); r = set(nl.execute_datalog_program(q)); print(q, r, f"{time.perf_counter()-t:.1f}s", flush=True)
