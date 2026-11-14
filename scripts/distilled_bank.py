"""
The distilled bank of the neurosynth engine (runs/nsv3e.md): the Sonnet
answers kept by distillation round 2 (runs/distill-round2.md) as entries
of NeuroLang's ``engines/neurosynth/examples.yaml``.

    # candidates, checked on the engine with the assistant's guard
    python scripts/distilled_bank.py check
    # the highest bge-m3 cosine of each to an evaluation question
    python scripts/distilled_bank.py leak
    # the bank of a variant: B (agreement only) or C (all kept), with traces
    python scripts/distilled_bank.py write C OUT.yaml [--traces]

``check`` keeps a kept answer (agreement, or Sonnet judge yes) unless:
- its question or its query (whitespace aside) is already in the bank of
  the engine or earlier in the candidates;
- it answers with ``mentions`` a question naming a Cognitive Atlas label
  with a definition, without saying mention, term or word (the
  Cognitive-Atlas-first rule of the golds, runs/nsv3d.md);
- its query, run with the assistant's limits (30 s, 4 GB), fails, is
  stopped or gives no rows.
``write`` also drops a candidate closer than 0.85 (bge-m3 cosine) to a
question of nsv2, v3, fresh or distill-heldout, in any language (``leak``).
A radius of 6 mm the question does not state is written
``{kernel_radius_mm}``, as in the hand-written bank. Queries run one at a
time (``data/distill/round2/bank_check.jsonl``, resumable).

A trace keeps the ``search_values`` / ``describe_predicate`` steps whose
observation shows a constant of the final query that the question does
not spell out: at most 3 steps, observations cut to 6 lines.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROUND2 = Path("data/distill/round2")
CHECK = ROUND2 / "bank_check.jsonl"
LEAK = ROUND2 / "bank_leakage.json"
LABELS = ROUND2 / "bank_cogat_labels.json"
SAYS_WORD = re.compile(r"mention|term|word|vocabular", re.I)
SIX_MM = re.compile(r"(<=\s*)6(\.0)?\)")
LITERAL = re.compile(r"'([^']+)'")


def norm(text):
    return " ".join(text.lower().split())


def kept():
    """Return the kept Sonnet answers, with their gate (``agreement``)."""
    judged = {
        j["id"]: j["verdict"]
        for j in map(json.loads, open(ROUND2 / "judge.sonnet.jsonl"))
    }
    out = []
    for answer in map(json.loads, open(ROUND2 / "react.sonnet.compact.jsonl")):
        status = answer["gate"]["status"]
        if status == "accepted" or (status == "disagreement"
                                    and judged.get(answer["id"])):
            answer["agreement"] = status == "accepted"
            out.append(answer)
    return out


def bank_query(answer):
    query = answer["query"].strip()
    if not re.search(r"\b6(\.0)?\s*mm", answer["question"]):
        query = SIX_MM.sub(r"\1{kernel_radius_mm})", query)
    return query


def trace(answer):
    literals = {
        v for v in LITERAL.findall(answer["query"])
        if v.lower() not in answer["question"].lower()
    }
    steps = []
    for step in answer["steps"]:
        if step["action"] not in ("search_values", "describe_predicate"):
            continue
        if not any(v in step["observation"] for v in literals):
            continue
        lines = step["observation"].splitlines()
        observation = "\n".join(lines[:6]) + ("\n…" if len(lines) > 6 else "")
        steps.append({"action": step["action"],
                      "arguments": step["arguments"],
                      "observation": observation})
    return steps[:3]


def mention_terms(answer):
    """The constants of a query using ``mentions`` for a question that does
    not say mention, term or word (e.g. ``term_association(s, 'reward')``)."""
    if "mentions(" not in answer["query"] or SAYS_WORD.search(
            answer["question"]):
        return []
    return LITERAL.findall(answer["query"])


def cogat_labels(nl, answers):
    """Return the ``mentions`` constants that are labels with a definition."""
    from text2query_bench.engine import execute

    terms = {t for a in answers for t in mention_terms(a)}
    found = set()
    for term in sorted(terms):
        for label in {term, term.rstrip("s")}:
            rows = execute(nl, f"ans(d) :- cogat_definition('{label}', d)",
                           "datalog").rows
            if rows:
                found.add(term)
    return found


def check(args):
    from neurolang_apps.utils.llm.examples import load_examples
    from neurolang_apps.utils.llm.validation import run_preview
    from text2query_bench.engine import build_engine

    bank = load_examples("neurosynth")
    questions = {norm(e.question) for e in bank}
    queries = {norm(e.query("datalog") or "") for e in bank}
    nl = build_engine("neurosynth", "neurolang_data")
    answers = kept()
    labels = cogat_labels(nl, answers)
    LABELS.write_text(json.dumps(sorted(labels)))
    print(f"cogat labels used with mentions: {sorted(labels)}", flush=True)
    done = {r["id"] for r in map(json.loads, open(CHECK))} if (
        CHECK.exists()) else set()
    with open(CHECK, "a") as out:
        for answer in answers:
            query = bank_query(answer)
            record = {"id": answer["id"], "agreement": answer["agreement"],
                      "category": answer["category"]}
            if norm(answer["question"]) in questions:
                record["drop"] = "duplicate question"
            elif norm(query) in queries:
                record["drop"] = "duplicate query"
            elif set(mention_terms(answer)) & labels:
                record["drop"] = "cogat label via mentions"
            questions.add(norm(answer["question"]))
            queries.add(norm(query))
            if "drop" not in record and answer["id"] not in done:
                runnable = query.replace("{kernel_radius_mm}", "6")
                preview = run_preview(nl, runnable, "datalog", rows=1,
                                      engine_name="neurosynth",
                                      timeout=30, memory_mb=4096)
                record.update(ok=preview.ok, rows=preview.rows,
                              message=preview.text[:200])
                if not (preview.ok and preview.rows):
                    record["drop"] = "guard, error or no rows"
            elif answer["id"] in done:
                continue
            out.write(json.dumps(record) + "\n")
            out.flush()
            print(record["id"], record.get("drop", "kept"), flush=True)


def leak(args):
    """The highest bge-m3 cosine of each candidate to an evaluation question."""
    sys.path.insert(0, "scripts")
    from leakage import embed
    from text2query_bench.dataset import load_dataset

    evaluation = [
        text for name in ("neurosynth-v2", "neurosynth-v3-heldout",
                          "neurosynth-v3-fresh", "neurosynth-distill-heldout")
        for q in load_dataset(f"datasets/{name}.yaml").questions
        for text in q.text.values()
    ]
    checked = {r["id"] for r in map(json.loads, open(CHECK)) if "drop" not in r}
    answers = [a for a in kept() if a["id"] in checked]
    cosines = embed([a["question"] for a in answers]) @ embed(evaluation).T
    out = {a["id"]: [round(float(row.max()), 3), evaluation[int(row.argmax())]]
           for a, row in zip(answers, cosines)}
    LEAK.write_text(json.dumps(out, indent=1))
    worst = max(out.items(), key=lambda kv: kv[1][0])
    print(f"max cosine {worst[1][0]} ({worst[0]}), "
          f"{sum(v[0] > 0.85 for v in out.values())} above 0.85")


def write(args):
    checked = {r["id"]: r for r in map(json.loads, open(CHECK))}
    leakage = json.loads(LEAK.read_text())
    labels = set(json.loads(LABELS.read_text()))
    entries = []
    for answer in kept():
        record = checked.get(answer["id"])
        if record is None or "drop" in record or leakage[answer["id"]][0] > 0.85:
            continue
        if set(mention_terms(answer)) & labels:
            continue  # checked before the labels covered every constant
        if args.variant == "B" and not answer["agreement"]:
            continue
        entry = {"question": answer["question"], "datalog": bank_query(answer)}
        steps = trace(answer) if args.traces else []
        if steps:
            entry["trace"] = steps
        entries.append(entry)

    class Dumper(yaml.SafeDumper):
        pass

    def text(dumper, value):
        style = "|" if "\n" in value else None
        return dumper.represent_scalar("tag:yaml.org,2002:str", value,
                                       style=style)

    Dumper.add_representer(str, text)
    header = (
        "# Questions on the neurosynth engine with their Datalog queries,\n"
        "# after the shared bank of coordinate_meta_analysis: Sonnet 5.5\n"
        "# answers of the distillation (neurolang-text2query-bench,\n"
        "# runs/distill-round2.md), kept when DeepSeek agreed"
        + (" or a judge accepted them" if args.variant == "C" else "")
        + ",\n# deduplicated and checked on the engine. A trace shows the\n"
        "# searches that found the query's constants.\n"
    )
    Path(args.out).write_text(header + yaml.dump(
        {"assistant_examples": entries}, Dumper=Dumper, sort_keys=False,
        allow_unicode=True, width=1000,
    ))
    print(f"{len(entries)} entries, "
          f"{sum('trace' in e for e in entries)} with a trace")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    sub.add_parser("leak")
    w = sub.add_parser("write")
    w.add_argument("variant", choices=["B", "C"])
    w.add_argument("out")
    w.add_argument("--traces", action="store_true")
    args = parser.parse_args()
    {"check": check, "leak": leak, "write": write}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
