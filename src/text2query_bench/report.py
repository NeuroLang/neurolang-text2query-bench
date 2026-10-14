"""Markdown reports of benchmark runs."""

COLUMNS = (
    ("F1", "f1", "{:.3f}"), ("P", "precision", "{:.3f}"),
    ("R", "recall", "{:.3f}"), ("exact", "exact", "{:.0%}"),
    ("valid", "valid", "{:.0%}"), ("runs", "executed", "{:.0%}"),
    ("calls", "calls", "{:.1f}"), ("tokens", "tokens", "{:.0f}"),
    ("s/question", "seconds", "{:.1f}"),
)


def _row(label: str, scores: dict) -> str:
    cells = [fmt.format(scores[key]) for _, key, fmt in COLUMNS]
    return f"| {label} | {scores['questions']} | " + " | ".join(cells) + " |"


def _table(title: str, rows) -> list:
    header = "| " + title + " | n | " + " | ".join(c for c, _, _ in COLUMNS)
    rule = "|---|---:|" + "---:|" * len(COLUMNS)
    return [header + " |", rule, *(_row(label, s) for label, s in rows)]


def run_report(name: str, summary: dict) -> str:
    """Return the report of one run: overall, per language, per tag."""
    lines = [f"## {name}", ""]
    lines += _table("", [("all", summary["overall"])])
    lines += ["", *_table("language", summary["languages"].items())]
    lines += ["", *_table("tag", summary["tags"].items())]
    return "\n".join(lines) + "\n"


def comparison_report(runs: dict) -> str:
    """Return the table comparing the overall scores of several runs."""
    lines = ["## Systems", ""]
    lines += _table(
        "system", [(name, s["overall"]) for name, s in runs.items()]
    )
    return "\n".join(lines) + "\n"


def failures_report(results: list, limit: int = 50) -> str:
    """Return the answers that are not exact, with their errors."""
    lines = ["## Answers that are not exact", ""]
    for result in results[:limit] if limit else results:
        if result["f1"] == 1.0:
            continue
        lines.append(
            f"- **{result['id']}** ({result['language']}) "
            f"F1 {result['f1']:.2f}, {result['rows']} rows vs "
            f"{result['gold_rows']} gold"
        )
        if result["query"]:
            query = result["query"].replace("\n", "\n    ")
            lines.append(f"\n    {query}\n")
        if result["error"]:
            lines.append(f"  error: {result['error'][:300]}")
    return "\n".join(lines) + "\n"
