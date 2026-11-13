"""
A cheap judge cascade for distilled answers, on Albert's DeepSeek only, and
its calibration (runs/nsv3d-step1.md).

An answer (a candidate query of a question) is accepted:

1. by agreement: DeepSeek answers the question 3 times (ReAct, temperature
   0.7, the question left out of the example bank); the candidate is
   accepted when at least 2 of the 3 answers return its rows (the same
   rows, up to the order of the columns). Sampling stops as soon as the
   outcome is known (2 equal, or 2 different);
2. otherwise by two DeepSeek judges: the verifier's instructions, the
   engine's description, predicates and guidance, the question, the query
   and its first rows, answered by ``VERDICT: yes/no``; the second request
   gives the query before the question. Both yes: accepted; both no:
   rejected;
3. the split verdicts are flagged for a stronger judge (Sonnet), not called
   here.

Calibration cases (``cases``):

- distill: the 79 Sonnet ReAct answers of data/distill/filtered.json, with
  Opus's verdict (66 kept, 13 rejected);
- gold: the gold queries of neurosynth-v2 and neurosynth-v3-heldout (right)
  and up to 2 other answers of past runs per question whose rows, on the
  current engine, are not the gold's (wrong). Their DeepSeek answers are
  those of past DeepSeek runs (3 per question, never the run of the
  candidate), re-run on the current engine.

Every query is re-run on the current engine. Steps, each resumable (their
records are appended to data/cascade/):

    source scripts/env.sh; source scripts/nsv3d_env.sh
    $VENV/bin/python scripts/judge_cascade.py cases
    $VENV/bin/python scripts/judge_cascade.py agree [--shard 0/2] [--set distill]
    $VENV/bin/python scripts/judge_cascade.py judge
    $VENV/bin/python scripts/judge_cascade.py report

Albert's key is read from ALBERT_API_KEY, never printed; every LLM request
and its tokens go to data/cascade/ledger.jsonl.
"""

import argparse
import json
import os
import re
import sys
import threading
import time
from collections import Counter, defaultdict
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "cascade"
ALBERT = "https://albert.api.etalab.gouv.fr/v1"
DEEPSEEK = "deepseek-v4-flash-0731"
CONFIG = ROOT / "configs" / "llm.nsv3d.yaml"
SAMPLES = 3
WRONG_PER_QUESTION = 2
PREVIEW_ROWS = 10

DATASETS = {
    "nsv2": "datasets/neurosynth-v2.yaml",
    "v3": "datasets/neurosynth-v3-heldout.yaml",
}
# DeepSeek V4 Flash 0731 runs (English), most recent first: the answers
# agreement reuses.
DEEPSEEK_RUNS = {
    "nsv2": [
        "nsv3c-partial-30db798e/nsv3c-nsv2-deepseek",
        "nsv3b-nsv2-test-deepseek",
        "nsv3b-nsv2-dev-deepseek", "nsv2-final-v3work-deepseek",
        "nsv2-distill-after-deepseek", "nsv2-base-v3work-deepseek",
        "nsv2-distill-before-deepseek", "nsv2-test-verifix-v0-deepseek-or",
        "nsv2-dev-verifix-deepseek-or", "nsv2-test-master-deepseek-albert",
    ],
    "v3": [
        "nsv3d-dev-step0-deepseek-albert",
        "nsv3c-partial-30db798e/nsv3c-test-deepseek",
        "nsv3b-test-deepseek", "nsv3-test-final-deepseek",
        "nsv3-dev-r2-deepseek", "nsv3-dev-r1-deepseek",
        "nsv3-test-base-deepseek", "nsv3-dev-base-deepseek",
    ],
}
# Other models' runs, where the wrong answers come from first.
OTHER_RUNS = {
    "nsv2": [
        "nsv2-react-sonnet", "nsv2-test-master-sonnet",
        "nsv2-dev-master-sonnet", "nsv2-dev-lean-sonnet",
        "nsv2-test-master-gemma-or", "nsv2-dev-master-gemma-or",
        "nsv2-distill-after-gemma", "nsv2-react-gemma-or-test",
        "nsv2-react-gemma-or-dev",
    ],
    "v3": [
        "nsv3c-partial-30db798e/nsv3c-test-sonnet", "nsv3b-test-sonnet", "nsv3-test-final-sonnet",
        "nsv3-dev-base-sonnet",
    ],
}


def log(message):
    print(message, file=sys.stderr, flush=True)


def records(name):
    path = OUT / name
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


_lock = threading.Lock()


def append(name, record):
    OUT.mkdir(parents=True, exist_ok=True)
    with _lock, open(OUT / name, "a") as out:
        out.write(json.dumps(record, default=str) + "\n")


def squash(text):
    return " ".join((text or "").split())


def english_answers(run):
    """Return {id: answer} of the English answers of *run*."""
    path = ROOT / "runs" / run / "answers.json"
    if not path.exists():
        return {}
    return {
        a["id"]: a for a in json.loads(path.read_text())
        if a.get("language", "en") == "en"
    }


def exact_ids(run):
    """Return the ids of the exact answers of *run* when it was scored."""
    path = ROOT / "runs" / run / "results.json"
    if not path.exists():
        return set()
    return {
        r["id"] for r in json.loads(path.read_text())["results"]
        if r.get("language", "en") == "en" and r.get("f1") == 1.0
    }


# --- cases ---------------------------------------------------------------


def cmd_cases(args):
    from text2query_bench.dataset import load_dataset

    from neurolang_apps.utils.llm.examples import load_examples

    bank = {squash(e.question) for e in load_examples("neurosynth")}
    # past DeepSeek answers of the held-out distill questions (v3 dh-*)
    v3_answers = defaultdict(list)
    for run in DEEPSEEK_RUNS["v3"]:
        for a in english_answers(run).values():
            if a.get("query"):
                v3_answers[squash(a["question"])].append((run, a["query"]))
    cases = []
    for d in json.loads((ROOT / "data/distill/filtered.json").read_text()):
        cases.append({
            "case": f"distill/{d['id']}", "set": "distill", "qid": d["id"],
            "question": d["question"], "query": d["query"],
            "label": d["status"] == "kept", "source": "sonnet",
            "banked": squash(d["question"]) in bank, "split": d["split"],
            # judged by Opus under the 3 mm radius of 30db798e's guidance
            "radius": "euclidean" in d["query"] or "3 mm" in d["reason"],
            "samples": v3_answers[squash(d["question"])][:SAMPLES],
        })
    # the Opus-rejected and the questions out of the bank first
    cases.sort(key=lambda c: (c["set"] != "distill", c["label"] is True,
                              c.get("banked", False)))
    for name, path in DATASETS.items():
        dataset = load_dataset(ROOT / path)
        samples = {run: english_answers(run) for run in DEEPSEEK_RUNS[name]}
        others = {run: english_answers(run) for run in OTHER_RUNS[name]}
        exact = {run: exact_ids(run)
                 for run in [*DEEPSEEK_RUNS[name], *OTHER_RUNS[name]]}
        for q in dataset.questions:
            gold = q.gold["datalog"]
            pool = [
                (run, a[q.id]["query"]) for run, a in samples.items()
                if q.id in a and a[q.id].get("query")
            ]
            base = {"set": f"gold-{name}", "qid": q.id,
                    "question": q.text["en"], "split": q.split,
                    "banked": squash(q.text["en"]) in bank}
            cases.append({**base, "case": f"{name}/{q.id}/gold", "query": gold,
                          "label": True, "source": "gold",
                          "samples": pool[:SAMPLES]})
            wrong, seen = [], {squash(gold)}
            for run, answers in [*others.items(), *samples.items()]:
                a = answers.get(q.id)
                if (not a or not a.get("query") or q.id in exact[run]
                        or squash(a["query"]) in seen):
                    continue
                seen.add(squash(a["query"]))
                wrong.append((run, a["query"]))
            for run, query in wrong[:WRONG_PER_QUESTION]:
                cases.append({
                    **base, "case": f"{name}/{q.id}/{run.replace('/', ':')}", "query": query,
                    "label": None, "source": run,
                    "samples": [s for s in pool if s[0] != run][:SAMPLES],
                })
    (OUT / "cases.json").parent.mkdir(parents=True, exist_ok=True)
    (OUT / "cases.json").write_text(json.dumps(cases, indent=1))
    log(f"{len(cases)} cases: {Counter(c['set'] for c in cases)}")


# --- agreement -----------------------------------------------------------


def same_rows(a, b):
    """Whether rows *a* and *b* are the same, up to the order of columns."""
    from text2query_bench.metrics import score

    return score(a, b).exact and score(b, a).exact


def preview(execution):
    """Return the first rows of an execution as the agent shows them."""
    columns = ", ".join(execution.columns)
    lines = [f"{len(execution.rows)} rows; columns {columns}"]
    lines += ["  ".join(str(v) for v in row)
              for row in execution.rows[:PREVIEW_ROWS]]
    return "\n".join(lines)


class Engine:
    """The engine and its executions, cached by query text."""

    def __init__(self, data_dir):
        from text2query_bench.engine import build_engine

        log("Building the neurosynth engine...")
        self.nl = build_engine("neurosynth", data_dir)
        self.cache = {}

    def run(self, query):
        from text2query_bench.engine import execute

        key = squash(query)
        if key not in self.cache:
            if len(self.cache) > 8:
                self.cache.clear()  # results of a few million rows
            self.cache[key] = execute(self.nl, query, "datalog", 300.0)
        return self.cache[key]


def deepseek_answer(engine, question):
    """Return (query, usage) of a new DeepSeek ReAct answer."""
    from neurolang_apps.utils.llm import LLMError, load_config, make_agent

    config = load_config(CONFIG)
    provider = config.provider("albert-deepseek")
    config.assistant.verify_rounds = 0
    config.assistant.temperature = 0.7
    agent = make_agent(
        engine.nl, provider, config.assistant, "datalog", "react",
        engine_name="neurosynth", exclude_question=question,
    )
    try:
        result = agent.run(question)
    except LLMError as exc:
        log(f"  DeepSeek: {exc}")
        return None, {}
    usage = dict(result.usage)
    append("ledger.jsonl", {"model": DEEPSEEK, "purpose": "answer",
                            "time": time.time(), "in": usage.get("input", 0),
                            "out": usage.get("output", 0),
                            "calls": result.calls})
    return result.query or "", usage


def cmd_agree(args):
    from text2query_bench.metrics import score

    cases = json.loads((OUT / "cases.json").read_text())
    done = {r["case"] for r in records("agree.jsonl")}
    index, count = args.shard
    todo = [
        c for n, c in enumerate(cases)
        if n % count == index and c["case"] not in done
        and (not args.set or c["set"].startswith(args.set))
    ]
    engine = Engine(args.data_dir)
    if not (OUT / "schema.txt").exists():
        from neurolang_apps.utils.llm.context import EngineContext

        (OUT / "schema.txt").write_text(
            EngineContext(engine.nl, "neurosynth").schema_summary())
    gold_rows = {}
    for case in todo:
        start = time.perf_counter()
        candidate = engine.run(case["query"])
        record = {"case": case["case"], "label": case["label"],
                  "rows": len(candidate.rows), "error": candidate.error,
                  "preview": preview(candidate)}
        if case["source"] != "gold" and case["set"] != "distill":
            gold = gold_rows.get(case["qid"])
            if gold is None:
                gold_case = next(
                    c for c in cases if c["set"] == case["set"]
                    and c["qid"] == case["qid"] and c["source"] == "gold")
                gold = engine.run(gold_case["query"]).rows
            record["label"] = (not candidate.error
                               and score(candidate.rows, gold).exact)
        if case["source"] == "gold":
            gold_rows = {case["qid"]: candidate.rows}
        equal, forward, sources = [], [], []
        samples = list(case["samples"])
        def decided():
            return all(sum(v) >= 2 or v.count(False) >= 2
                       for v in (equal, forward))

        if candidate.error or not candidate.rows:
            samples = []  # not judged: the query must run and give rows
        while len(equal) < SAMPLES and not decided():
            if samples:
                source, query = samples.pop(0)
            elif case["set"] == "distill":
                source = "albert"
                query, _ = deepseek_answer(engine, case["question"])
                if query is None:
                    break
            else:
                break
            rows = engine.run(query).rows if query else []
            ok = bool(query) and not candidate.error
            equal.append(ok and same_rows(rows, candidate.rows))
            # agreement_gate.py's test: F1 = 1 of the sample's rows
            # against the candidate's
            forward.append(ok and score(rows, candidate.rows).exact)
            sources.append(source)
        if (case["set"] == "distill" and candidate.rows
                and not candidate.error and not decided()):
            log(f"{case['case']}: incomplete, left for a later run")
            continue
        record.update(equal=equal, forward=forward, sample_sources=sources,
                      agreed=sum(equal) >= 2,
                      agreed_forward=sum(forward) >= 2,
                      seconds=time.perf_counter() - start)
        append("agree.jsonl", record)
        log(f"{case['case']}: label={record['label']} rows={record['rows']} "
            f"equal={equal} agreed={record['agreed']}")


# --- judges --------------------------------------------------------------


class Albert:
    """DeepSeek on Albert, at most *per_minute* requests a minute."""

    def __init__(self, per_minute=6):
        self.key = os.environ["ALBERT_API_KEY"]
        self.interval = 60.0 / per_minute
        self.last = 0.0

    def __call__(self, messages, purpose):
        for attempt in range(6):
            with _lock:
                wait = self.last + self.interval - time.time()
                self.last = max(time.time(), self.last + self.interval)
            if wait > 0:
                time.sleep(wait)
            try:
                response = httpx.post(
                    f"{ALBERT}/chat/completions", timeout=300,
                    headers={"Authorization": f"Bearer {self.key}"},
                    json={"model": DEEPSEEK, "messages": messages,
                          "temperature": 0.0, "max_tokens": 4096},
                )
                response.raise_for_status()
                data = response.json()
                text = data["choices"][0]["message"]["content"] or ""
                if not text.strip():
                    raise ValueError("empty reply")
                break
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                log(f"{purpose}: {type(exc).__name__}, retry {attempt}")
                time.sleep(10 * (attempt + 1))
        else:
            raise RuntimeError(f"Albert kept failing for {purpose}")
        usage = data.get("usage", {})
        append("ledger.jsonl", {
            "model": DEEPSEEK, "purpose": purpose, "time": time.time(),
            "in": usage.get("prompt_tokens", 0),
            "out": usage.get("completion_tokens", 0), "calls": 1,
        })
        return text


def judge_context():
    """Return the system prompt of the judges, as the Opus judge's."""
    from neurolang_apps.utils import engine_registry
    from neurolang_apps.utils.llm import prompts
    schema_file = OUT / "schema.txt"  # written by agree
    config = engine_registry.get_engine_config("neurosynth")
    description = " ".join(config.get("description", "").split())
    guidance = " ".join(config.get("assistant_guidance", "").split())
    radius = str(config.get("kernel_radius_mm", ""))
    description = description.replace("{kernel_radius_mm}", radius)
    guidance = guidance.replace("{kernel_radius_mm}", radius)
    return (
        f"{prompts.VERIFICATION}\n\n# The engine\n{description}\n\n"
        f"# Predicates of the engine\n{schema_file.read_text()}\n\n"
        f"# How to answer on this engine\n{guidance}"
    )


_VERDICT = re.compile(r"VERDICT\s*:\s*\**\s*(yes|no)\b", re.I)


def verdict(text):
    found = _VERDICT.findall(text)
    return found[-1].lower() == "yes" if found else None


def judge_messages(system, question, query, rows, swapped):
    parts = [f"# Question\n{question}",
             f"# Query\n{query}\n\n# First rows of its answer\n{rows}"]
    if swapped:
        parts.reverse()
    return [{"role": "system", "content": system},
            {"role": "user", "content": "\n\n".join(parts)}]


def cmd_judge(args):
    from concurrent.futures import ThreadPoolExecutor

    cases = {c["case"]: c for c in json.loads((OUT / "cases.json").read_text())}
    agreed = {r["case"]: r for r in records("agree.jsonl")}
    done = {(r["case"], r["swapped"]) for r in records("judge.jsonl")}
    system = judge_context()
    albert = Albert(args.per_minute)
    jobs = [
        (case, swapped) for case, r in agreed.items()
        if not r["agreed"] and not r["error"] and r["rows"]
        for swapped in (False, True)
        if (case, swapped) not in done
    ]
    log(f"{len(jobs)} judge requests")

    def one(job):
        case, swapped = job
        c, r = cases[case], agreed[case]
        messages = judge_messages(system, c["question"], c["query"],
                                  r["preview"], swapped)
        text = albert(messages, "judge")
        if verdict(text) is None:  # no VERDICT line: asked once more
            text = albert(messages, "judge")
        append("judge.jsonl", {"case": case, "swapped": swapped,
                               "verdict": verdict(text),
                               "reason": " ".join(text.split())[-500:]})
        log(f"{case} swapped={swapped}: {verdict(text)}")

    with ThreadPoolExecutor(args.threads) as pool:
        list(pool.map(one, jobs))


# --- report --------------------------------------------------------------


def outcome(agree, verdicts):
    """Return the cascade's outcome of a case."""
    if agree["agreed"]:
        return "accepted by agreement"
    if False not in verdicts or True not in verdicts:
        return "pending"
    pair = (verdicts[False], verdicts[True])
    if pair == (True, True):
        return "accepted by judges"
    if pair == (False, False):
        return "rejected by judges"
    return "flagged"


def cmd_report(args):
    cases = {c["case"]: c for c in json.loads((OUT / "cases.json").read_text())}
    agreed = {r["case"]: r for r in records("agree.jsonl")}
    verdicts = defaultdict(dict)
    for r in records("judge.jsonl"):
        verdicts[r["case"]][r["swapped"]] = r["verdict"]
    groups = defaultdict(list)
    skipped = Counter()
    for case, agree in agreed.items():
        c = cases[case]
        if agree["error"] or not agree["rows"]:
            # the cascade judges only queries that run and return rows
            skipped[c["set"]] += 1
            continue
        label = agree["label"]
        result = outcome(agree, verdicts[case])
        groups[c["set"]].append((c, label, result))
        if c["set"] == "distill":
            groups["distill, banked" if c["banked"] else
                   "distill, not banked"].append((c, label, result))
            if not c["radius"]:
                groups["distill, radius-free"].append((c, label, result))
        else:
            groups["gold, both"].append((c, label, result))
    print("| set | cases | right | agreement | judges yes | judges no | "
          "flagged | pending | accept precision | accept recall | "
          "agreement with label (flagged as right / wrong) |")
    print("|---|" + "---:|" * 10)
    for group, items in groups.items():
        count = Counter(r for _, _, r in items)
        right = sum(bool(l) for _, l, _ in items)
        accepted = [l for _, l, r in items if r.startswith("accepted")]
        settled = [(l, r) for _, l, r in items if r not in ("flagged", "pending")]
        precision = sum(map(bool, accepted)) / len(accepted) if accepted else 0
        recall = sum(map(bool, accepted)) / right if right else 0
        hit = sum(bool(l) == r.startswith("accepted") for l, r in settled)
        flagged = count["flagged"]
        best = hit + flagged
        print(f"| {group} | {len(items)} | {right} | "
              f"{count['accepted by agreement']} | "
              f"{count['accepted by judges']} | "
              f"{count['rejected by judges'] + count['rejected (no rows)']} | "
              f"{flagged} | {count['pending']} | {precision:.3f} | "
              f"{recall:.3f} | {hit}/{len(settled)} settled "
              f"({best / len(items):.3f} if Sonnet settles the flagged right, "
              f"{hit / len(items):.3f} if wrong) |")
    print("\nFalse accepts and false rejects by the source of the candidate:")
    errors = Counter()
    for case, agree in agreed.items():
        c = cases[case]
        if case in [k for k in skipped]:
            continue
        result = outcome(agree, verdicts[case])
        if result in ("flagged", "pending") or agree["error"] or not agree["rows"]:
            continue
        accepted = result.startswith("accepted")
        if accepted != bool(agree["label"]):
            kind = "false accept" if accepted else "false reject"
            source = c["source"].split(":")[-1].split("/")[-1]
            errors[(c["set"], kind, result.split(" by ")[-1], source)] += 1
    for key, n in sorted(errors.items()):
        print(f"- {' / '.join(key)}: {n}")
    forward = Counter(
        (cases[k]["set"], r.get("agreed"), r.get("agreed_forward"))
        for k, r in agreed.items() if "agreed_forward" in r)
    print("\nAgreement, symmetric vs one-directional F1 = 1 (agreement_gate.py):"
          f" {dict(forward)}")
    if args.verbose:
        for group, items in groups.items():
            for c, label, result in items:
                if bool(label) != result.startswith("accepted"):
                    print(f"- {group} {c['case']} label={label}: {result}")
    print(f"\nLeft out (the query fails or returns no rows): {dict(skipped)}")
    ledger = records("ledger.jsonl")
    print(f"\nAlbert DeepSeek: {len(ledger)} records, "
          f"{sum(r.get('calls', 1) for r in ledger)} requests, "
          f"{sum(r['in'] for r in ledger)} in, "
          f"{sum(r['out'] for r in ledger)} out tokens")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["cases", "agree", "judge", "report"])
    parser.add_argument("--data-dir", default=str(ROOT / "neurolang_data"))
    parser.add_argument("--shard", default="0/1",
                        type=lambda v: tuple(map(int, v.split("/"))))
    parser.add_argument("--set", help="agree: only the cases of this set")
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--per-minute", type=int, default=6)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    {"cases": cmd_cases, "agree": cmd_agree, "judge": cmd_judge,
     "report": cmd_report}[args.command](args)


if __name__ == "__main__":
    main()
