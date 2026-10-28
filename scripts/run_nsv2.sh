#!/bin/bash
# ReAct run of a provider on neurosynth-v2:
#   scripts/run_nsv2.sh PROVIDER OUTPUT [t2q-bench run options...]
# e.g. scripts/run_nsv2.sh openrouter-gemma runs/nsv2-react-gemma-or-dev --split dev
# VENV selects the bench venv (default .venv-llmex), e.g. VENV=.venv-llmfix
# for the NeuroLang-llmfix worktree (feat/llm-lean-schema).
# RETRIEVAL (bm25, hybrid) overrides example_retrieval of configs/llm.yaml,
# in a copy of it kept as OUTPUT/llm.yaml.
cd "$(dirname "$0")/.." || exit 1
source scripts/env.sh
provider=$1; out=$2; shift 2
mkdir -p runs/logs
config=configs/llm.yaml
if [ -n "$RETRIEVAL" ]; then
    mkdir -p "$out"; config=$out/llm.yaml
    sed "s/^  example_retrieval: .*/  example_retrieval: $RETRIEVAL/" \
        configs/llm.yaml > "$config"
fi
exec "${VENV:-.venv-llmex}/bin/t2q-bench" --dataset datasets/neurosynth-v2.yaml run \
    --strategy react --llm-config "$config" --lang en fr \
    --provider "$provider" -o "$out" "$@" \
    > "runs/logs/$(basename "$out").log" 2>&1
