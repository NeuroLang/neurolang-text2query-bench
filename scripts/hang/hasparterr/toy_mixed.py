"""A predicate with an ontology constraint and a rule of its own."""
import runpy
import sys
import traceback

sys.argv = ["toy"]
nl = runpy.run_path(sys.path[0] + "/toy.py")["nl"]
nl.add_tuple_set([("Ana", "College C")], name="leads")
nl.execute_datalog_program("headOf(x, y) :- leads(x, y)")
for q in ["ans(a) :- headOf(a, b)", "ans(a, b) :- headOf(a, b)",
          "ans(a) :- headOf(a, b), College(b)"]:
    try:
        print("MIXED", q, "->", set(nl.execute_datalog_program(q)))
    except Exception:
        traceback.print_exc(limit=-1)
with nl.scope as e:
    e.answer[e.a] = e.headOf[e.a, e.b]
    print("MIXED solve_all headOf ->", set(nl.solve_all()["answer"]))
