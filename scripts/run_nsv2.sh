#!/bin/bash
# ReAct run of a provider on neurosynth-v2:
#   scripts/run_nsv2.sh PROVIDER OUTPUT [t2q-bench run options...]
# e.g. scripts/run_nsv2.sh openrouter-gemma runs/nsv2-react-gemma-or-dev --split dev
cd "$(dirname "$0")/.." || exit 1
source scripts/env.sh
provider=$1; out=$2; shift 2
mkdir -p runs/logs
exec .venv-llmex/bin/t2q-bench --dataset datasets/neurosynth-v2.yaml run \
    --strategy react --llm-config configs/llm.yaml --lang en fr \
    --provider "$provider" -o "$out" "$@" \
    > "runs/logs/$(basename "$out").log" 2>&1
