"""Cross-check, with rdflib on cogat.v2.owl, the answers of
``ans(x) :- P(x, y)`` for P in ro:has_part, ro:part_of: asserted P triples,
and individuals typed (through rdfs:subClassOf*) with a class that has a
someValuesFrom restriction on P; plus the class-level restriction count."""
import sys

import rdflib
from rdflib import OWL, RDF, RDFS, URIRef

g = rdflib.Graph()
g.parse(sys.argv[1] if len(sys.argv) > 1 else
        "/Users/bot/neurolang-text2query-bench/neurolang_data/neurosynth/"
        "cogat.v2.owl")
RO = "http://www.obofoundry.org/ro/ro.owl#"
classes = set(g.subjects(RDF.type, OWL.Class))
individuals = {
    (s, o) for s, o in g.subject_objects(RDF.type)
    if o in classes
}
print("classes", len(classes), "individuals typed with a class",
      len(individuals))
for name in ("has_part", "part_of"):
    p = URIRef(RO + name)
    triples = set(g.subject_objects(p))
    restricted = {
        c for c, r in g.subject_objects(RDFS.subClassOf)
        if (r, OWL.onProperty, p) in g
        and g.value(r, OWL.someValuesFrom) is not None
    }
    rows = {
        (c, d) for c, r in g.subject_objects(RDFS.subClassOf)
        if (r, OWL.onProperty, p) in g
        for d in g.objects(r, OWL.someValuesFrom)
    }
    print(name, "(class, someValuesFrom class) rows", len(rows))
    sub = set()
    for c in restricted:
        sub |= set(g.transitive_subjects(RDFS.subClassOf, c))
    typed = {s for s, o in individuals if o in sub}
    print(name, "triples", len(triples), "restricted classes",
          len(restricted), "with subclasses", len(sub),
          "certain answers", len({s for s, _ in triples} | typed))
