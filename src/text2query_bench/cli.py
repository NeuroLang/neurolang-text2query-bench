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
    nl = build_engine(dataset.engine, args.data_dir)
    _log(f"Built in {time.perf_counter() - start:.0f} s.")
    return nl


def _gold_path(dataset) -> Path:
    return dataset.path.with_suffix(".gold.json")


def _gold(args, nl, dataset) -> dict:
    """Return the gold rows, from the cache when it is up to date."""
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


def _system(args, nl, dataset):
    from .systems import AssistantSystem, EndpointSystem

    if getattr(args, "endpoint", None):
        return EndpointSystem(
            args.endpoint, dataset.uri, args.name or "endpoint",
            args.query_language,
        )
    return AssistantSystem(
        nl, dataset.engine, args.query_language, args.provider,
        args.strategy, args.llm_config,
    )


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


def cmd_check_gold(args) -> int:
    dataset = load_dataset(args.dataset)
    nl = _engine(args, dataset)
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
    answers = ask(
        system, dataset, args.languages, _questions(args, dataset),
        _print_answer,
    )
    write_json(args.output, answers)
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
    answers = ask(
        system, dataset, args.languages, _questions(args, dataset),
        _print_answer,
    )
    write_json(out_dir / "answers.json", answers)
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
                  else Path(path).parent.name)
        runs[system] = data["summary"]
    print(comparison_report(runs))
    return 0


def _add_selection(parser) -> None:
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="t2q-bench", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--data-dir", default="neurolang_data",
                        help="data directory of the NeuroLang engines")
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="time limit of a query, in seconds")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("check-gold", help="run and cache the gold queries")

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
    "check-gold": cmd_check_gold, "ask": cmd_ask, "evaluate": cmd_evaluate,
    "run": cmd_run, "serve": cmd_serve, "report": cmd_report,
}


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return COMMANDS[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
