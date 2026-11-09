#!/bin/bash
# The runs of runs/nsv3c.md, NeuroLang upstream master (scripts/nsv3c_env.sh):
#   scripts/run_nsv3c.sh nsv2|v3|fresh
# English, ReAct, BM25 examples, verify_rounds 0. Single DeepSeek and Sonnet
# with configs/llm.nsv3.yaml; DeepSeek x3 vote + Sonnet fallback with
# configs/llm.nsv3b-vote.yaml (its vote-only answers: scripts/vote_only.py).
cd "$(dirname "$0")/.." || exit 1
source scripts/env.sh; source scripts/nsv3c_env.sh
DS=openrouter-deepseek-0731
case $1 in
nsv2)
    scripts/run_nsv2.sh $DS runs/nsv3c-nsv2-deepseek --lang en &
    CONFIG=configs/llm.nsv3b-vote.yaml scripts/run_nsv2.sh $DS runs/nsv3c-nsv2-deepseek-vote --lang en &
    ;;
v3|fresh)
    if [ "$1" = v3 ]; then
        export DATASET=datasets/neurosynth-v3-heldout.yaml; split="--split test"; n=test
    else
        export DATASET=datasets/neurosynth-v3-fresh.yaml; split=; n=fresh
    fi
    scripts/run_nsv2.sh $DS runs/nsv3c-$n-deepseek $split --lang en &
    CONFIG=configs/llm.nsv3b-vote.yaml scripts/run_nsv2.sh $DS runs/nsv3c-$n-deepseek-vote $split --lang en &
    scripts/run_nsv2.sh openrouter runs/nsv3c-$n-sonnet $split --lang en &
    ;;
esac
wait
