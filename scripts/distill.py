"""
Distillation of Sonnet's ReAct answers into few-shot examples for the
NeuroLang query assistant (OpenRouter only).

Steps, each reading what the previous one wrote in ``data/distill/``:

    slots      real values of the engine (terms, Cognitive Atlas concepts,
               networks, regions, titles) to fill question templates
    pool       Sonnet proposes templates per category, the slots fill
               them; questions near a neurosynth-v2 question are dropped
               (bge-m3 cosine), the rest is split into a held-out slice
               and the questions to learn from
    answer     Sonnet ReAct (the teacher) answers the pool, every step
               recorded
    filter     keep a question when its ReAct query ran and returned rows
               and a judge (Opus) says it answers the question
    calibrate  the judge on the neurosynth-v2 golds and broken queries
    bank       write the kept pairs as the bank additions, and the
               held-out slice as a bench dataset

Round 2 (``--round 2``, written in ``data/distill/round2/``): ``pool``
writes ``pool2.json``, weighted toward DeepSeek's failure types
(CATEGORIES2) and kept away from every evaluation set; ``answer``
takes ``--provider``, ``--tag`` and ``--temperature`` (Sonnet the
teacher, DeepSeek x3 for the agreement gate, scripts/agreement_gate.py)
and stops at ``--max-usage`` dollars of the OpenRouter key.

    source scripts/env.sh
    .venv-distill/bin/python scripts/distill.py slots
    .venv-distill/bin/python scripts/distill.py pool
    ...

Keys are read from the environment (scripts/env.sh), never printed.
"""

import argparse
import json
import os
import random
import re
import signal
import sys
import time
from collections import Counter
from pathlib import Path

import httpx
import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).parent))
import leakage  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "distill"
ROUND2 = OUT / "round2"
LEDGER = OUT / "ledger.jsonl"   # data/distill/round2/tokens.jsonl in round 2
OPENROUTER = "https://openrouter.ai/api/v1"
SONNET = "anthropic/claude-sonnet-5.5"
JUDGE = "anthropic/claude-opus-5.5"
EMBEDDING = "baai/bge-m3"
MAX_LEAK = 0.85
MAX_DUPLICATE = 0.92
GRIST = "https://grist.numerique.gouv.fr"
GRIST_DOC = "x3XcRRNuWbxfGb7BtigLKm"

# category: (target questions, what it asks)
CATEGORIES = {
    "free_text": (24, "a topic given as a free-text description of a "
                  "phenomenon or paradigm (no keyword of the vocabulary): "
                  "which studies are about it, what titles, which regions "
                  "or networks its studies activate. Write the topic "
                  "inside the question, no placeholder."),
    "cogat_term": (18, "a Cognitive Atlas concept {cogat} used as a "
                   "term: studies mentioning it, the regions or networks "
                   "they activate, its definition."),
    "cogat_hierarchy": (10, "the Cognitive Atlas hierarchy of {parent}: "
                        "its subclasses, the studies mentioning one of "
                        "them, the regions they activate."),
    "schaefer": (20, "the Schaefer functional networks ({network}, "
                 "{network2}) and the term {term}: probability of "
                 "activation, which networks a term activates, parcels "
                 "of a network, left or right hemisphere."),
    "destrieux": (16, "gyri and sulci of the Destrieux atlas ({destrieux}, "
                  "{destrieux2}) and the term {term}: activation of a "
                  "region, which regions a term activates."),
    "tian": (14, "subcortical structures ({tian}, {tian2}) of the Tian "
             "atlas and the term {term}: activation of a structure, "
             "which structures a term activates."),
    "prob_forward": (20, "marginal and conditional probabilities over the "
                     "studies: the probability of a term {term}, of "
                     "{term} given {term2}, of the activation of the MNI "
                     "point {point} given {term}, lift or Bayes factor of "
                     "an association (forward inference)."),
    "coactivation": (14, "co-activation: regions ({destrieux}, {tian}) or "
                     "networks ({network}) activated by the same studies, "
                     "with a seed, or for studies mentioning {term}."),
    "counts": (20, "how many studies (a count): mention {term}, mention "
               "both {term} and {term2}, per term, per region, how many "
               "terms or concepts; use combien/how many."),
    "negation": (10, "studies or terms that do not mention {term}, "
                 "regions not activated, terms mentioned without {term2}."),
    "conj_disj": (14, "conjunction (both {term} and {term2}) and "
                  "disjunction (either {term} or {term2}) of terms or "
                  "regions ({destrieux}, {tian}), and their probabilities."),
    "study_titles": (14, "titles of studies: the title of study {study_id}, "
                     "titles of the studies mentioning {term}, the study "
                     "titled '{title}' and what it mentions."),
}

SCHAEFER_NAMES = {
    "VisCent": "central visual", "VisPeri": "peripheral visual", "SomMot": "somatomotor", "DorsAttn": "dorsal attention",
    "SalVentAttn": "salience ventral attention", "Limbic": "limbic",
    "Cont": "frontoparietal control", "Default": "default mode",
    "TempPar": "temporoparietal",
}
TIAN_NAMES = {
    "HIP": "hippocampus", "AMY": "amygdala", "THA": "thalamus",
    "NAc": "nucleus accumbens", "GP": "globus pallidus", "PUT": "putamen",
    "CAU": "caudate",
}
# MNI landmarks (mm) for the questions on points.
POINTS = [
    ("left hippocampus", (-28, -22, -14)), ("right hippocampus", (28, -22, -14)),
    ("right amygdala", (24, -4, -20)), ("left putamen", (-24, 4, 0)),
    ("right caudate", (12, 12, 10)), ("left thalamus", (-10, -18, 8)),
    ("posterior cingulate", (0, -52, 26)), ("left insula", (-38, 6, 2)),
    ("right insula", (38, 6, 2)), ("medial prefrontal cortex", (0, 52, -6)),
    ("left motor hand area", (-38, -22, 56)), ("right fusiform face area", (40, -52, -18)),
    ("primary visual cortex", (0, -90, 0)), ("left Broca's area", (-48, 18, 14)),
]
# More MNI landmarks for round 2.
POINTS2 = POINTS + [
    ("left amygdala", (-24, -4, -20)), ("right putamen", (24, 4, 0)),
    ("left caudate", (-12, 12, 10)), ("right thalamus", (10, -18, 8)),
    ("dorsal anterior cingulate", (0, 24, 30)), ("pre-supplementary motor area", (0, 18, 50)),
    ("left dorsolateral prefrontal cortex", (-44, 36, 24)),
    ("right dorsolateral prefrontal cortex", (44, 36, 24)),
    ("left temporoparietal junction", (-50, -56, 22)),
    ("right temporoparietal junction", (52, -54, 22)),
    ("precuneus", (2, -60, 40)), ("left angular gyrus", (-44, -66, 36)),
    ("right intraparietal sulcus", (32, -56, 48)), ("left fusiform face area", (-40, -52, -18)),
    ("ventromedial prefrontal cortex", (2, 46, -10)), ("right orbitofrontal cortex", (28, 34, -14)),
    ("left visual word form area", (-44, -58, -12)), ("right V5/MT", (46, -70, 2)),
    ("left primary auditory cortex", (-46, -22, 8)), ("ventral striatum", (10, 10, -8)),
    ("left cerebellum", (-24, -62, -26)), ("right frontal eye field", (30, -4, 52)),
]

# Round 2: the 12 categories of round 1 (and of neurosynth-v3), with the
# failure types of DeepSeek (runs/nsv3c.md) as categories of their own.
FOCUS = {
    "answer_shape": (100, "questions whose answer is a table of pairs or "
                     "groups, not a plain list: each pair of regions "
                     "({destrieux}, {tian}) or of networks ({network}) "
                     "co-activated by studies about {term}, with its "
                     "probability; for each network, region or "
                     "subcortical structure the probability or the number "
                     "of studies mentioning {term} (one row per region); "
                     "for each of {term} and {term2} its probability; the "
                     "networks with their parcels; per hemisphere. Say "
                     "what each row holds ('each pair', 'for each', "
                     "'per', 'with')."),
    "prob_negation": (90, "probabilistic negation: the probability that a "
                      "region ({destrieux}, {tian}), a network ({network}) "
                      "or the MNI point {point} is NOT activated by "
                      "studies about {term}; which gyri, sulci, structures "
                      "or networks are not activated by studies about "
                      "{term}, with the probability of not being "
                      "activated; the probability that a study mentions "
                      "{term} but not {term2}; the probability that a "
                      "study about {term} activates {tian} but not "
                      "{destrieux}. Use 'not activated', 'does not "
                      "activate', 'without'."),
    "mni_point": (90, "MNI coordinates in millimetres, {point}: the "
                  "probability of an activation near the point, given "
                  "{term}; the lift or Bayes factor of the point and "
                  "{term}; the terms of the studies with a peak near the "
                  "point; the region of an atlas ({destrieux}, {tian}, a "
                  "network) at or near the point; how many studies report "
                  "a peak within a few mm; two points activated together. "
                  "Keep the coordinates as written in the placeholder."),
    "value_search": (100, "questions naming things as a researcher would, "
                     "so that the engine's own value must be looked up "
                     "first: a gyrus, sulcus or subcortical structure in "
                     "plain anatomical words, not an atlas label (e.g. "
                     "'the left angular gyrus', 'the right anterior "
                     "hippocampus', 'the head of the caudate'); a "
                     "Cognitive Atlas concept by a synonym or "
                     "description; a network by its usual name ('the "
                     "salience network', 'the default network', 'the "
                     "dorsal attention network'); a term in another "
                     "form or plural ('emotional faces', 'memories'). Ask "
                     "their studies, activation probability, "
                     "co-activation, subclasses or definition. Write the "
                     "names in the template; placeholders only {term} or "
                     "{cogat}."),
}
CATEGORIES2 = {
    **{c: (35, description) for c, (_, description) in CATEGORIES.items()},
    **FOCUS,
}
EVALUATION_SETS = ["neurosynth-v2", "neurosynth-v3-heldout",
                   "neurosynth-v3-fresh", "neurosynth-distill-heldout"]


def log(message):
    print(message, file=sys.stderr, flush=True)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False, default=str))


def read_json(path):
    return json.loads(Path(path).read_text())


def chat(model, messages, purpose, temperature=0.0, max_tokens=4000):
    """Return the reply of *model* on OpenRouter; tokens go to the ledger."""
    headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
    for attempt in range(5):
        try:
            response = httpx.post(
                f"{OPENROUTER}/chat/completions", headers=headers, timeout=240,
                json={"model": model, "messages": messages,
                      "temperature": temperature, "max_tokens": max_tokens},
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            break
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            log(f"{model} {purpose}: {type(exc).__name__}, retry {attempt}")
            time.sleep(5 * (attempt + 1))
    else:
        raise RuntimeError(f"OpenRouter kept failing for {purpose}")
    usage = data.get("usage", {})
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "a") as ledger:
        ledger.write(json.dumps({
            "model": model, "purpose": purpose, "time": time.time(),
            "in": usage.get("prompt_tokens", 0),
            "out": usage.get("completion_tokens", 0),
        }) + "\n")
    return text


def json_block(text):
    """Return the JSON value in the first fenced block or bracket of *text*."""
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    body = match.group(1) if match else text
    start = min((i for i in (body.find("["), body.find("{")) if i >= 0))
    return json.JSONDecoder().raw_decode(body[start:])[0]


def embed(texts):
    return leakage.embed(
        texts, model=EMBEDDING, base_url=OPENROUTER,
        key_env="OPENROUTER_API_KEY",
    )


def engine(args):
    from text2query_bench.engine import build_engine

    log("Building the neurosynth engine...")
    return build_engine("neurosynth", args.data_dir)


def run_rows(nl, query, timeout=300.0):
    """Return the rows and the error of *query* on the engine."""
    from text2query_bench.engine import execute
    from neurolang_apps.utils.llm import validation

    # in a forked child, killed at the timeout: a thread left running a
    # timed-out query would hold the engine (and a CPU) for the next ones
    try:
        execution = validation._in_child(
            lambda: execute(nl, query, "datalog", timeout), timeout + 30, 16000)
    except (validation.QueryTimeout, validation.QueryTooLarge) as exc:
        return [], f"{type(exc).__name__} running the rows of the final query"
    return execution.rows, execution.error


# --- slots -------------------------------------------------------------


def cmd_slots(args):
    nl = engine(args)

    def rows(query):
        found, error = run_rows(nl, query)
        assert not error, error
        return found

    counts = dict(rows("ans(t, n) :- AGGREGATE[t](mentions(s, t) @ count(s)) = n"))
    plain = re.compile(r"[a-z]+( [a-z]+)?")
    terms = [t for t, n in counts.items()
             if plain.fullmatch(t) and len(t) >= 4 and 150 <= n <= 4000]
    cogat = [t for (t,) in rows("ans(t) :- cogat_term(c, t)")
             if plain.fullmatch(t) and counts.get(t, 0) >= 20]
    parents = [t for (t,) in rows(
        "ans(t) :- cogat_subclass_of(x, c), cogat_term(c, t)"
    ) if plain.fullmatch(t)]
    schaefer = [l for (l,) in rows("ans(l) :- schaefer(l, r)")]
    destrieux = [l for (l,) in rows("ans(l) :- destrieux(l, r)")]
    tian = [l for (l,) in rows("ans(l) :- tian(l, r)")]
    titles = [(s, t) for s, t in rows("ans(s, t) :- study_title(s, t)")
              if 40 <= len(t) <= 110]
    rng = random.Random(0)
    topical = chat(SONNET, [{"role": "user", "content": (
        "From these words of a neuroimaging literature vocabulary keep "
        "those naming a topic a researcher would ask about: a cognitive "
        "process, task, stimulus, sensory modality, disorder, drug, "
        "anatomy or behaviour. Drop generic words. Reply with a JSON list "
        "of the kept words, nothing else.\n" + " ".join(terms)
    )}], "slots", max_tokens=12000)
    terms = [t for t in json_block(topical) if t in counts]
    networks = sorted({
        re.match(r"17Networks [LR]H ([A-Za-z]+?)[A-C]?( |$)", l).group(1)
        for l in schaefer
    })
    names = chat(SONNET, [{"role": "user", "content": (
        "Give the plain English anatomical name a neuroscientist would use "
        "for each Destrieux atlas label (hemisphere first, G = gyrus, S = "
        "sulcus), e.g. 'L G temp sup Lateral' -> 'left superior temporal "
        "gyrus (lateral surface)'. Reply with a JSON object label -> name, "
        "nothing else.\n" + "\n".join(destrieux)
    )}], "slots", max_tokens=12000)
    write_json(OUT / "slots.json", {
        "term": rng.sample(terms, min(len(terms), 250)),
        "cogat": rng.sample(cogat, min(len(cogat), 120)),
        "parent": parents,
        "network": [SCHAEFER_NAMES[n] for n in networks if n in SCHAEFER_NAMES],
        "destrieux": json_block(names),
        "tian": sorted({TIAN_NAMES[re.sub(r"^[lamp]*(?=[A-Z])", "", l.split()[0])]
                        for l in tian
                        if re.sub(r"^[lamp]*(?=[A-Z])", "", l.split()[0])
                        in TIAN_NAMES}),
        "study_id": [s for s, _ in rng.sample(titles, 60)],
        "title": [t for _, t in rng.sample(titles, 60)],
        "point": [f"{n} (MNI {x}, {y}, {z})" for n, (x, y, z) in POINTS],
    })
    log(f"slots written; {len(terms)} terms, {len(cogat)} concepts")


# --- pool --------------------------------------------------------------


def fill(template, slots, rng, used):
    """
    Fill the {placeholders} of *template* with unused slot values, or
    return None when it has a placeholder of no known kind.
    """
    if any(re.sub(r"\d+$", "", k) not in slots
           for k in re.findall(r"\{(\w+)\}", template)):
        return None
    def value(match):
        key = match.group(1)
        kind = re.sub(r"\d+$", "", key)
        if kind == "destrieux":
            choices = list(slots["destrieux"].values())
        else:
            choices = slots[kind]
        fresh = [c for c in choices if (kind, str(c)) not in used] or choices
        choice = rng.choice(fresh)
        used.add((kind, str(choice)))
        return str(choice)

    return re.sub(r"\{(\w+)\}", value, template)


def grist_questions():
    """Return the questions of users' bad rows of the Answers table, if any."""
    key = os.environ.get("GRIST_API_KEY")
    if not key:
        log("GRIST_API_KEY is not set: no questions from the Grist document")
        return []
    response = httpx.get(
        f"{GRIST}/api/docs/{GRIST_DOC}/tables/Answers/records",
        headers={"Authorization": f"Bearer {key}"}, timeout=60,
    )
    response.raise_for_status()
    fields = [r["fields"] for r in response.json()["records"]]
    return [
        f["question"] for f in fields
        if str(f.get("verdict", "")).lower() == "bad"
        and f.get("user") != "test" and f.get("question")
    ]


def propose(category, wanted, description, bank_questions, slots, avoid=()):
    keys = sorted(set(re.findall(r"\{(\w+)\}", description)))
    written = ("\n\nThese templates are already written; write different "
               "ones (other phrasing, other kind of answer):\n- "
               + "\n- ".join(avoid)) if avoid else ""
    reply = chat(SONNET, [{"role": "user", "content": (
        "You write English questions a researcher might ask a "
        "meta-analytic engine over ~14,000 neuroimaging studies "
        "(NeuroSynth terms, Cognitive Atlas concepts, brain atlases, "
        "MNI points, study titles). Style of the existing bank (short, "
        "plain, at most 15 words):\n- " + "\n- ".join(bank_questions[:14])
        + f"\n\nWrite {wanted} different question templates for the "
        f"category '{category}': {description}\nA template may contain "
        "the placeholders " + ", ".join("{" + k + "}" for k in keys)
        + " (use a placeholder only where a value of that kind fits, "
        "a second one as {term2} etc.), which are replaced by values of "
        "the engine. Vary the phrasing, the verb and the kind of answer. "
        "Reply with a JSON list of strings, nothing else." + written
    )}], f"pool-{category}", temperature=0.8, max_tokens=4000)
    try:
        return [t for t in json_block(reply) if isinstance(t, str)]
    except ValueError:
        log(f"{category}: no JSON list in the reply, asked again")
        return []


def cmd_pool(args):
    from text2query_bench.dataset import load_dataset
    from neurolang_apps.utils.llm.examples import load_examples

    second = args.round == 2
    categories = CATEGORIES2 if second else CATEGORIES
    slots = read_json(OUT / "slots.json")
    if second:
        slots["point"] = [f"{n} (MNI {x}, {y}, {z})" for n, (x, y, z) in POINTS2]
    bank = [e.question for e in load_examples("neurosynth") if e.question]
    rng = random.Random(2 if second else 1)
    used = set()
    pool = [] if second else [
        {"category": "grist", "question": q, "source": "grist"}
        for q in grist_questions()
    ]
    for category, (target, description) in categories.items():
        cache = (ROUND2 / "templates" if second else OUT / "templates") / f"{category}.json"
        templates = read_json(cache) if cache.exists() else []
        # round 2: twice the target, 40 templates a request
        wanted = int(target * (2.2 if second else 1.4))
        while len(templates) < wanted:
            templates += propose(
                category, min(40, wanted - len(templates)), description,
                bank, slots, avoid=templates,
            )
            write_json(cache, templates)
            if not second:
                break
        mine = []
        for template in templates:
            question = fill(template, slots, rng, used)
            if question:
                mine.append({"category": category, "source": "template",
                             "question": question.strip()})
        if second:
            rng.shuffle(mine)
        pool += mine
        log(f"{category}: {len(templates)} templates")
    sets = EVALUATION_SETS if second else EVALUATION_SETS[:1]
    evaluation = [text for name in sets
                  for q in load_dataset(ROOT / f"datasets/{name}.yaml").questions
                  for text in q.text.values()]
    known = bank + ([p["question"] for p in read_json(OUT / "pool.json")]
                    if second else [])
    vectors = embed([p["question"] for p in pool] + evaluation + known)
    n, m = len(pool), len(evaluation)
    leak = (vectors[:n] @ vectors[n:n + m].T).max(axis=1)
    near_bank = (vectors[:n] @ vectors[n + m:].T).max(axis=1)
    kept, dropped = [], Counter()
    for i, item in enumerate(pool):
        item["leak"], item["bank"] = float(leak[i]), float(near_bank[i])
        if leak[i] > MAX_LEAK:
            dropped["near an evaluation question"] += 1
        elif near_bank[i] > MAX_DUPLICATE:
            dropped["duplicate of a bank (or round-1 pool) question"] += 1
        elif kept and float((vectors[kept] @ vectors[i]).max()) > MAX_DUPLICATE:
            dropped["duplicate in the pool"] += 1
        else:
            kept.append(i)
    # at most the category's target of each, grist first
    taken, per = [], Counter()
    for i in kept:
        c = pool[i]["category"]
        if c == "grist" or per[c] < categories[c][0]:
            per[c] += 1
            taken.append(i)
    final = [pool[i] for i in taken]
    for number, item in enumerate(final, 1):
        item["id"] = f"p2-{number:04d}" if second else f"pool-{number:03d}"
    # held-out slice: every 5th question of each category (about 20%);
    # none in round 2, evaluated on neurosynth-v3 and fresh
    seen = Counter()
    for item in final:
        seen[item["category"]] += 1
        item["split"] = (
            "heldout" if not second and item["category"] != "grist"
            and seen[item["category"]] % 5 == 0 else "train"
        )
    write_json(OUT / ("pool2.json" if second else "pool.json"), final)
    log(f"proposed {n}, dropped {dict(dropped)}, kept {len(final)} "
        f"({sum(i['split'] == 'heldout' for i in final)} held out)")
    log(f"max cosine to an evaluation question ({', '.join(sets)}; kept): "
        f"{max(i['leak'] for i in final):.3f}; "
        f"max over all proposed: {leak.max():.3f}")
    log(f"per category: {dict(Counter(i['category'] for i in final))}")


# --- the teacher: Sonnet ReAct answers -------------------------------


def spent(model=SONNET):
    """Return the tokens (in, out) of *model* in the ledger."""
    total = Counter()
    path = OUT / "ledger.jsonl"
    for line in path.read_text().splitlines() if path.exists() else []:
        entry = json.loads(line)
        if entry["model"] == model:
            total["in"] += entry["in"]
            total["out"] += entry["out"]
    return total["in"], total["out"]


def normalised(rows):
    from text2query_bench.metrics import normalise

    return [[normalise(v) for v in row] for row in rows]


def pool_order(pool):
    """
    Return the pool as it is answered: the questions of Grist, then the
    held-out slice, then the rest, the categories being interleaved so
    that any prefix covers them all (the Sonnet budget ends the run).
    """
    ranks = Counter()
    keyed = []
    for item in pool:
        group = ("grist" if item["category"] == "grist" else item["split"],
                 item["category"])
        keyed.append((
            ["grist", "heldout", "train"].index(group[0]), ranks[group], item
        ))
        ranks[group] += 1
    return [item for _, _, item in sorted(keyed, key=lambda k: k[:2])]


def key_usage():
    """Return the dollars spent by the OpenRouter key."""
    response = httpx.get(
        f"{OPENROUTER}/key", timeout=60,
        headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
    )
    response.raise_for_status()
    return response.json()["data"]["usage"]


def given_up(item, path, provider, timeout):
    """
    Fork: return False in the child, which answers *item*; in the parent,
    wait for it and return True, killing it after *timeout* seconds (a
    query stuck in the engine's planning, out of reach of the assistant's
    guard) and recording the question as given up.
    """
    pid = os.fork()
    if pid == 0:
        return False
    start = time.monotonic()
    while not os.waitpid(pid, os.WNOHANG)[0]:
        if time.monotonic() - start > timeout:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
            log(f"{item['id']}: stuck for {timeout} s, given up")
            with open(path, "a") as answers:
                answers.write(json.dumps({
                    "id": item["id"], "question": item["question"],
                    "category": item["category"], "query": "", "valid": False,
                    "error": f"stuck for {timeout} s (engine)", "rows": [],
                    "steps": [], "calls": 0, "usage": {}, "seconds": timeout,
                    "model": provider.model, "hung": True,
                }) + "\n")
            break
        time.sleep(2)
    return True


def gate_decided(qid):
    """
    Whether the agreement gate (scripts/agreement_gate.py) has decided
    *qid* from Sonnet's answer and the DeepSeek samples 0 and 1 (read
    once: run it once they are complete).
    """
    import agreement_gate

    if not hasattr(gate_decided, "answers"):
        gate_decided.answers = [agreement_gate.load(ROUND2, tag) for tag in
                                ("react.sonnet", "deepseek.0", "deepseek.1")]
    teacher, *answers = [a.get(qid) for a in gate_decided.answers]
    return agreement_gate.status(teacher, answers)[0] != "unanswered"


def cmd_answer(args):
    """
    Answer the pool with ReAct: Sonnet (the teacher), or in round 2 any
    provider of ``--config`` (``--tag`` names the output, ``--temperature``
    sets the sampling). ``--workers`` processes share the engine, forked
    once it is built; ``--shard I/N`` splits the pool between commands.
    """
    from neurolang_apps.utils.llm import LLMError, load_config, make_agent

    second = args.round == 2
    nl = engine(args)
    config = load_config(ROOT / (args.config or "configs/llm.master-v0.yaml"))
    provider = config.provider(args.provider)
    config.assistant.comment_rules = False
    config.assistant.verify_rounds = 0
    if args.temperature is not None:
        config.assistant.temperature = args.temperature
    if second:
        pool = pool_order(read_json(OUT / "pool2.json"))
        out, tag = ROUND2, args.tag
    else:
        pool = pool_order(read_json(OUT / "pool.json"))
        out, tag = OUT, "react"
    out.mkdir(parents=True, exist_ok=True)
    done = {
        json.loads(line)["id"] for file in out.glob(f"{tag}.*jsonl")
        for line in file.read_text().splitlines()
    }
    index, count = args.shard
    worker = 0
    if args.workers > 1:
        # Forked workers share the engine's memory (copy on write). On
        # macOS a forked child cannot load the text encoder: load it first.
        from neurolang_apps.utils import text_embeddings

        run_rows(nl, "ans(s) :- similar_study('working memory', s)")
        text_embeddings.prepare_for_fork()
        for worker in range(args.workers - 1, -1, -1):
            if worker == 0 or os.fork() == 0:
                break
    name = f"{index}-{worker}" if args.workers > 1 else f"{index}"
    path = out / (f"{tag}.w{name}.jsonl" if second else f"{tag}.{name}.jsonl")
    answered = 0
    # the shards and workers split what remains to answer, evenly
    todo = [item for item in pool if item["id"] not in done]
    for number, item in enumerate(todo):
        if number % count != index or (number // count) % args.workers != worker:
            continue
        if args.limit and answered >= args.limit:
            break
        if args.lazy and gate_decided(item["id"]):
            continue
        if not second and sum(spent()) > args.budget:
            log("Sonnet budget reached")
            break
        if second and answered % 5 == 0 and key_usage() > args.max_usage:
            log(f"worker {index}: OpenRouter usage above {args.max_usage}$, stop")
            break
        if second and given_up(item, path, provider, args.question_timeout):
            answered += 1
            continue  # the parent; the child answers below
        steps = []
        agent = make_agent(
            nl, provider, config.assistant, "datalog", "react",
            engine_name="neurosynth", exclude_question=item["question"],
            on_step=lambda step: steps.append({
                "thought": step.thought, "action": step.action,
                "arguments": step.arguments, "observation": step.observation,
            }),
        )
        start = time.perf_counter()
        try:
            result = agent.run(item["question"])
        except LLMError as exc:
            log(f"{item['id']}: {exc}")
            if second:
                with open(out / f"{tag}.errors.log", "a") as errors:
                    errors.write(f"{item['id']}\t{exc}\n")
                os._exit(0)
            continue
        rows, error = ([], "") if not result.query else run_rows(nl, result.query)
        entry = {
            "id": item["id"], "question": item["question"],
            "query": result.query, "valid": result.valid,
            "error": result.error or error, "rows": normalised(rows),
            "steps": steps, "calls": result.calls,
            "usage": dict(result.usage), "seconds": time.perf_counter() - start,
        }
        if second:
            entry.update(category=item["category"], model=provider.model,
                         explanation=result.explanation,
                         temperature=config.assistant.temperature)
        with open(path, "a") as answers:
            answers.write(json.dumps(entry, default=str) + "\n")
        with open(LEDGER, "a") as ledger:
            ledger.write(json.dumps({
                "model": provider.model, "purpose": f"react-{tag}" if second else "react",
                "time": time.time(),
                "in": result.usage.get("input", 0),
                "out": result.usage.get("output", 0),
            }) + "\n")
        done.add(item["id"])
        answered += 1
        log(f"{item['id']} {item['category']}: valid={result.valid} "
            f"rows={len(rows)} steps={len(steps)} "
            f"tokens={sum(result.usage.values())}"
            + ("" if second else f" spent={sum(spent())}"))
        if second:
            os._exit(0)
    if worker:
        os._exit(0)
    while args.workers > 1:
        try:
            os.wait()
        except ChildProcessError:
            break


# --- judge, filter and calibration ---------------------------------------


class Judge:
    """
    Opus (OpenRouter) says whether queries answer a question: the
    assistant's own verification instructions, the engine's description,
    schema and guidance, the question, the queries and their first rows.
    """

    def __init__(self, nl):
        from neurolang_apps.utils import engine_registry
        from neurolang_apps.utils.llm import prompts
        from neurolang_apps.utils.llm.context import EngineContext

        config = engine_registry.get_engine_config("neurosynth")
        description = " ".join(config.get("description", "").split())
        guidance = " ".join(config.get("assistant_guidance", "").split())
        self.system = (
            f"{prompts.VERIFICATION}\n\n# The engine\n{description}\n\n"
            f"# Predicates of the engine\n"
            f"{EngineContext(nl, 'neurosynth').schema_summary()}\n\n"
            f"# How to answer on this engine\n{guidance}\n\n"
            "Several queries may be given for the question, A, B...: judge "
            "each on its own. End with one line per query, "
            "`VERDICT A: yes` or `VERDICT A: no`, and so on."
        )

    def __call__(self, question, queries):
        """Return {letter: (verdict, reason)} for the {letter: (query, rows)}."""
        parts = [f"Question: {question}"]
        for letter, (query, rows) in queries.items():
            shown = "\n".join(str(tuple(r)) for r in rows[:10])
            parts.append(
                f"Query {letter}:\n{query}\nIt returns {len(rows)} rows, "
                f"the first being:\n{shown or '(none)'}"
            )
        reply = chat(JUDGE, [
            {"role": "system", "content": self.system},
            {"role": "user", "content": "\n\n".join(parts)},
        ], "judge", max_tokens=2500)
        verdicts = {
            m.group(1): m.group(2).lower() == "yes"
            for m in re.finditer(r"VERDICT\s+([A-Z])\s*:\s*(yes|no)", reply, re.I)
        }
        return {
            letter: (verdicts.get(letter, False), " ".join(reply.split())[-600:])
            for letter in queries
        }


def load_answers(mode):
    out = {}
    for file in sorted(OUT.glob(f"{mode}.*.jsonl")):
        for line in file.read_text().splitlines():
            entry = json.loads(line)
            out[entry["id"]] = entry
    return out


def cmd_filter(args):
    nl = engine(args)
    judge = Judge(nl)
    pool = {item["id"]: item for item in read_json(OUT / "pool.json")}
    decisions = []
    for qid, teacher in load_answers("react").items():
        decision = {
            "id": qid, "question": teacher["question"],
            "category": pool[qid]["category"], "split": pool[qid]["split"],
            "query": teacher["query"], "rows": teacher["rows"],
        }
        if not (teacher["valid"] and teacher["rows"]):
            decision.update(status="rejected",
                            reason="the query is invalid or returns no rows")
        else:
            right, reason = judge(
                teacher["question"], {"A": (teacher["query"], teacher["rows"])}
            )["A"]
            decision.update(status="kept" if right else "rejected",
                            reason="judge: " + reason)
        decisions.append(decision)
        log(f"{qid} {decision['status']}")
    write_json(OUT / "filtered.json", decisions)
    for split in ("train", "heldout"):
        mine = [d for d in decisions if d["split"] == split]
        log(f"{split}: {len(mine)} answered, "
            f"{Counter(d['status'] for d in mine)}")


def mutations(query, constants):
    """Yield (kind, broken query) variants of the gold *query*."""
    quoted = re.findall(r"'([a-z ]+)'", query)
    if quoted and "mentions" in query:
        other = next(c for c in constants if c not in quoted)
        yield "swapped term", query.replace(f"'{quoted[0]}'", f"'{other}'", 1)
    if "//" in query:
        yield "condition dropped", re.sub(r"\s*//[^\]]*\]", "]", query)
    if ", selected_study(s)" in query:
        yield "no selected_study", query.replace(", selected_study(s)", "")
    if "~" in query:
        yield "negation dropped", query.replace("~", "")
    for a, b in (("destrieux_activated", "tian_activated"),
                 ("tian_activated", "schaefer_activated"),
                 ("schaefer_activated", "destrieux_activated")):
        if a in query:
            yield "wrong atlas", query.replace(a, b)
            break
    if "cogat_term(" in query:
        yield "rdfs:label for cogat_term", query.replace("cogat_term(", "rdfs:label(")
    if "AGGREGATE" in query:
        yield "count instead of probability", None


def cmd_calibrate(args):
    from text2query_bench.dataset import load_dataset

    nl = engine(args)
    judge = Judge(nl)
    dataset = load_dataset(ROOT / "datasets/neurosynth-v2.yaml")
    gold = read_json(ROOT / "datasets/neurosynth-v2.gold.json")
    slots = read_json(OUT / "slots.json")
    cases = []
    for q in dataset.questions:
        cases.append({"id": q.id, "kind": "gold", "right": True,
                      "question": q.text["en"], "query": gold[q.id]["query"],
                      "rows": gold[q.id]["rows"]})
    rng = random.Random(3)
    broken = []
    for q in dataset.questions:
        for kind, query in mutations(gold[q.id]["query"], slots["term"]):
            if query:
                broken.append({"id": q.id, "kind": kind, "question": q.text["en"],
                               "query": query})
    # a query of another question with the same tag: right to run, wrong answer
    by_tag = {}
    for q in dataset.questions:
        by_tag.setdefault(q.tags[0], []).append(q)
    for tag, qs in by_tag.items():
        if len(qs) > 1:
            a, b = rng.sample(qs, 2)
            broken.append({"id": a.id, "kind": "query of another question",
                           "question": a.text["en"], "query": gold[b.id]["query"]})
    kinds = {}
    for case in broken:
        kinds.setdefault(case["kind"], []).append(case)
    chosen = [c for cs in kinds.values() for c in rng.sample(cs, min(len(cs), 4))]
    for case in chosen:
        rows, error = run_rows(nl, case["query"])
        if error:
            continue  # the assistant only offers queries that run
        cases.append({**case, "right": False, "rows": normalised(rows)})
    for case in cases:
        verdict, reason = judge(case["question"], {"A": (case["query"], case["rows"])})["A"]
        case.update(verdict=verdict, reason=reason, correct=verdict == case["right"])
    write_json(OUT / "calibration.json", cases)
    gold_cases = [c for c in cases if c["right"]]
    bad = [c for c in cases if not c["right"]]
    log(f"gold judged right: {sum(c['correct'] for c in gold_cases)}/{len(gold_cases)}")
    log(f"broken judged wrong: {sum(c['correct'] for c in bad)}/{len(bad)}")
    for kind in sorted({c["kind"] for c in bad}):
        mine = [c for c in bad if c["kind"] == kind]
        log(f"  {kind}: {sum(c['correct'] for c in mine)}/{len(mine)}")
    for c in cases:
        if not c["correct"]:
            log(f"  disagrees: {c['id']} [{c['kind']}] {c['question']}\n    {c['reason'][-300:]}")


# --- bank and held-out dataset -------------------------------------------

BANK = ("/Users/bot/NeuroLang-distill/packages/neurolang_apps/neurolang_apps/"
        "utils/engines/coordinate_meta_analysis/examples.yaml")
MAX_QUESTION = 140


def cmd_bank(args):
    """Append the kept questions of the train split to the bank, and write
    the kept held-out questions as the bench dataset."""
    from neurolang_apps.utils.llm.examples import load_examples

    kept = [d for d in read_json(OUT / "filtered.json") if d["status"] == "kept"]
    train = [d for d in kept if d["split"] == "train"]
    heldout = [d for d in kept if d["split"] == "heldout"]
    bank = load_examples("neurosynth")
    squash = lambda text: " ".join(text.split())
    known = {squash(e.query("datalog")) for e in bank}
    held = embed([d["question"] for d in heldout])
    vectors = embed([d["question"] for d in train]) if train else []
    added, dropped = [], Counter()
    for d, vector in zip(train, vectors):
        query = d["query"]
        if len(d["question"]) > MAX_QUESTION:
            dropped["question too long"] += 1
        elif squash(query) in known:
            dropped["query already in the bank"] += 1
        elif float((held @ vector).max()) > MAX_LEAK:
            dropped["near a held-out question"] += 1
        else:
            known.add(squash(query))
            added.append((d, query))
    text = (
        "\n  # Distilled from Sonnet 5.5's ReAct answers on generated questions "
        "(terms, Cognitive\n  # Atlas concepts, networks, regions and titles of "
        "the engine), kept when the\n  # query returned rows and a judge (Opus 5.5) accepted it.\n"
    )
    for d, query in added:
        body = "\n".join("      " + line for line in query.splitlines())
        text += (f"\n  - question: {json.dumps(d['question'], ensure_ascii=False)}"
                 f"\n    datalog: |-\n{body}\n")
    if not args.heldout_only:
        with open(BANK, "a") as bank_file:
            bank_file.write(text)
    log(f"bank: {len(added)} added, dropped {dict(dropped)}; "
        f"per category {dict(Counter(d['category'] for d, _ in added))}")
    questions = []
    for d in heldout:
        questions.append({
            "id": "dh-" + d["id"].split("-")[1], "tags": [d["category"]], "split": "heldout",
            "question": {"en": d["question"]},
            "gold": {"datalog": d["query"]},
        })
    (ROOT / "datasets/neurosynth-distill-heldout.yaml").write_text(
        "dataset: https://neurolang.github.io/text2query/2026/neurosynth-distill-heldout/\n"
        "engine: neurosynth\n"
        "description: >\n  Generated questions of scripts/distill.py kept out of "
        "the example bank. The gold is Sonnet 5.5's\n  ReAct query, kept when "
        "it returned rows and the judge (Opus 5.5)\n  accepted it.\n\n"
        + yaml.safe_dump({"questions": questions}, allow_unicode=True,
                         sort_keys=False, width=100)
    )
    log(f"held-out dataset: {len(questions)} questions")


# --- the other steps are added below ----------------------------------

COMMANDS = {"slots": cmd_slots, "pool": cmd_pool, "answer": cmd_answer,
            "filter": cmd_filter, "calibrate": cmd_calibrate,
            "bank": cmd_bank}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--data-dir", default=str(ROOT / "neurolang_data"))
    parser.add_argument("--shard", default="0/1", type=lambda v: tuple(map(int, v.split("/"))),
                        help="I/N: the I-th of N interleaved shards")
    parser.add_argument("--heldout-only", action="store_true",
                        help="bank: write the held-out dataset, not the bank")
    parser.add_argument("--limit", type=int, help="stop after N answers")
    parser.add_argument("--budget", type=int, default=2_800_000,
                        help="stop when Sonnet has used this many tokens")
    parser.add_argument("--round", type=int, default=1, choices=[1, 2])
    parser.add_argument("--config", help="answer: LLM config (default "
                        "configs/llm.master-v0.yaml)")
    parser.add_argument("--provider", default="openrouter")
    parser.add_argument("--tag", default="react.sonnet",
                        help="answer, round 2: name of the answer files")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--workers", type=int, default=1,
                        help="answer: processes forked after the engine build")
    parser.add_argument("--question-timeout", type=int, default=900,
                        help="answer, round 2: give a question up after "
                        "this many seconds")
    parser.add_argument("--lazy", action="store_true",
                        help="answer, round 2: skip the questions the "
                        "agreement gate decides without this answer")
    parser.add_argument("--max-usage", type=float, default=170.0,
                        help="answer, round 2: stop when the OpenRouter key "
                        "has spent this many dollars")
    args = parser.parse_args()
    global LEDGER
    if args.round == 2:
        LEDGER = ROUND2 / "tokens.jsonl"
    COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
