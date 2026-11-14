"""Certain answers, with rdflib on cogat.v2.owl, for one individual of each
class in ``sys.argv[1:]``: is it an answer of ``ans(x) :- P(x, y)`` (one of
its superclasses, through rdfs:subClassOf*, has a someValuesFrom restriction
on P), and is it a skos:Concept (subClassOf* skos:Concept)."""
import sys

import rdflib
from rdflib import OWL, RDFS, SKOS, URIRef

g = rdflib.Graph()
g.parse("/Users/bot/neurolang-text2query-bench/neurolang_data/neurosynth/"
        "cogat.v2.owl")
RO = "http://www.obofoundry.org/ro/ro.owl#"
COGAT = "http://www.cognitiveatlas.org/ontology/cogat.owl#"
for name in sys.argv[1:]:
    supers = set(g.transitive_objects(URIRef(COGAT + name), RDFS.subClassOf))
    for p in ("has_part", "part_of"):
        hit = any(
            (r, OWL.onProperty, URIRef(RO + p)) in g
            and g.value(r, OWL.someValuesFrom) is not None
            for c in supers for r in g.objects(c, RDFS.subClassOf)
        )
        print(name, p, "answer" if hit else "no answer")
    print(name, "skos:Concept", SKOS.Concept in supers,
          "named superclasses", sum(isinstance(c, URIRef) for c in supers))
