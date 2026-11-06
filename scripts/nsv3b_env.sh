# The NeuroLang of the nsv3b runs: master + #1104 + the magic-sets fix +
# #1116 (vote, fallback) + #1054, worktree /Users/bot/NeuroLang-nsv3b
# (branch bench-nsv3b), over the .venv-dsparity install:
#   source scripts/nsv3b_env.sh
P=/Users/bot/NeuroLang-nsv3b/packages
export PYTHONPATH=$P/neurolang:$P/nl_core:$P/nl_expr:$P/neurolang_apps
export VENV=.venv-dsparity CONFIG=configs/llm.nsv3.yaml RETRIEVAL=bm25
