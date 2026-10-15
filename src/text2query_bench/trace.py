"""
Tracing the requests a system sends to its LLM, to debug a run.

:class:`TracingClient` wraps the chat client of the assistant and
reports each request and reply to a :class:`Tracer`. The tracer writes
one JSON Lines file per question, ``<id>-<language>.jsonl``, in its
directory, and prints the events when it has a :class:`Printer`.

``t2q-bench watch RUN_DIR`` follows the trace of the question being
asked by a run started with ``--trace``, from another terminal
(:func:`watch`).

The events are dicts with an ``event`` key:

* ``question``: ``id``, ``language`` and ``text`` of the question;
* ``request``: the ``call`` number, the ``messages`` added to the
  conversation since the previous request (from index ``start``; all of
  them when the conversation is a new one), the ``tools`` offered and
  the ``temperature``;
* ``reply``: the ``call`` number, ``text``, ``tool_calls``, ``usage``
  and ``seconds``, or ``error`` when the request failed;
* ``answer``: the ``query`` of the system, ``valid`` and ``error``.
"""

import json
import sys
import time
from pathlib import Path
from typing import Optional


class Tracer:
    """
    Records the events of the questions, in *directory* and on *printer*.

    Either may be ``None``. :meth:`begin` starts the trace of a question:
    its file is rewritten when the question is asked again.
    """

    def __init__(self, directory=None, printer: Optional["Printer"] = None):
        self.directory = Path(directory) if directory else None
        self.printer = printer
        self._file = None

    def begin(self, question_id: str, language: str, text: str) -> None:
        """Start the trace of the question *question_id* in *language*."""
        self.close()
        if self.directory:
            self.directory.mkdir(parents=True, exist_ok=True)
            path = self.directory / f"{question_id}-{language}.jsonl"
            self._file = path.open("w", encoding="utf-8")
        self.emit({
            "event": "question", "id": question_id, "language": language,
            "text": text,
        })

    def end(self, answer: dict) -> None:
        """End the trace of the question with the system's *answer*."""
        self.emit({
            "event": "answer", "query": answer.get("query", ""),
            "valid": bool(answer.get("valid")),
            "error": answer.get("error", ""),
        })
        self.close()

    def emit(self, event: dict) -> None:
        """Record *event*."""
        event = {"time": time.time(), **event}
        if self._file:
            self._file.write(
                json.dumps(event, ensure_ascii=False, default=str) + "\n"
            )
            self._file.flush()
        if self.printer:
            self.printer.show(event)

    def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None


class TracingClient:
    """The chat *client* reporting its requests and replies to *tracer*."""

    def __init__(self, client, tracer: Tracer):
        self.client = client
        self.tracer = tracer
        self.calls = 0
        self._previous = []

    def complete(self, messages, tools=None, temperature=0.0):
        self.calls += 1
        call = self.calls
        start = len(self._previous)
        if messages[:start] != self._previous:
            start = 0
        self._previous = list(messages)
        self.tracer.emit({
            "event": "request", "call": call, "start": start,
            "messages": messages[start:],
            "tools": [_tool_name(tool) for tool in tools or ()],
            "temperature": temperature,
        })
        began = time.perf_counter()
        try:
            reply = self.client.complete(messages, tools, temperature)
        except Exception as exc:
            self.tracer.emit({
                "event": "reply", "call": call, "error": str(exc),
                "seconds": time.perf_counter() - began,
            })
            raise
        self.tracer.emit({
            "event": "reply", "call": call, "text": reply.text,
            "tool_calls": [
                {"id": c.id, "name": c.name, "arguments": c.arguments}
                for c in reply.tool_calls
            ],
            "usage": reply.usage, "seconds": time.perf_counter() - began,
        })
        return reply

    def close(self) -> None:
        self.client.close()


def _tool_name(tool: dict) -> str:
    """Return the name of *tool*, in the OpenAI or Anthropic format."""
    return tool.get("name") or tool.get("function", {}).get("name", "?")


class Printer:
    """
    Prints the events of a trace on *stream*.

    Messages are cut to *limit* characters, and system prompts to
    *system_limit*, unless *full*.
    """

    def __init__(self, stream=None, full: bool = False, limit: int = 4000,
                 system_limit: int = 800):
        self.stream = stream or sys.stderr
        self.full = full
        self.limit = limit
        self.system_limit = system_limit
        self.color = getattr(self.stream, "isatty", lambda: False)()

    def show(self, event: dict) -> None:
        show = getattr(self, f"_{event.get('event')}", None)
        if show:
            show(event)
            self.stream.flush()

    def note(self, text: str) -> None:
        """Print *text*, a remark of the printer rather than an event."""
        self._write(self._paint(text, "2"))
        self.stream.flush()

    def _question(self, event):
        self._rule("═", f"{event['id']} [{event['language']}] "
                        f"{event['text']}", "1")

    def _request(self, event):
        tools = ", ".join(event["tools"]) or "none"
        self._rule("─", f"call {event['call']} → "
                        f"{len(event['messages'])} new message(s) from "
                        f"#{event['start']}, tools: {tools}", "36")
        for message in event["messages"]:
            self._message(message)

    def _reply(self, event):
        if "error" in event:
            self._rule("─", f"call {event['call']} ← failed after "
                            f"{event['seconds']:.1f} s", "31")
            self._write(event["error"])
            return
        usage = ", ".join(f"{k} {v}" for k, v in event["usage"].items())
        self._rule("─", f"call {event['call']} ← {event['seconds']:.1f} s"
                        + (f", {usage}" if usage else ""), "32")
        if event["text"]:
            self._write(self._cut(event["text"], self.limit))
        for call in event["tool_calls"]:
            self._write(f"tool call {call['name']}: "
                        + json.dumps(call["arguments"], ensure_ascii=False))

    def _answer(self, event):
        status = "valid" if event["valid"] else "INVALID"
        self._rule("═", f"answer ({status})", "1")
        self._write(event["query"] or "(no query)")
        if event["error"]:
            self._write(f"error: {event['error']}")

    def _message(self, message: dict):
        role = message.get("role", "?")
        limit = self.system_limit if role == "system" else self.limit
        self._write(self._paint(f"[{role}]", "33"))
        self._write(self._cut(_content(message), limit))

    def _cut(self, text: str, limit: int) -> str:
        if self.full or len(text) <= limit:
            return text
        return (f"{text[:limit]}\n… ({len(text) - limit} more characters, "
                "--full shows them)")

    def _rule(self, char: str, title: str, color: str):
        self._write(self._paint(f"{char * 3} {title} {char * 3}", color))

    def _paint(self, text: str, color: str) -> str:
        return f"\033[{color}m{text}\033[0m" if self.color else text

    def _write(self, text: str):
        print(text, file=self.stream)


def _content(message: dict) -> str:
    """Return the text of *message*, with its tool calls or results."""
    content = message.get("content")
    if isinstance(content, str):
        text = content
    elif content is None:
        text = ""
    else:
        text = json.dumps(content, indent=1, ensure_ascii=False)
    extra = {
        key: value for key, value in message.items()
        if key not in ("role", "content")
    }
    if extra:
        text += ("\n" if text else "") + json.dumps(
            extra, ensure_ascii=False, default=str
        )
    return text


def _trace_files(directory: Path) -> list:
    return sorted(directory.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)


def watch(target, printer: Printer, poll: float = 0.5,
          follow: bool = True) -> None:
    """
    Print the trace of the question being asked, following it.

    *target* is a run directory (its ``trace`` directory, or itself when
    it holds the traces) or a trace file. In a directory, the trace of
    the latest question is printed from its start, then the next ones as
    the run moves on. Without *follow*, it stops at the end of the trace.
    """
    target = Path(target)
    if target.is_dir() and (target / "trace").is_dir():
        target = target / "trace"
    directory = target if target.is_dir() else None
    current, offset, waiting = None, 0, False
    while True:
        if directory:
            files = _trace_files(directory)
            if not files and not waiting:
                printer.note(f"No trace in {directory} yet: was the run "
                             "started with --trace?")
                waiting = True
            if files and files[-1] != current and (
                current is None or current.stat().st_size <= offset
            ):
                current, offset = files[-1], 0
        elif target.exists():
            current = target
        if current:
            if current.stat().st_size < offset:  # the question asked again
                offset = 0
            with current.open("rb") as stream:
                stream.seek(offset)
                for line in iter(stream.readline, b""):
                    if not line.endswith(b"\n"):
                        break
                    offset += len(line)
                    try:
                        event = json.loads(line)
                    except ValueError:
                        printer.note(f"Skipped a line of {current.name} that "
                                     f"is not an event: {line[:80]!r}")
                        continue
                    printer.show(event)
        if not follow:
            return
        time.sleep(poll)
