"""A domain fact on a named value, derived through an unnamed one, then a
subclass axiom on it: Dean ⊑ ∃headOf.Dept, domain(headOf) = Manager,
Manager ⊑ Person; and a transitive chain through two unnamed values."""
import io

from neurolang.frontend import NeurolangPDL
from neurolang.frontend.tests.test_ontologies_frontend import DEAN_DEPT_UNIT

nl = NeurolangPDL()
nl.load_ontology(io.StringIO(
    DEAN_DEPT_UNIT + ":headOf rdfs:domain :Manager . "
    ":Manager a owl:Class ; rdfs:subClassOf :Person ."), format="turtle")
nl.add_tuple_set([("Juan",)], name="Dean")
for q in ["ans(x) :- Manager(x)", "ans(x) :- Person(x)"]:
    print(q, sorted(nl.execute_datalog_program(q)))
nl = NeurolangPDL()
nl.load_ontology(io.StringIO("""
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix : <http://ex.org/> .
:A a owl:Class ; rdfs:subClassOf [ a owl:Restriction ; owl:onProperty :p ;
    owl:someValuesFrom :B ] .
:B a owl:Class ; rdfs:subClassOf [ a owl:Restriction ; owl:onProperty :p ;
    owl:someValuesFrom :C ] .
:p a owl:TransitiveProperty .
"""), format="turtle")
nl.add_tuple_set([("a",)], name="A")
for q in ["ans(x) :- p(x, y), C(y)", "ans(x) :- p(x, y), B(y)"]:
    print(q, sorted(nl.execute_datalog_program(q)))

# Two levels: Manager ⊑ ∃runs.Team, domain(runs) = Lead; Manager has facts.
nl = NeurolangPDL()
nl.load_ontology(io.StringIO(
    DEAN_DEPT_UNIT + ":headOf rdfs:domain :Manager . "
    ":Manager a owl:Class ; rdfs:subClassOf :Person , [ a owl:Restriction ;"
    " owl:onProperty :runs ; owl:someValuesFrom :Team ] . "
    ":runs rdfs:domain :Lead ."), format="turtle")
nl.add_tuple_set([("Juan",)], name="Dean")
nl.add_tuple_set([("Eva",)], name="Manager")
for q in ["ans(x) :- Manager(x)", "ans(x) :- Person(x)",
          "ans(x) :- Lead(x)", "ans(x) :- runs(x, y)"]:
    print(q, sorted(nl.execute_datalog_program(q)))
# allValuesFrom through an inverse: Dean ⊑ ∃headOf.Dept, headOf inverse of
# headedBy, Dept ⊑ ∀headedBy.Boss: Boss('Juan').
nl = NeurolangPDL()
nl.load_ontology(io.StringIO(
    DEAN_DEPT_UNIT + ":headedBy owl:inverseOf :headOf . "
    ":Dept rdfs:subClassOf [ a owl:Restriction ; owl:onProperty :headedBy ;"
    " owl:allValuesFrom :Boss ] ."), format="turtle")
nl.add_tuple_set([("Juan",)], name="Dean")
for q in ["ans(x) :- Boss(x)"]:
    print("allValuesFrom via inverse", q, sorted(nl.execute_datalog_program(q)))
