"""Rerun the distill agent on hanging questions, logging each tool call before it runs."""
import faulthandler, json, sys, time
sys.path.insert(0, "/Users/bot/neurolang-text2query-bench/scripts")
from pathlib import Path
from neurolang_apps.utils.llm import load_config, make_agent
from neurolang_apps.utils.llm import agent as agent_mod
from text2query_bench.engine import build_engine

ROOT = Path("/Users/bot/neurolang-text2query-bench")
provider_name, qids = sys.argv[1], sys.argv[2:]
pool = {i["id"]: i for i in json.loads((ROOT / "data/distill/pool2.json").read_text())}
nl = build_engine("neurosynth", ROOT / "neurolang_data")
config = load_config(ROOT / "configs/llm.nsv3.yaml")
provider = config.provider(provider_name)
config.assistant.comment_rules = False
config.assistant.verify_rounds = 0
orig = None
for cls in [agent_mod.Toolbox]:
    if True:
        orig = cls._call
        def traced(self, name, arguments, _orig=orig):
            print(f"TOOL {name} {json.dumps(arguments)}", flush=True)
            faulthandler.dump_traceback_later(120, exit=True, file=sys.stderr)
            t = time.perf_counter()
            try:
                out = _orig(self, name, arguments)
            finally:
                faulthandler.cancel_dump_traceback_later()
            print(f"  -> {time.perf_counter()-t:.1f}s {str(out[0])[:300]!r}", flush=True)
            return out
        cls._call = traced
for qid in qids:
    item = pool[qid]
    print("=== ", qid, item["question"], flush=True)
    agent = make_agent(nl, provider, config.assistant, "datalog", "react",
                       engine_name="neurosynth", exclude_question=item["question"])
    r = agent.run(item["question"])
    print("FINAL", r.query, r.valid, r.error, flush=True)
