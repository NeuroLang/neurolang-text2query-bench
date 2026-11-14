#!/bin/bash
# After nsv3e_queue.sh (A 21 / C 27 on Albert DeepSeek, v3 test): its
# repeats and fresh, one at a time.  scripts/nsv3e_queue2.sh [PID to wait for]
cd "$(dirname "$0")/.." || exit 1
[ -n "$1" ] && while kill -0 "$1" 2>/dev/null; do sleep 30; done
run() {
    scripts/run_nsv3e.sh "$@"
    scripts/or_spend.sh runs/nsv3e-ledger.jsonl "$1 $2 $3$4"
}
run A test albert-deepseek -r2; run C test albert-deepseek -r2
run A fresh albert-deepseek ""; run C fresh albert-deepseek ""
