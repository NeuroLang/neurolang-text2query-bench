# The NeuroLang of the nsv3e runs (runs/nsv3e.md): upstream master
# 1a4dafd8 (#1201-#1205 merged) for variant A, branch
# feat/llm-distilled-bank for the others; one detached worktree per
# variant, chosen with NL_TREE (see scripts/run_nsv3e.sh).
#   source scripts/nsv3e_env.sh
P=${NL_TREE:-/Users/bot/NeuroLang-nsv3e-A}/packages
export PYTHONPATH=$P/neurolang:$P/nl_core:$P/nl_expr:$P/neurolang_apps
export VENV=.venv-dsparity CONFIG=${CONFIG:-configs/llm.nsv3.yaml} RETRIEVAL=${RETRIEVAL:-bm25}
