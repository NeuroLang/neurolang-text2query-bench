"""
The systems answering the questions of the benchmark.

A system turns a question into a NeuroLang query
(:meth:`System.generate`). Two kinds are provided:

* :class:`AssistantSystem` runs the NeuroLang LLM assistant in process
  (``neurolang.utils.llm``), with the strategy (ICL or ReAct), provider
  and query language chosen;
* :class:`EndpointSystem` asks an HTTP endpoint following the TEXT2SPARQL
  protocol (``GET /?question=...&dataset=...``), e.g. the server of
  :mod:`.server`, so that any implementation can be benchmarked.
"""

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import httpx


@dataclass
class Generation:
    """
    The query a system wrote for a question, with what it cost.

    *valid* tells whether the system itself found its query valid;
    *calls* and *tokens* count the LLM requests and tokens, when known.
    """

    query: str = ""
    language: str = "datalog"
    valid: bool = False
    error: str = ""
    explanation: str = ""
    seconds: float = 0.0
    calls: int = 0
    tokens: int = 0
    steps: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


class System:
    """A system writing NeuroLang queries; *name* identifies its runs."""

    name = "system"

    def generate(self, question: str, language: str) -> Generation:
        """Return the query answering *question*, in natural *language*."""
        raise NotImplementedError


class AssistantSystem(System):
    """
    The NeuroLang LLM assistant, run in process on the engine *nl*.

    *provider* and *strategy* default to those of the configuration at
    *config_path* (see ``neurolang.utils.llm.config``); *query_language*
    is ``datalog`` or ``squall``. *exclude_gold* leaves the question out
    of the few-shot examples when the engine's example bank holds it.

    *examples* (``neurolang.utils.llm.examples.Example``) and
    *description* replace the example bank and the description of the
    engine, e.g. for an engine that is not in NeuroLang's registry.
    """

    def __init__(
        self, nl, engine_name: str, query_language: str = "datalog",
        provider: Optional[str] = None, strategy: Optional[str] = None,
        config_path=None, client=None, exclude_gold: bool = True,
        examples=None, description: Optional[str] = None,
    ):
        from neurolang.utils.llm import load_config

        self.nl = nl
        self.engine_name = engine_name
        self.query_language = query_language
        self.config = load_config(config_path)
        self.provider = self.config.provider(provider)
        self.strategy = strategy or self.config.assistant.strategy
        self.client = client
        self.exclude_gold = exclude_gold
        self.examples = examples
        self.description = description
        self.name = (
            f"{self.strategy}-{self.query_language}-{self.provider.name}"
        )

    def generate(self, question: str, language: str) -> Generation:
        from neurolang.utils.llm import LLMError, make_agent

        steps = []
        agent = make_agent(
            self.nl, self.provider, self.config.assistant,
            self.query_language, self.strategy,
            engine_name=self.engine_name, client=self.client,
            on_step=lambda step: steps.append({
                "action": step.action, "arguments": step.arguments,
                "observation": step.observation[:500],
            }),
            exclude_question=question if self.exclude_gold else "",
            examples=self.examples, description=self.description,
        )
        start = time.perf_counter()
        try:
            result = agent.run(question)
        except LLMError as exc:
            return Generation(
                language=self.query_language, error=str(exc),
                seconds=time.perf_counter() - start, steps=steps,
            )
        return Generation(
            result.query, result.language, result.valid, result.error,
            result.explanation, time.perf_counter() - start, result.calls,
            sum(result.usage.values()), steps,
        )


class EndpointSystem(System):
    """A system behind an HTTP endpoint of the TEXT2SPARQL protocol."""

    def __init__(
        self, url: str, dataset: str, name: str = "endpoint",
        query_language: str = "datalog", timeout: float = 600.0,
    ):
        self.url = url
        self.dataset = dataset
        self.name = name
        self.query_language = query_language
        self.timeout = timeout

    def generate(self, question: str, language: str) -> Generation:
        start = time.perf_counter()
        try:
            response = httpx.get(
                self.url,
                params={"question": question, "dataset": self.dataset},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return Generation(
                language=self.query_language, error=str(exc),
                seconds=time.perf_counter() - start,
            )
        return Generation(
            data.get("query", ""),
            data.get("language", self.query_language),
            bool(data.get("query")),
            data.get("error", ""),
            data.get("explanation", ""),
            time.perf_counter() - start,
            data.get("calls", 0),
            data.get("tokens", 0),
        )


def gold_examples(dataset, query_language: str = "datalog") -> list:
    """
    Return the few-shot examples of the gold queries of *dataset*.

    Each question with a gold query in *query_language* gives one example
    per natural language, so that a question is left out of its own
    prompt in any language (leave-one-out).
    """
    from neurolang.utils.llm.examples import Example

    examples = []
    for question in dataset.questions:
        query = question.gold.get(query_language)
        if query:
            examples += [
                Example(text, {query_language: query})
                for text in question.text.values()
            ]
    return examples


def engine_description(dataset) -> Optional[str]:
    """Return the description of the engine of *dataset*, if declared."""
    if not dataset.engines_file:
        return None
    import yaml

    engines = yaml.safe_load(Path(dataset.engines_file).read_text())
    return (engines.get("engines", {}).get(dataset.engine) or {}).get(
        "description"
    )
