"""
Command line of the benchmark: ``t2q-bench``.

    t2q-bench check-gold                   # run the gold queries, cache them
    t2q-bench run --strategy react --provider claude-code
    t2q-bench ask --endpoint http://localhost:8000/ -o runs/x/answers.json
    t2q-bench evaluate runs/x/answers.json
    t2q-bench serve --strategy icl --provider albert
    t2q-bench report runs/*/results.json

The engine is built once per command (the NeuroSynth engine takes about
a minute and a half); ``--data-dir`` is its data directory.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from .dataset import load_dataset
from .report import comparison_report, failures_report, run_report
from .runner import (
    ask,
    evaluate,
    gold_answers,
    results_as_dicts,
    summary,
    write_json,
)

DEFAULT_DATASET = Path("datasets/neurosynth.yaml")


def _log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _engine(args, dataset):
    from .engine import build_engine

    _log(f"Building the {dataset.engine} engine...")
    start = time.perf_counter()
    nl = build_engine(dataset.engine, args.data_dir, dataset.engines_file)
    _log(f"Built in {time.perf_counter() - start:.0f} s.")
    return nl


def _gold_path(dataset) -> Path:
    return dataset.path.with_suffix(".gold.json")


def _gold(args, nl, dataset) -> dict:
    """Return the gold rows, from the cache when it is up to date."""
    if dataset.metric == "text2sparql":
        return gold_answers(nl, dataset)
    path = _gold_path(dataset)
    if path.exists() and path.stat().st_mtime >= dataset.path.stat().st_mtime:
        gold = json.loads(path.read_text(encoding="utf-8"))
        if set(gold) == {q.id for q in dataset.questions}:
            for entry in gold.values():
                entry["rows"] = [tuple(row) for row in entry["rows"]]
            return gold
    _log("Running the gold queries...")
    gold = gold_answers(nl, dataset)
    write_json(path, gold)
    return gold


def _questions(args, dataset):
    return dataset.select(args.ids, args.tags)[: args.limit or None]


def _examples(args, dataset):
    """Return the few-shot examples of ``--examples-from``, if any."""
    from .systems import gold_examples

    source = getattr(args, "examples_from", None)
    if not source:
        return None
    other = dataset if source == "self" else load_dataset(source)
    return gold_examples(other, args.query_language)


def _system(args, nl, dataset):
    from .systems import AssistantSystem, EndpointSystem, engine_description

    if getattr(args, "endpoint", None):
        return EndpointSystem(
            args.endpoint, dataset.uri, args.name or "endpoint",
            args.query_language,
        )
    return AssistantSystem(
        nl, dataset.engine, args.query_language, args.provider,
        args.strategy, args.llm_config,
        examples=_examples(args, dataset),
        description=engine_description(dataset),
    )


def _previous_answers(args, path: Path) -> list:
    """Return the answers of the run to resume, if ``--resume``."""
    if getattr(args, "resume", False) and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def _saving(path: Path):
    """Return the progress callback printing and saving the answers."""
    def progress(answer, answers):
        _print_answer(answer)
        write_json(path, answers)
    return progress


def _print_answer(answer: dict) -> None:
    status = "ok" if answer["valid"] else "INVALID"
    _log(
        f"[{answer['id']} {answer['language']}] {status} "
        f"{answer['seconds']:.0f} s, {answer['calls']} calls: "
        f"{' '.join(answer['query'].split())[:120]}"
    )


def _print_result(result) -> None:
    _log(
        f"[{result.id} {result.language}] F1 {result.f1:.2f} "
        f"({result.rows} rows / {result.gold_rows} gold)"
        + (f" {result.error[:100]}" if result.error else "")
    )


def _evaluate_and_write(args, nl, dataset, answers, out_dir: Path) -> None:
    gold = _gold(args, nl, dataset)
    results = evaluate(
        nl, dataset, answers, gold, args.timeout, _print_result
    )
    scores = summary(dataset, results)
    write_json(out_dir / "results.json", {
        "dataset": dataset.uri, "summary": scores,
        "results": results_as_dicts(results),
    })
    name = answers[0]["system"] if answers else out_dir.name
    report = run_report(name, scores) + "\n" + failures_report(
        results_as_dicts(results), limit=0
    )
    (out_dir / "report.md").write_text(report, encoding="utf-8")
    print(run_report(name, scores))


def cmd_import(args) -> int:
    from .text2sparql import SETS, write_dataset

    for name in args.sets or sorted(SETS):
        path = write_dataset(name)
        _log(f"Wrote {path}")
    return 0


def cmd_build_dbpedia(args) -> int:
    from .dataset import load_dataset as load
    from .dbpedia_subgraph import Endpoint, build, write

    from .text2sparql import load_gold

    questions, answers = [], set()
    for path in args.datasets:
        dataset = load(path)
        questions += [
            (q.id, q.gold["sparql"]) for q in dataset.questions
            if q.gold.get("sparql")
        ]
        for values in load_gold(dataset.gold_results).values():
            if isinstance(values, dict):
                answers |= {v for v in values if v.startswith("http")}
    graph = build(questions, Endpoint(args.endpoint), _log, answers)
    write(graph, args.output)
    _log(f"Wrote {len(graph)} triples to {args.output}")
    return 0


def cmd_check_translations(args, dataset, nl) -> int:
    from .text2sparql import check_translations

    checks = check_translations(nl, dataset, args.timeout)
    counts = {}
    for check in checks:
        counts[check["status"]] = counts.get(check["status"], 0) + 1
        if check["status"] != "missing":
            detail = check.get("detail", "")
            print(
                f"{check['status']:<8} {check['id']}: F1 "
                f"{check['f1']:.2f} {detail}"
            )
    print(", ".join(f"{n} {status}" for status, n in sorted(counts.items())))
    write_json(dataset.path.with_suffix(".translations.json"), checks)
    return 0


def cmd_check_gold(args) -> int:
    dataset = load_dataset(args.dataset)
    nl = _engine(args, dataset)
    if dataset.metric == "text2sparql":
        return cmd_check_translations(args, dataset, nl)
    gold = gold_answers(nl, dataset, args.timeout)
    failed = 0
    for question_id, entry in gold.items():
        if entry["error"]:
            failed += 1
            print(f"FAIL {question_id}: {entry['error']}")
        else:
            print(
                f"ok   {question_id}: {len(entry['rows'])} rows "
                f"({entry['seconds']:.1f} s)"
            )
            if not entry["rows"]:
                print(f"     warning: {question_id} has no gold rows")
    write_json(_gold_path(dataset), gold)
    return 1 if failed else 0


def cmd_ask(args) -> int:
    dataset = load_dataset(args.dataset)
    nl = None if args.endpoint else _engine(args, dataset)
    system = _system(args, nl, dataset)
    output = Path(args.output)
    answers = ask(
        system, dataset, args.languages, _questions(args, dataset),
        _saving(output), _previous_answers(args, output),
    )
    write_json(output, answers)
    return 0


def cmd_evaluate(args) -> int:
    dataset = load_dataset(args.dataset)
    answers = json.loads(Path(args.answers).read_text(encoding="utf-8"))
    nl = _engine(args, dataset)
    _evaluate_and_write(args, nl, dataset, answers, Path(args.answers).parent)
    return 0


def cmd_run(args) -> int:
    dataset = load_dataset(args.dataset)
    nl = _engine(args, dataset)
    system = _system(args, nl, dataset)
    out_dir = Path(args.output or f"runs/{system.name}")
    path = out_dir / "answers.json"
    answers = ask(
        system, dataset, args.languages, _questions(args, dataset),
        _saving(path), _previous_answers(args, path),
    )
    write_json(path, answers)
    _evaluate_and_write(args, nl, dataset, answers, out_dir)
    return 0


def cmd_serve(args) -> int:
    from .server import make_server

    dataset = load_dataset(args.dataset)
    nl = _engine(args, dataset)
    system = _system(args, nl, dataset)
    server = make_server(system, [dataset.uri], args.host, args.port)
    _log(
        f"Serving {system.name} on http://{args.host}:{args.port}/ "
        f"for dataset {dataset.uri}"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def cmd_report(args) -> int:
    runs = {}
    for path in args.results:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        system = (data["results"][0]["system"] if data["results"]
                  else "")
        dataset = data.get("dataset", "").rstrip("/").split("/")[-1]
        runs[f"{Path(path).parent.name} ({system}, {dataset})"] = (
            data["summary"]
        )
    print(comparison_report(runs))
    return 0


def _add_selection(parser) -> None:
    parser.add_argument(
        "--resume", action="store_true",
        help="keep the answers of an interrupted run (answers.json) and "
        "ask the questions it failed to",
    )
    parser.add_argument("--lang", dest="languages", nargs="+",
                        default=["en"], help="natural languages (en fr)")
    parser.add_argument("--ids", nargs="+", help="question ids to ask")
    parser.add_argument("--tags", nargs="+", help="question tags to ask")
    parser.add_argument("--limit", type=int, help="ask the first N only")


def _add_system(parser) -> None:
    parser.add_argument("--strategy", choices=("react", "icl"))
    parser.add_argument("--provider", help="LLM provider of the config")
    parser.add_argument("--llm-config", help="LLM configuration file")
    parser.add_argument("--query-language", default="datalog",
                        choices=("datalog", "squall"))
    parser.add_argument(
        "--examples-from", metavar="DATASET",
        help="few-shot examples from the gold queries of DATASET (a dataset "
        "file, or 'self': the other questions of the dataset)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="t2q-bench", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--data-dir", default="neurolang_data",
                        help="data directory of the NeuroLang engines")
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="time limit of a query, in seconds")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser(
        "check-gold",
        help="run and cache the gold queries; for a TEXT2SPARQL set, "
        "check the Datalog translations against the official answers",
    )

    dbpedia_parser = commands.add_parser(
        "build-dbpedia-subgraph",
        help="fetch the DBpedia subgraph of the DBpedia question sets",
    )
    dbpedia_parser.add_argument(
        "datasets", nargs="*",
        default=["datasets/db25.yaml", "datasets/db26.yaml"],
    )
    dbpedia_parser.add_argument(
        "--endpoint", default="http://141.57.8.18:9081/sparql"
    )
    dbpedia_parser.add_argument(
        "-o", "--output", default="data/dbpedia-subgraph.ttl"
    )

    import_parser = commands.add_parser(
        "import-text2sparql", help="import TEXT2SPARQL question sets"
    )
    import_parser.add_argument(
        "sets", nargs="*", help="ck25 ck26 db25 db26 (default: all)"
    )

    ask_parser = commands.add_parser("ask", help="collect a system's queries")
    _add_system(ask_parser)
    _add_selection(ask_parser)
    ask_parser.add_argument("--endpoint", help="TEXT2SPARQL-style endpoint")
    ask_parser.add_argument("--name", help="name of the endpoint system")
    ask_parser.add_argument("-o", "--output", required=True)

    evaluate_parser = commands.add_parser("evaluate", help="score answers")
    evaluate_parser.add_argument("answers")

    run_parser = commands.add_parser("run", help="ask and evaluate")
    _add_system(run_parser)
    _add_selection(run_parser)
    run_parser.add_argument("--endpoint", help="TEXT2SPARQL-style endpoint")
    run_parser.add_argument("--name", help="name of the endpoint system")
    run_parser.add_argument("-o", "--output", help="run directory")

    serve_parser = commands.add_parser("serve", help="serve a system")
    _add_system(serve_parser)
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)

    report_parser = commands.add_parser("report", help="compare runs")
    report_parser.add_argument("results", nargs="+")
    return parser


COMMANDS = {
    "import-text2sparql": cmd_import,
    "build-dbpedia-subgraph": cmd_build_dbpedia,
    "check-gold": cmd_check_gold, "ask": cmd_ask, "evaluate": cmd_evaluate,
    "run": cmd_run, "serve": cmd_serve, "report": cmd_report,
}


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return COMMANDS[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
