#!/bin/bash
# Round-2 teacher runs of scripts/distill.py on data/distill/pool2.json,
# NeuroLang of scripts/nsv3c_env.sh, OpenRouter only:
#   scripts/run_round2.sh sonnet N        # Sonnet ReAct, N workers
#   scripts/run_round2.sh deepseek I N    # DeepSeek sample I (0-2), N workers
# Resumable (answered ids are skipped); every worker stops when the key
# has spent MAX_USAGE dollars (default 170).
cd "$(dirname "$0")/.." || exit 1
source scripts/env.sh; source scripts/nsv3c_env.sh
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
run() {  # TAG PROVIDER WORKERS [options]: one engine, forked workers
    tag=$1 provider=$2 n=$3; shift 3
    $VENV/bin/python scripts/distill.py answer --round 2 \
        --config configs/llm.nsv3.yaml --provider "$provider" --tag "$tag" \
        --workers "$n" --max-usage "${MAX_USAGE:-170}" "$@" \
        >> "data/distill/round2/$tag.log" 2>&1
}
case $1 in
sonnet) run react.sonnet openrouter "${2:-8}" ;;
# the samples of the x3 vote: temperature 0.7, as the agent's vote
# sample 2 only where samples 0 and 1 split (run it once they and Sonnet
# are complete)
deepseek) run "deepseek.$2" openrouter-deepseek-0731 "${3:-8}" --temperature 0.7 \
    $([ "$2" = 2 ] && echo --lazy) ;;
esac
