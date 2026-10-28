import io
import json

from text2query_bench.runner import ask
from text2query_bench.systems import AssistantSystem
from text2query_bench.trace import (
    Printer, Tracer, TracingClient, trace_directory, watch,
)


class FakeClient:
    """Replies with the scripted *texts*, one per request."""

    def __init__(self, texts):
        self.texts = list(texts)

    def complete(self, messages, tools=None, temperature=0.0):
        from neurolang_apps.utils.llm.providers import Reply

        return Reply(self.texts.pop(0), usage={"input_tokens": 5})

    def close(self):
        pass


def events(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_requests_hold_the_new_messages_only(tmp_path):
    tracer = Tracer(tmp_path)
    client = TracingClient(FakeClient(["a", "b", "c"]), tracer)
    tracer.begin("q1", "en", "Which studies?")
    system = {"role": "system", "content": "You write queries."}
    first = [system, {"role": "user", "content": "Which studies?"}]
    client.complete(first)
    second = first + [{"role": "assistant", "content": "a"},
                      {"role": "user", "content": "Observation: 3 rows"}]
    client.complete(second)
    client.complete([system, {"role": "user", "content": "Again?"}])
    tracer.end({"query": "ans(s) :- study(s)", "valid": True})
    trace = events(tmp_path / "q1-en.jsonl")
    assert [e["event"] for e in trace] == [
        "question", "request", "reply", "request", "reply", "request",
        "reply", "answer",
    ]
    requests = [e for e in trace if e["event"] == "request"]
    assert [(r["start"], len(r["messages"])) for r in requests] == [
        (0, 2), (2, 2), (0, 2)
    ]
    assert trace[2]["text"] == "a" and trace[2]["usage"] == {
        "input_tokens": 5
    }
    assert trace[-1]["query"] == "ans(s) :- study(s)"


def test_failed_requests_are_traced(tmp_path):
    tracer = Tracer(tmp_path)
    client = TracingClient(FakeClient([]), tracer)
    tracer.begin("q1", "en", "Which studies?")
    try:
        client.complete([{"role": "user", "content": "q"}])
    except IndexError:
        pass
    assert "error" in events(tmp_path / "q1-en.jsonl")[-1]


def test_printer_and_watch(tmp_path):
    stream = io.StringIO()
    tracer = Tracer(tmp_path / "trace")
    client = TracingClient(FakeClient(["Thought: look\n" + "x" * 50]),
                           tracer)
    tracer.begin("q2", "fr", "Quelles études ?")
    client.complete([{"role": "system", "content": "s" * 100},
                     {"role": "user", "content": "Quelles études ?"}])
    tracer.end({"query": "", "valid": False, "error": "no query"})
    watch(tmp_path, Printer(stream, limit=20, system_limit=10),
          follow=False)
    text = stream.getvalue()
    assert "q2 [fr] Quelles études ?" in text
    assert "call 1 → 2 new message(s)" in text and "[system]" in text
    assert "90 more characters" in text and "Thought: look" in text
    assert "answer (INVALID)" in text and "error: no query" in text
    full = io.StringIO()
    watch(tmp_path / "trace" / "q2-fr.jsonl", Printer(full, full=True),
          follow=False)
    assert "s" * 100 in full.getvalue()


def test_tracing_a_run(nl, dataset, tmp_path):
    tracer = Tracer(tmp_path)
    system = AssistantSystem(
        nl, "small", strategy="icl", tracer=tracer,
        client=FakeClient(["```datalog\nans(s) :- mentions(s, 'pain')\n```"]),
    )
    questions = [q for q in dataset.questions if q.id == "q1"]
    answers = ask(system, dataset, ["en"], questions,
                  lambda answer, answers: tracer.end(answer),
                  on_question=tracer.begin)
    assert answers[0]["valid"]
    trace = events(tmp_path / "q1-en.jsonl")
    assert trace[0]["text"] == "Which studies mention pain?"
    request = trace[1]
    assert request["messages"][0]["role"] == "system"
    assert "mentions" in request["messages"][0]["content"]
    assert trace[-1]["query"] == "ans(s) :- mentions(s, 'pain')"


def test_watch_skips_what_is_not_an_event(tmp_path):
    (tmp_path / "trace").mkdir()
    path = tmp_path / "trace" / "q1-en.jsonl"
    event = {"event": "question", "id": "q1", "language": "en",
             "text": "Which?"}
    path.write_text(json.dumps(event) + "\n \n" + json.dumps(event) + "\n")
    stream = io.StringIO()
    watch(path, Printer(stream), follow=False)
    text = stream.getvalue()
    assert text.count("q1 [en] Which?") == 2
    assert "Skipped a line of q1-en.jsonl" in text


def test_watch_finds_the_traces_of_an_answers_file(tmp_path):
    assert trace_directory(tmp_path / "x" / "answers.json") == (
        tmp_path / "x" / "trace"
    )
    answers = tmp_path / "r"
    assert trace_directory(answers) == tmp_path / "r.trace"
    answers.write_text('[\n  {"id": "q1"}\n]\n')
    stream = io.StringIO()
    watch(answers, Printer(stream), follow=False)
    assert "No trace in" in stream.getvalue()
    tracer = Tracer(trace_directory(answers))
    tracer.begin("q1", "en", "Which?")
    tracer.end({"query": "ans(s) :- study(s)", "valid": True})
    stream = io.StringIO()
    watch(answers, Printer(stream), follow=False)
    text = stream.getvalue()
    assert "q1 [en] Which?" in text and "Skipped" not in text
    run = io.StringIO()
    watch(tmp_path / "run", Printer(run), follow=False)
    assert f"No trace in {tmp_path / 'run' / 'trace'}" in run.getvalue()
