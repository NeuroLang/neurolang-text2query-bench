# Engine hang / crash investigations on the neurosynth engine

Scripts used to chase two NeuroLang engine bugs hit by the LLM agents on
the neurosynth engine (Cognitive Atlas ontology loaded). Run them with
`source scripts/nsv3c_env.sh` (or a `PYTHONPATH` to the NeuroLang
worktree under test) and the `.venv-dsparity` interpreter; they build the
engine from `neurolang_data/`.

## Stratification hang (NeuroLang PR #1224, branch fix/stratify-scc)

- `repro.py QUERY...`: `check_query` of each query on the real engine,
  with a faulthandler dump after `$DUMP` seconds (default 60).
- `repro2.py`, `repro3.py`, `dump.py`, `where.py`, `where2.py`, `stub*.py`,
  `guard.py`, `verify.py`: locate the hang (dumping the stratified program,
  sampling stacks), and check the fix.
- `toy.py N M`: a synthetic program with `N`-long and `M`-deep recursive
  components; times `stratify`.
- `analyse.py`, `bench.py`: analyse and time `stratify` on the dumped
  programs.
- `difftest.py SEEDS`: differential test of the new `stratify` against the
  old one (`expression_processing_old.py`, the module before the fix) on
  random programs.
- `trace_agent.py`: rerun the distill agent on the hanging questions,
  logging each tool call before it runs.

## `ro:has_part` IndexError in magic sets (NeuroLang PR #1228)

- `hasparterr/toy.py`, `toy_mixed.py`, `toy_trace.py`: a one-restriction
  OWL ontology; a property only constrained by it (and also given a rule)
  queried through `execute_datalog_program`, against `solve_all`.
- `hasparterr/debug.py`, `run.py QUERY...`: the query rule and rules seen
  by magic sets; run queries on the real engine.
- `hasparterr/xrewrite_profile.py`, `xrewrite_dups.py SECONDS`: profile and
  count the Xrewrite of `q(x) :- ro:has_part(x, y)` on cogat (it does not
  finish: ~40k distinct rewritings a minute).
