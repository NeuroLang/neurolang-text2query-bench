#!/bin/bash
# The runs of runs/nsv3d.md (Cognitive-Atlas-first rule), both arms of a
# set at once so that they share the machine's load:
#   scripts/run_nsv3d_cogat.sh nsv2|v3|fresh
# Arms: master = NeuroLang upstream d66a4245 (detached worktree
# /Users/bot/NeuroLang-cogatmaster), branch = feat/llm-cogat-first
# (/Users/bot/NeuroLang-cogatfirst), over .venv-dsparity (PYTHONPATH).
# English, ReAct, BM25, verify_rounds 0. DeepSeek single
# (configs/llm.nsv3.yaml), DeepSeek x3 vote + Sonnet fallback
# (configs/llm.nsv3b-vote.yaml) on every set; Sonnet single on v3 and
# fresh only. Runs in runs/nsv3d-cogat-ARM-SET-MODEL.
cd "$(dirname "$0")/.." || exit 1
source scripts/env.sh
DS=openrouter-deepseek-0731
case $1 in
nsv2) export DATASET=datasets/neurosynth-v2.yaml; split=;;
v3) export DATASET=datasets/neurosynth-v3-heldout.yaml; split="--split test";;
fresh) export DATASET=datasets/neurosynth-v3-fresh.yaml; split=;;
*) echo "usage: $0 nsv2|v3|fresh"; exit 1;;
esac
for arm in master branch; do
    (
        NL_TREE=/Users/bot/NeuroLang-cogat$([ $arm = master ] && echo master || echo first)
        source scripts/nsv3c_env.sh
        out=runs/nsv3d-cogat-$arm-$1
        scripts/run_nsv2.sh $DS $out-deepseek $split --lang en &
        CONFIG=configs/llm.nsv3b-vote.yaml scripts/run_nsv2.sh $DS $out-deepseek-vote $split --lang en &
        if [ "$1" != nsv2 ]; then
            scripts/run_nsv2.sh openrouter $out-sonnet $split --lang en &
        fi
        wait
    ) &
done
wait
