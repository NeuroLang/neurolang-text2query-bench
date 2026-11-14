"""With rdflib on cogat.v2.owl: each task with a contrast that measures
response inhibition (CAO_00487) or a named subclass of it, the contrast and
the concept it measures."""
import sys
from rdflib import Graph, RDFS, OWL, URIRef

CA = "http://www.cognitiveatlas.org/ontology/cogat.owl#"
CO = "http://www.cogpo.org/ontologies/working/CogPOver2011.owl#"
g = Graph().parse(sys.argv[1] if len(sys.argv) > 1 else
                  "neurolang_data/neurosynth/cogat.v2.owl")


def some(c, prop):
    for r in g.objects(c, RDFS.subClassOf):
        if g.value(r, OWL.onProperty) == URIRef(prop):
            v = g.value(r, OWL.someValuesFrom)
            if v is not None:
                yield v


def label(x):
    return str(g.value(x, RDFS.label)).strip()


ri = URIRef(CA + "CAO_00487")
forms = {ri} | set(g.transitive_subjects(RDFS.subClassOf, ri))
for t in sorted(set(g.subjects(RDFS.subClassOf, None))):
    for k in some(t, CO + "has_contrast"):
        for c in some(k, CA + "measures"):
            if c in forms:
                print(f"{t.split('#')[1]} ({label(t)}) has_contrast "
                      f"{k.split('#')[1]} ({label(k)}) measures "
                      f"{c.split('#')[1]} ({label(c)})")
