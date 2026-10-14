"""
The DBpedia subgraph of the TEXT2SPARQL DBpedia question sets.

DBpedia (2015-10, about 200 million triples) is too large for an
in-memory NeuroLang engine. The benchmark loads instead the part of it
the questions need, fetched from the challenge's public endpoint:

* for each gold query, the triples matching its patterns, with a
  ``CONSTRUCT`` over the query's own ``WHERE`` clause, so that the gold
  query gives on the subgraph the answers it gives on DBpedia;
* the outgoing triples of each entity the gold queries name (at most
  ``NEIGHBOURHOOD`` of them), so that a system has other properties to
  choose from;
* the ``rdfs:label`` (English and Spanish) and DBpedia ontology types of
  the entities the gold queries name, of their neighbours and of the
  gold answers, so that a system can find an entity by its name.

A system's query is thus exact on the subgraph when it follows the gold
pattern, and approximate otherwise. The replies of the endpoint are
cached, so that the subgraph is rebuilt without querying it again.
"""

import hashlib
import re
import time
from pathlib import Path

import httpx
import rdflib
from rdflib import URIRef, Variable
from rdflib.paths import Path as PropertyPath
from rdflib.plugins.sparql import prepareQuery

ENDPOINT = "http://141.57.8.18:9081/sparql"
NEIGHBOURHOOD = 2000
BATCH = 100
PREFIXES = {
    "dbo": "http://dbpedia.org/ontology/",
    "dbr": "http://dbpedia.org/resource/",
    "dbp": "http://dbpedia.org/property/",
    "esdbr": "http://es.dbpedia.org/resource/",
    "esdbp": "http://es.dbpedia.org/property/",
    "yago": "http://dbpedia.org/class/yago/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "dct": "http://purl.org/dc/terms/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#",
    "georss": "http://www.georss.org/georss/",
    "prov": "http://www.w3.org/ns/prov#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}
_IRI = re.compile(r"<(http[^<>\s]*)>")


class EndpointError(Exception):
    """Raised when the endpoint does not answer a query."""


class Endpoint:
    """A SPARQL endpoint whose CONSTRUCT replies are cached on disk."""

    def __init__(self, url=ENDPOINT, cache_dir=Path("data/dbpedia-cache"),
                 retries=4, timeout=300.0):
        self.url = url
        self.cache_dir = Path(cache_dir)
        self.retries = retries
        self.timeout = timeout

    def construct(self, query: str) -> str:
        """Return the N-Triples of the CONSTRUCT *query*."""
        key = hashlib.sha256(query.encode("utf-8")).hexdigest()[:24]
        path = self.cache_dir / f"{key}.nt"
        if path.exists():
            return path.read_text(encoding="utf-8")
        for attempt in range(self.retries):
            try:
                response = httpx.post(
                    self.url, data={"query": query},
                    headers={"Accept": "application/n-triples"},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                break
            except httpx.HTTPError as exc:
                if attempt == self.retries - 1:
                    raise EndpointError(f"{exc}\n{query}") from exc
                time.sleep(2 ** (attempt + 1))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(response.text, encoding="utf-8")
        return response.text


def _algebra_triples(node, found):
    """Collect the triple patterns of the algebra *node* into *found*."""
    if isinstance(node, dict):
        if getattr(node, "name", None) == "BGP":
            found.extend(node["triples"])
        for value in node.values():
            _algebra_triples(value, found)
    elif isinstance(node, (list, tuple)):
        for value in node:
            _algebra_triples(value, found)


def triple_patterns(sparql: str) -> list:
    """Return the triple patterns of *sparql* without property paths."""
    query = prepareQuery(sparql)
    found = []
    _algebra_triples(query.algebra, found)
    return [
        triple for triple in found
        if not any(isinstance(term, PropertyPath) for term in triple)
    ]


def _body(sparql: str) -> tuple:
    """
    Return the prologue and the group pattern of the query *sparql*.

    The group pattern is the text between the first ``{`` of the query
    form and its matching ``}``; braces in IRIs and strings are skipped.
    """
    form = re.search(r"\b(SELECT|ASK|CONSTRUCT|DESCRIBE)\b", sparql, re.I)
    prologue = sparql[:form.start()] if form else ""
    depth, start, quote, in_iri = 0, None, None, False
    for i in range(form.end() if form else 0, len(sparql)):
        char = sparql[i]
        if quote:
            quote = None if char == quote else quote
        elif in_iri:
            in_iri = char != ">"
        elif char in "'\"":
            quote = char
        elif char == "<" and re.match(r"<[^\s<>]*>", sparql[i:]):
            in_iri = True
        elif char == "{":
            depth += 1
            if start is None:
                start = i + 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start is not None:
                return prologue, sparql[start:i]
    raise ValueError("no group pattern")


def _n3(term) -> str:
    return f"?{term}" if isinstance(term, Variable) else term.n3()


_SUBSELECT = re.compile(
    r"\bSELECT\s+(?:DISTINCT\s+|REDUCED\s+)?(?:(?!\bWHERE\b).)*?\bWHERE\b",
    re.I | re.S,
)


def _project_everything(body: str) -> str:
    """
    Return *body* with its sub-selects projecting all their variables.

    A sub-select projecting only some variables would leave the others
    of the template unbound. Sub-selects that group are left as they are.
    """
    if re.search(r"\bGROUP\s+BY\b", body, re.I):
        return body
    return _SUBSELECT.sub("SELECT * WHERE", body)


def construct_query(sparql: str):
    """
    Return the CONSTRUCT query of the triples a gold query matches.

    Its template holds the triple patterns of the query, its WHERE clause
    the query's group pattern, its sub-selects projecting all their
    variables. It is None for a query without plain triple patterns.
    """
    patterns = triple_patterns(sparql)
    if not patterns:
        return None
    prologue, body = _body(sparql)
    body = _project_everything(body)
    template = " .\n  ".join(
        " ".join(_n3(term) for term in triple) for triple in patterns
    )
    return f"{prologue}CONSTRUCT {{\n  {template} .\n}}\nWHERE {{{body}}}"


def mentioned_entities(sparql: str) -> set:
    """Return the DBpedia resources the query *sparql* names."""
    query = prepareQuery(sparql)
    found = []
    _algebra_triples(query.algebra, found)
    entities = {
        str(term) for triple in found for term in triple
        if isinstance(term, URIRef) and "/resource/" in str(term)
    }
    entities |= {
        iri for iri in _IRI.findall(sparql) if "/resource/" in iri
    }
    return entities


def neighbourhood_query(entity: str) -> str:
    """Return the CONSTRUCT query of the outgoing triples of *entity*."""
    return (
        f"CONSTRUCT {{ <{entity}> ?p ?o }} WHERE {{ <{entity}> ?p ?o }} "
        f"LIMIT {NEIGHBOURHOOD}"
    )


def labels_query(entities: list) -> str:
    """Return the CONSTRUCT query of the labels and types of *entities*."""
    values = " ".join(f"<{e}>" for e in entities)
    return (
        "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
        "CONSTRUCT { ?e rdfs:label ?l . ?e a ?t } WHERE {\n"
        f"  VALUES ?e {{ {values} }}\n"
        "  { ?e rdfs:label ?l . FILTER(lang(?l) = 'en' || lang(?l) = 'es') }\n"
        "  UNION { ?e a ?t . FILTER(STRSTARTS(STR(?t), "
        "'http://dbpedia.org/ontology/')) }\n}"
    )


def _parse(graph: rdflib.Graph, ntriples: str) -> None:
    if ntriples.strip():
        graph.parse(data=ntriples, format="nt")


def build(questions, endpoint: Endpoint, log=print, answers=()):
    """
    Return the subgraph of the gold queries of *questions*.

    *questions* are ``(id, sparql)`` pairs and *answers* the IRIs of the
    gold answers, whose labels and types are fetched.
    """
    graph = rdflib.Graph()
    for prefix, namespace in PREFIXES.items():
        graph.bind(prefix, namespace, override=True)
    entities = set()
    for question_id, sparql in questions:
        try:
            query = construct_query(sparql)
            entities |= mentioned_entities(sparql)
        except Exception as exc:
            log(f"{question_id}: cannot read the query ({exc})")
            continue
        if query is None:
            continue
        try:
            _parse(graph, endpoint.construct(query))
        except EndpointError as exc:
            log(f"{question_id}: the endpoint failed: {str(exc)[:200]}")
        log(f"{question_id}: {len(graph)} triples")
    labelled = set(entities) | {a for a in answers if "/resource/" in a}
    for entity in sorted(entities):
        try:
            neighbourhood = rdflib.Graph()
            _parse(
                neighbourhood,
                endpoint.construct(neighbourhood_query(entity)),
            )
        except EndpointError as exc:
            log(f"neighbourhood of {entity}: {str(exc)[:200]}")
            continue
        graph += neighbourhood
        labelled |= {
            str(term) for term in neighbourhood.objects()
            if isinstance(term, URIRef) and "/resource/" in str(term)
        }
    log(f"with the neighbourhoods: {len(graph)} triples")
    resources = sorted(labelled)
    log(f"labels and types of {len(resources)} entities")
    for start in range(0, len(resources), BATCH):
        try:
            _parse(graph, endpoint.construct(
                labels_query(resources[start:start + BATCH])
            ))
        except EndpointError as exc:
            log(f"labels {start}: {str(exc)[:200]}")
    log(f"with the labels and types: {len(graph)} triples")
    return graph


def write(graph: rdflib.Graph, path: Path) -> None:
    """Write *graph* in Turtle, with the DBpedia prefixes, at *path*."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(path, format="turtle")
