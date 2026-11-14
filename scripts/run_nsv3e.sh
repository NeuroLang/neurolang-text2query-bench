#!/bin/bash
# One run of the nsv3e ablation (runs/nsv3e.md), one at a time:
#   scripts/run_nsv3e.sh VARIANT SET MODE [NAME_SUFFIX] [t2q-bench run options]
# VARIANT A (master 1a4dafd8), B, C, D (distilled banks, traces) or E
# (D or C + the local hybrid selection, its choices logged in the run's
# hybrid.jsonl): the detached worktree /Users/bot/NeuroLang-nsv3e-VARIANT.
# SET dev|test (v3 heldout splits) or fresh. MODE single (DeepSeek on
# OpenRouter), vote (x3 + Sonnet fallback), sonnet, albert-deepseek,
# albert-gemma. The load average is logged every minute in OUT/load.log.
cd "$(dirname "$0")/.." || exit 1
variant=$1 set=$2 mode=$3 suffix=$4; shift 4
export NL_TREE=/Users/bot/NeuroLang-nsv3e-$variant
source scripts/env.sh; source scripts/nsv3e_env.sh
case $set in
dev|test) export DATASET=datasets/neurosynth-v3-heldout.yaml; split=(--split $set) ;;
fresh) export DATASET=datasets/neurosynth-v3-fresh.yaml; split=() ;;
esac
provider=openrouter-deepseek-0731
case $mode in
vote) export CONFIG=configs/llm.nsv3b-vote.yaml ;;
sonnet) provider=openrouter ;;
albert-deepseek) provider=albert-deepseek; export CONFIG=configs/llm.nsv3d.yaml ;;
albert-gemma) provider=albert-gemma; export CONFIG=configs/llm.nsv3d.yaml ;;
esac
out=runs/nsv3e-$variant-$set-$mode$suffix
mkdir -p "$out"
[ "$variant" = E ] && export NL_HYBRID_EXAMPLES=$PWD/$out/hybrid.jsonl
(while true; do echo "$(date +%H:%M) $(sysctl -n vm.loadavg)" >> "$out/load.log"; sleep 60; done) &
logger=$!
scripts/run_nsv2.sh $provider "$out" "${split[@]}" --lang en "$@"
kill $logger
