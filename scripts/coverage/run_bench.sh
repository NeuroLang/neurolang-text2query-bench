#!/bin/bash
# Before/after: DeepSeek-0731 (OpenRouter) on the region/network questions
# of neurosynth-v3-heldout, master vs feat/atlas-kernel-coverage.
cd /Users/bot/neurolang-text2query-bench || exit 1
source scripts/env.sh
export HOME_REAL=$HOME
for variant in before after; do
  case $variant in
  before) P=/tmp/nl-master/packages ;;
  after) P=/Users/bot/NeuroLang-coverage/packages ;;
  esac
  export PYTHONPATH=$P/neurolang:$P/nl_core:$P/nl_expr:$P/neurolang_apps
  out=runs/coverage-$variant
  .venv-dsparity/bin/t2q-bench --dataset datasets/neurosynth-v3-heldout.yaml run \
    --strategy react --llm-config configs/llm.nsv3.yaml --lang en \
    --provider openrouter-deepseek-0731 -o $out \
    --tags schaefer destrieux tian coactivation > runs/logs/coverage-$variant.log 2>&1
  echo "$variant rc=$?"
done
