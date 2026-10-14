"""
Scores of a system's answers against the gold answers.

As in TEXT2SPARQL, a question is scored by the precision, recall and F1
of the rows the system's query returns against the rows of the gold
query. Rows are compared as tuples of normalised values: strings as is,
numbers rounded. Since the columns of the two queries can be in another
order, or the system can return extra columns (e.g. the TF-IDF weight
with the study), the system's columns are matched to the gold columns:
of the projections of its rows on as many columns as the gold rows have,
in any order, the one with the best F1 is scored.
"""

import itertools
import math
from dataclasses import dataclass

DECIMALS = 4
MAX_ALIGNMENTS = 720


def normalise(value):
    """Return *value* in the form rows are compared in."""
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            value = value.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        if value.is_integer():
            return int(value)
        return round(value, DECIMALS)
    if isinstance(value, (int, str)):
        return value
    return str(value)


def normalise_rows(rows) -> set:
    """Return the set of the normalised *rows*."""
    return {tuple(normalise(v) for v in row) for row in rows}


@dataclass
class Score:
    """Precision, recall and F1 of an answer."""

    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0

    @property
    def exact(self) -> bool:
        """Whether the answer is exactly the gold answer."""
        return self.f1 == 1.0


def _prf(predicted: set, gold: set) -> Score:
    """Return the score of the *predicted* rows against the *gold* rows."""
    if not predicted and not gold:
        return Score(1.0, 1.0, 1.0)
    if not predicted or not gold:
        return Score()
    common = len(predicted & gold)
    precision = common / len(predicted)
    recall = common / len(gold)
    f1 = 0.0 if common == 0 else 2 * precision * recall / (precision + recall)
    return Score(precision, recall, f1)


def _arity(rows: set):
    """Return the number of columns of *rows*, or None if empty."""
    return len(next(iter(rows))) if rows else None


def alignments(predicted_arity: int, gold_arity: int):
    """Yield the column orders projecting predicted rows on the gold arity."""
    if predicted_arity < gold_arity:
        return
    for count, columns in enumerate(
        itertools.permutations(range(predicted_arity), gold_arity)
    ):
        if count >= MAX_ALIGNMENTS:
            return
        yield columns


def score(predicted_rows, gold_rows) -> Score:
    """
    Return the score of the *predicted_rows* against the *gold_rows*.

    The predicted columns are aligned with the gold ones (see the
    module), the best alignment being kept.
    """
    predicted = normalise_rows(predicted_rows)
    gold = normalise_rows(gold_rows)
    predicted_arity, gold_arity = _arity(predicted), _arity(gold)
    if predicted_arity is None or gold_arity is None:
        return _prf(predicted, gold)
    best = Score()
    for columns in alignments(predicted_arity, gold_arity):
        projected = {tuple(row[c] for c in columns) for row in predicted}
        candidate = _prf(projected, gold)
        if candidate.f1 > best.f1:
            best = candidate
            if best.exact:
                break
    return best


def mean(values) -> float:
    """Return the mean of *values*, 0 when there are none."""
    values = list(values)
    return sum(values) / len(values) if values else 0.0
