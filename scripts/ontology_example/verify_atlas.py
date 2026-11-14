"""Check, with rdflib on cogat.v2.owl, the Cognitive Atlas facts the Stroop
example of doc/ontologies.rst relies on: class labels, the restrictions on
the Stroop task, its contrasts and what they measure, the subclasses of
response inhibition, and the stop-signal task's contrasts."""
import sys
from rdflib import Graph, RDFS, OWL, URIRef

g = Graph().parse(sys.argv[1] if len(sys.argv) > 1 else
                  "neurolang_data/neurosynth/cogat.v2.owl")
print("namespaces", [(p, str(n)) for p, n in g.namespaces()
                     if "cogn" in str(n) or "cogpo" in str(n).lower()])


def label(x):
    return str(g.value(x, RDFS.label) or x).strip()


def find(text):
    return sorted(s for s, o in g.subject_objects(RDFS.label)
                  if str(o).strip().lower() == text)


def restrictions(c):
    for sup in g.objects(c, RDFS.subClassOf):
        p = g.value(sup, OWL.onProperty)
        if p is not None:
            yield p, g.value(sup, OWL.someValuesFrom), g.value(
                sup, OWL.allValuesFrom)
        else:
            yield RDFS.subClassOf, sup, None


for text in ["stroop task", "response inhibition", "motor inhibition",
             "stop signal task", "stop-signal task", "go/no-go task"]:
    for c in find(text):
        print(f"\n== {c} '{label(c)}'")
        for p, v, a in restrictions(c):
            print("  ", p.split("#")[-1].split("/")[-1], "some" if v else "",
                  v and f"{v.split('#')[-1]} '{label(v)}'", a or "")
        for s in g.subjects(RDFS.subClassOf, c):
            print("   subclass:", s.split("#")[-1], label(s))

ri = find("response inhibition")
print("\nresponse inhibition ids", ri)


def contrasts(task):
    for p, v, _ in restrictions(task):
        if str(p).endswith("has_contrast") and v is not None:
            yield v


def measured(k):
    return [v for p, v, _ in restrictions(k)
            if str(p).endswith("measures") and v is not None]


for text in ["stroop task", "stop signal task", "stop-signal task"]:
    for t in find(text):
        print(f"\ncontrasts of '{label(t)}':")
        for k in contrasts(t):
            print("  ", k.split("#")[-1], repr(label(k)),
                  [(m.split("#")[-1], label(m)) for m in measured(k)])

# every contrast that measures response inhibition or a subclass of it
sub = set(ri)
frontier = list(ri)
while frontier:
    c = frontier.pop()
    for s in g.subjects(RDFS.subClassOf, c):
        if isinstance(s, URIRef) and s not in sub:
            sub.add(s)
            frontier.append(s)
print("\nresponse inhibition and its named subclasses:",
      sorted(label(s) for s in sub))
ks = {k for k in g.subjects() for m in measured(k) if m in sub}
print("contrasts measuring them:", len(ks))
tasks = {t for t in g.subjects(RDFS.subClassOf) for k in contrasts(t)
         if k in ks}
print("tasks with such a contrast:", len(tasks),
      sorted(label(t) for t in tasks))
props = sorted({str(p) for p in g.objects(None, OWL.onProperty)})
print("\nproperties in restrictions:", props)

# The facts a plain Datalog reading has: triples between individuals.
from rdflib import RDF  # noqa: E402
CO = "http://www.cogpo.org/ontologies/working/CogPOver2011.owl#"
CA = "http://www.cognitiveatlas.org/ontology/cogat.owl#"
print("\ntriples with predicate cogpo:has_contrast:",
      len(list(g.triples((None, URIRef(CO + "has_contrast"), None)))))
print("triples with predicate cogat:measures:",
      len(list(g.triples((None, URIRef(CA + "measures"), None)))))
print("rdf:type cogat:CAO_00487:",
      len(list(g.triples((None, RDF.type, URIRef(CA + "CAO_00487"))))))
print("rdf:type cogat:CAO_00872:",
      len(list(g.triples((None, RDF.type, URIRef(CA + "CAO_00872"))))))
