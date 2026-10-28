"""
Size of the ReAct system prompt on an engine, by section, and the
outputs of the tools the baseline found misleading.

    .venv-llmfix/bin/python scripts/prompt_size.py [QUESTION] [--dump]

--dump prints the whole system prompt too. Tokens are estimated as
characters / 4, which undercounts IRIs (about 2 characters a token).
"""

import re
import sys

from neurolang_apps.utils.llm import load_config, make_agent
from text2query_bench.engine import build_engine

args = [a for a in sys.argv[1:] if a != "--dump"]
question = args[0] if args else (
    "Which Tian regions are activated by studies mentioning reward?"
)
config = load_config("configs/llm.yaml")
nl = build_engine("neurosynth", "neurolang_data")
agent = make_agent(
    nl, config.provider("openrouter-gemma"), config.assistant, "datalog",
    "react", engine_name="neurosynth", client=object(),
)
prompt = agent.system_prompt(question, text_tools=True)
print(f"system prompt: {len(prompt)} chars, ~{len(prompt) // 4} tokens")
for section in re.split(r"\n\n(?=# )", prompt):
    title = section.splitlines()[0][:50]
    print(f"  {len(section):7d} chars  {title}")
context = agent.context
print("\n--- describe_predicate study_title\n" + context.describe("study_title"))
print("\n--- describe_predicate tian\n" + context.describe("tian"))
print("\n--- search_values accumbens\n" + context.search_values("accumbens"))
print("\n--- search_values accumbens in tian_activated\n"
      + context.search_values("accumbens", "tian_activated"))
if "--dump" in sys.argv:
    print("\n--- system prompt\n" + prompt)
