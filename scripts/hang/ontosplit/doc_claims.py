import io
from neurolang.frontend import NeurolangPDL
from neurolang.frontend.tests.test_ontologies_frontend import DEAN_DEPT_UNIT
def mk():
    nl = NeurolangPDL()
    nl.load_ontology(io.StringIO(DEAN_DEPT_UNIT), format="turtle")
    nl.add_tuple_set([('Juan',)], name='Dean')
    nl.add_tuple_set([('Ana', 'Physics')], name='headOf')
    nl.add_tuple_set([('Physics',)], name='Dept')
    nl.add_tuple_set([('Juan',), ('Ana',), ('Eva',)], name='person')
    return nl
for prog in [
  "ans(x) :- headOf(x, y), Unit(y)",
  "heads(x, y) :- headOf(x, y)\nans(x) :- heads(x, y)",
  "heads(x) :- headOf(x, y)\nans(x) :- heads(x)",
  "unit(y) :- Unit(y)\nans(y) :- unit(y)",
  "headsunit(x) :- headOf(x, y), Unit(y)\nans(x) :- person(x), ~headsunit(x)",
  "ans(x, count(y)) :- headOf(x, y)",
  "ans(count(x)) :- headOf(x, y)",
]:
    nl = mk()
    try: print(repr(prog), sorted(nl.execute_datalog_program(prog)))
    except Exception as e: print(repr(prog), "ERR", type(e).__name__, str(e)[:100])
nl = mk()
nl.add_probabilistic_facts_from_tuples([(0.5, 'Juan'), (0.2, 'Ana')], name='funded')
for prog in ["leads(x) :- headOf(x, y), Unit(y)\nans(x, PROB(x)) :- funded(x), leads(x)",
             "ans(x, PROB(x)) :- funded(x), headOf(x, y)"]:
    try: print(repr(prog), sorted(nl.execute_datalog_program(prog)))
    except Exception as e: print(repr(prog), "ERR", type(e).__name__, str(e)[:200])
