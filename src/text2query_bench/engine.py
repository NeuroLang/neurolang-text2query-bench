"""
Running queries on a NeuroLang engine for the benchmark.

Queries run in a scope of the engine that is discarded afterwards, so
that the rules of a system's query never change those of the next one,
and with a time limit: a query still running after it is interrupted
(see :func:`run_with_timeout`).
"""

import contextlib
import ctypes
import io
import threading
import time
import warnings
from dataclasses import dataclass, field
from pathlib import Path


class QueryTimeout(Exception):
    """Raised in a query that ran longer than its time limit."""


def build_engine(name: str, data_dir, engines_file=None):
    """
    Return the engine *name* of the NeuroLang registry.

    The engine is that of *engines_file*, an engines YAML file, when
    given, else of NeuroLang's own engines.
    """
    from neurolang.utils import engine_registry

    return engine_registry.build_engine(
        name, Path(data_dir), None,
        yaml_path=Path(engines_file) if engines_file else None,
    )


def run_with_timeout(function, timeout: float):
    """
    Return ``function()``, interrupting it after *timeout* seconds.

    The function runs in a worker thread, in which :class:`QueryTimeout`
    is raised when the time is up: it stops as soon as it runs Python
    code again, so that the engine is free for the next query.
    """
    outcome = {}
    done = threading.Event()

    def target():
        try:
            outcome["value"] = function()
        except BaseException as exc:
            outcome["error"] = exc
        finally:
            done.set()

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    if not done.wait(timeout):
        ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_ulong(worker.ident), ctypes.py_object(QueryTimeout)
        )
        done.wait()
    if "error" in outcome:
        raise outcome["error"]
    return outcome.get("value")


@dataclass
class Execution:
    """The rows of a query, or the error it raised, and its duration."""

    rows: list = field(default_factory=list)
    columns: list = field(default_factory=list)
    error: str = ""
    seconds: float = 0.0

    @property
    def ok(self) -> bool:
        return not self.error


def _last_result(result):
    """Return the result of the last ``obtain`` of a SQUALL program."""
    if isinstance(result, dict):
        return list(result.values())[-1] if result else None
    return result


def execute(
    nl, query: str, language: str, timeout: float = 120.0,
    unknown_is_empty: bool = False,
):
    """
    Run *query* in *language* on the engine *nl* and return its rows.

    With *unknown_is_empty*, a query on a predicate the engine does not
    have returns no rows, as SPARQL does, instead of failing.
    """
    from neurolang.exceptions import SymbolNotFoundError

    from neurolang.utils.cli import result_to_dataframe

    run = (
        nl.execute_squall_program if language == "squall"
        else nl.execute_datalog_program
    )

    def scoped():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with contextlib.redirect_stdout(io.StringIO()):
                with nl.scope:
                    return run(query)

    start = time.perf_counter()
    try:
        result = _last_result(run_with_timeout(scoped, timeout))
    except SymbolNotFoundError as exc:
        if not unknown_is_empty:
            return Execution(
                error=f"{type(exc).__name__}: {exc}"[:500],
                seconds=time.perf_counter() - start,
            )
        return Execution(seconds=time.perf_counter() - start)
    except QueryTimeout:
        return Execution(
            error=f"timeout after {timeout:.0f} s",
            seconds=time.perf_counter() - start,
        )
    except Exception as exc:
        return Execution(
            error=f"{type(exc).__name__}: {exc}".strip()[:500],
            seconds=time.perf_counter() - start,
        )
    seconds = time.perf_counter() - start
    if result is None:
        return Execution(seconds=seconds)
    if isinstance(result, bool):
        return Execution([(result,)], ["result"], seconds=seconds)
    frame = result_to_dataframe(result)
    return Execution(
        [tuple(row) for row in frame.itertuples(index=False)],
        [str(c) for c in frame.columns], seconds=seconds,
    )
