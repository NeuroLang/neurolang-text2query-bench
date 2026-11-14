"""rdflib closure for one instance of CAO_01600 in cogat.v2.owl: its named
superclasses, the someValuesFrom properties they restrict, and the classes
these properties' rdfs:domain (and their superclasses) give the instance."""
import rdflib
from rdflib.namespace import OWL, RDFS

g = rdflib.Graph()
g.parse("/Users/bot/neurolang-text2query-bench/neurolang_data/neurosynth/"
        "cogat.v2.owl", format="xml")
COGAT = "http://www.cognitiveatlas.org/ontology/cogat.owl#"


def supers(c):
    seen, todo = set(), [c]
    while todo:
        for s in g.objects(todo.pop(), RDFS.subClassOf):
            if s not in seen:
                seen.add(s)
                todo.append(s)
    return seen


up = supers(rdflib.URIRef(COGAT + "CAO_01600")) | {
    rdflib.URIRef(COGAT + "CAO_01600")}
named = {c for c in up if isinstance(c, rdflib.URIRef)}
props = {g.value(r, OWL.onProperty) for r in up
         if isinstance(r, rdflib.BNode) and g.value(r, OWL.someValuesFrom)}
print("named superclasses", len(named))
print("someValuesFrom properties", sorted(map(str, props)))
domains = {d for p in props for d in g.objects(p, RDFS.domain)}
print("domains", sorted(map(str, domains)))
print("domain classes and their superclasses",
      sorted(map(str, {x for d in domains for x in supers(d) | {d}
                       if isinstance(x, rdflib.URIRef)})))
print("already named superclasses of the instance:",
      sorted(str(d) for d in domains if d in named))
