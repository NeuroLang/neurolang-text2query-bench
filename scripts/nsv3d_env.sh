# The NeuroLang of the nsv3d runs (runs/nsv3d-step1.md): upstream master
# 8532a28b (0.1a22, after #1176), detached worktree /Users/bot/NeuroLang-nsv3d,
# over the .venv-dsparity install (as scripts/nsv3c_env.sh):
#   source scripts/nsv3d_env.sh
# NL_TREE overrides the worktree, e.g. the local integration branch of the
# step-1 fixes.
P=${NL_TREE:-/Users/bot/NeuroLang-nsv3d}/packages
export PYTHONPATH=$P/neurolang:$P/nl_core:$P/nl_expr:$P/neurolang_apps
export VENV=.venv-dsparity CONFIG=configs/llm.nsv3d.yaml RETRIEVAL=bm25
