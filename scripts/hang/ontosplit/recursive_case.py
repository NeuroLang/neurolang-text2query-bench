import io, signal, time
from neurolang.frontend import NeurolangPDL
from neurolang.frontend.tests.test_ontologies_frontend import _turtle
axioms = [('all', 'C1', 'p', 'C2'), ('and', 'C1', 'C3', 'C3'), ('some', 'C0', 'r', 'C1'), ('some', 'C1', 'p', 'C3'), ('sub', 'C0', None, 'C1'), ('sub', 'C2', None, 'C1')]
facts = [('C1', 'c'), ('C3', 'a'), ('C3', 'c'), ('p', 'a', 'b'), ('p', 'a', 'c'), ('r', 'c', 'a')]
nl = NeurolangPDL()
nl.load_ontology(io.StringIO(_turtle(axioms)), format="turtle")
for name in {f[0] for f in facts}:
    nl.add_tuple_set([f[1:] for f in facts if f[0] == name], name=name)
def stop(*_): raise KeyboardInterrupt
signal.signal(signal.SIGALRM, stop)
for q in ["ans(y) :- p(z, y), C3(z), C3(y)", "ans(y) :- C3(z), p(z, y)", "ans(z, y) :- p(z, y), C3(z), C3(y)"]:
    t = time.perf_counter(); signal.alarm(30)
    try: r = set(nl.execute_datalog_program(q))
    except KeyboardInterrupt: r = "TIMEOUT"
    signal.alarm(0); print(q, r, f"{time.perf_counter()-t:.1f}s", flush=True)
