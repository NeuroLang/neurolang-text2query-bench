# The NeuroLang of the nsv3c runs: upstream master 30db798e (after #1057,
# #1104, #1116, #1117, #1126, #1127, #1102, #1103), detached worktree
# /Users/bot/NeuroLang-nsv3c, over the .venv-dsparity install:
#   source scripts/nsv3c_env.sh
P=/Users/bot/NeuroLang-nsv3c/packages
export PYTHONPATH=$P/neurolang:$P/nl_core:$P/nl_expr:$P/neurolang_apps
export VENV=.venv-dsparity CONFIG=configs/llm.nsv3.yaml RETRIEVAL=bm25
