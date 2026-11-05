#!/bin/bash
# Nemotron 3.5 Lightning (OpenRouter), English, master-v0 config, before and
# after the distilled bank of NeuroLang #1057:
#   before: worktree /Users/bot/NeuroLang-distill-before (f695d502, the bank
#           of 46), reached through PYTHONPATH over .venv-distill
#   after:  .venv-distill (7c41d73f, the bank of 85)
# usage: scripts/run_nsv2_nemotron.sh [PROVIDER]
cd "$(dirname "$0")/.." || exit 1
provider=${1:-openrouter-nemotron-lightning}
export VENV=.venv-distill CONFIG=configs/llm.master-v0.yaml
B=/Users/bot/NeuroLang-distill-before/packages
before_path=$B/neurolang_apps:$B/neurolang:$B/nl_core:$B/nl_expr
for bank in before after; do
  if [ $bank = before ]; then export PYTHONPATH=$before_path; else unset PYTHONPATH; fi
  for s in dev test; do
    scripts/run_nsv2.sh $provider runs/nsv2-$s-nemotron-$bank --split $s --lang en
  done
  DATASET=datasets/neurosynth-distill-heldout.yaml \
    scripts/run_nsv2.sh $provider runs/distill-heldout-$bank-nemotron-or --lang en
done
