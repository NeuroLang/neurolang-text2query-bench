"""Rename the one-letter columns of the ans rules of a distilled query."""
import re

TOKEN = re.compile(r"'[^']*'|[A-Za-z_][A-Za-z0-9_]*|.", re.S)
RULE = re.compile(r"^\s*(\w+)\s*(?:\[\w+\])?\s*\((.*?)\)\s*:-\s*(.*)$")
ATOM = re.compile(r"(\w+)\s*\(([^()]*)\)")
STORED = {
    "destrieux": ["region", "image"], "destrieux_activated": ["region", "study"],
    "destrieux_covered": ["region", "study"],
    "schaefer": ["parcel", "image"], "schaefer_activated": ["parcel", "study"],
    "schaefer_covered": ["parcel", "study"],
    "tian": ["region", "image"], "tian_activated": ["region", "study"],
    "tian_covered": ["region", "study"],
    "mentions": ["study", "term"], "weighted_mention": ["study", "term", "tfidf"],
    "similar_study": ["text", "study"], "study_title": ["study", "title"],
    "study_year": ["study", "year"], "study_journal": ["study", "journal"],
    "study_abstract": ["study", "abstract"], "study_pmid": ["study", "pmid"],
    "study_doi": ["study", "doi"], "selected_study": ["study"], "study": ["study"],
    "peak_mni": ["x_mm", "y_mm", "z_mm", "study"],
    "cogat_term": ["concept_class", "concept"],
    "cogat_definition": ["concept", "definition"],
    "cogat_subclass_of": ["subclass", "concept_class"],
    "destrieux_points": ["x_mm", "y_mm", "z_mm", "region"],
    "schaefer_points": ["x_mm", "y_mm", "z_mm", "parcel"],
    "tian_points": ["x_mm", "y_mm", "z_mm", "region"],
    "term_in_study_tfidf": ["study", "term", "tfidf"],
}
NETWORKS = {"VisCent", "VisPeri", "SomMot", "DorsAttn", "SalVentAttn",
            "Limbic", "Cont", "Default", "TempPar"}
HEMISPHERES = {"L", "R", "LH", "RH", "lh", "rh"}
KEYWORDS = {"PROB", "AGGREGATE", "RESAMPLE", "boot_studies"}
PLURAL = {"study": "studies", "term": "terms", "region": "regions",
          "parcel": "parcels", "concept": "concepts"}


def _tokens(line):
    """The tokens of *line*, each with whether it is a variable."""
    tokens = TOKEN.findall(line)
    out = []
    for n, t in enumerate(tokens):
        following = "".join(tokens[n + 1:]).lstrip()[:1]
        out.append((t, re.fullmatch(r"[A-Za-z_]\w*", t) is not None
                    and following not in ("(", "[") and t not in KEYWORDS))
    return out


def variables(line):
    return [t for t, is_var in _tokens(line) if is_var]


def substitute(line, mapping):
    return "".join(mapping.get(t, t) if is_var else t
                   for t, is_var in _tokens(line))


def split_args(text):
    return [a.strip() for a in text.split(",")] if text.strip() else []


def rules(query):
    out = []
    for line in query.strip().splitlines():
        m = RULE.match(line)
        out.append((m.group(1), split_args(m.group(2)), m.group(3), line)
                   if m else (None, [], "", line))
    return out


def name_of(var, body, all_rules, depth=0):
    """The name of *var* from where the body binds it."""
    if depth > 6:
        return None
    if re.search(r"PROB\s*\[[^\]]*\]\s*=\s*" + var + r"\b", body):
        return "probability"
    m = re.search(r"@\s*(\w+)\((\w+)\)\s*\)\s*=\s*" + var + r"\b", body)
    if m:
        fn, arg = m.groups()
        if fn == "count":
            inner = name_of(arg, body, all_rules, depth + 1)
            return PLURAL.get(inner, "number")
        return fn if fn not in ("max", "min", "sum") else (
            fn + "_" + (name_of(arg, body, all_rules, depth + 1) or "value"))
    for pred, args in ATOM.findall(body):
        args = split_args(args)
        if var not in args:
            continue
        k = args.index(var)
        if pred in STORED and k < len(STORED[pred]):
            return STORED[pred][k]
        for r in all_rules:
            if r[0] == pred and k < len(r[1]):
                head = r[1][k]
                if head == "PROB":
                    return "probability"
                if head.strip("'") in NETWORKS:
                    return "network"
                if head.strip("'") in HEMISPHERES:
                    return "hemisphere"
                if re.fullmatch(r"\w+", head):
                    if len(head) > 1 and head not in ("l1", "l2", "p1", "p2"):
                        return head
                    n = name_of(head, r[2], all_rules, depth + 1)
                    if n:
                        return n
    m = re.search(r"\(\s*" + var + r"\s*==\s*(.*?)\)\s*(,|$)", body)
    if m:
        expr = m.group(1)
        if "/" in expr:
            return "ratio"
        if "-" in expr:
            return "difference"
        if "*" in expr and "100" in expr:
            return "percentage"
        if expr.strip().strip("'") in HEMISPHERES:
            return "hemisphere"
        if expr.strip().strip("'") in NETWORKS:
            return "network"
    return None


def rename(query):
    """Return *query* with readable ans columns, or None if not resolved."""
    rs = rules(query)
    lines = []
    for r in rs:
        pred, args, body, line = r
        if pred != "ans":
            lines.append(line)
            continue
        if any(not re.fullmatch(r"\w+", a) for a in args):
            return None  # a call in the head
        words = set(variables(line))
        mapping = {}
        for a in args:
            if len(a) > 2 and a not in ("bf",) or a in ("i", "j", "k"):
                continue
            if len(a) == 2 and not re.fullmatch(r"[a-z]\d", a) and a not in (
                    "bf", "pa", "pb", "pc", "pt", "nm", "np", "lp"):
                continue
            n = name_of(a, body, rs)
            if a == "bf":
                n = "bayes_factor"
            if not n:
                return None
            mapping[a] = n
        # suffix duplicates and avoid names already in the rule
        used = set(words) - set(mapping)
        counts = {}
        for n in mapping.values():
            counts[n] = counts.get(n, 0) + 1
        seen = {}
        for a in args:
            if a not in mapping:
                continue
            n = mapping[a]
            if counts[n] > 1:
                seen[n] = seen.get(n, 0) + 1
                n = f"{n}_{seen[n]}"
            while n in used:
                n = n + "_"
            used.add(n)
            mapping[a] = n
        new = substitute(line, mapping)
        assert substitute(new, {v: k for k, v in mapping.items()}) == line
        lines.append(new)
    return "\n".join(lines)
