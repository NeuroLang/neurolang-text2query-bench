"""A predicate the ontology only constrains (a someValuesFrom restriction,
no rule, no fact), queried alone: IndexError in magic sets on master."""
import io
import traceback

from neurolang.frontend import NeurolangPDL

OWL = '''<?xml version="1.0"?>
<rdf:RDF xmlns="http://www.w3.org/2002/07/owl#"
    xmlns:owl="http://www.w3.org/2002/07/owl#"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">
    <Ontology/>
    <owl:Class rdf:ID="Dean">
        <rdfs:subClassOf>
            <owl:Class>
                <owl:intersectionOf rdf:parseType="Collection">
                    <owl:Class rdf:about="#Person" />
                    <owl:Restriction>
                        <owl:onProperty rdf:resource="#headOf" />
                        <owl:someValuesFrom>
                            <owl:Class rdf:about="#College" />
                        </owl:someValuesFrom>
                    </owl:Restriction>
                </owl:intersectionOf>
            </owl:Class>
        </rdfs:subClassOf>
    </owl:Class>
</rdf:RDF>'''

nl = NeurolangPDL()
nl.load_ontology(io.StringIO(OWL))
nl.add_tuple_set([("Juan",), ("Manuel",)], name="Dean")
print(nl.symbol_table[nl.new_symbol(name="headOf").expression])
for q in [
    "ans(a) :- headOf(a, b)",
    "ans(a, b) :- headOf(a, b)",
    "ans(a) :- headOf(a, b), College(b)",
    "ans(a) :- Dean(a), headOf(a, b)",
]:
    try:
        print(q, "->", set(nl.execute_datalog_program(q)))
    except Exception as e:
        traceback.print_exc(limit=-1)

with nl.scope as e:
    e.answer[e.a] = e.headOf[e.a, e.b] & e.College[e.b]
    print("solve_all headOf & College ->", set(nl.solve_all()["answer"]))
with nl.scope as e:
    e.answer[e.a] = e.headOf[e.a, e.b]
    print("solve_all headOf ->", set(nl.solve_all()["answer"]))
with nl.scope as e:
    print("query headOf & College ->", set(nl.query((e.a,), e.headOf[e.a, e.b] & e.College[e.b])))
