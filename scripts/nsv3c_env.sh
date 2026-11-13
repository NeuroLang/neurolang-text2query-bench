# The NeuroLang of the nsv3c runs: upstream master 8532a28b (0.1a22, after
# #1176: kernel_radius_mm 6 for activated and the atlases, matching the 6 mm
# MNI golds), detached worktree /Users/bot/NeuroLang-nsv3c, over the
# .venv-dsparity install. (The first, partial nsv3c runs were on 30db798e.)
#   source scripts/nsv3c_env.sh
P=${NL_TREE:-/Users/bot/NeuroLang-nsv3c}/packages
export PYTHONPATH=$P/neurolang:$P/nl_core:$P/nl_expr:$P/neurolang_apps
export VENV=.venv-dsparity CONFIG=configs/llm.nsv3.yaml RETRIEVAL=bm25
