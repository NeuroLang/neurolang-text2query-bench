#!/bin/bash
# The final nsv3e runs (runs/nsv3e.md), one at a time, A and the best dev
# variant (C) interleaved, the key's spend logged after each:
#   scripts/nsv3e_queue.sh
cd "$(dirname "$0")/.." || exit 1
run() {
    scripts/run_nsv3e.sh "$@"
    scripts/or_spend.sh runs/nsv3e-ledger.jsonl "$1 $2 $3$4"
}
for set in test fresh; do run A $set vote ""; run C $set vote ""; done
for set in test fresh; do run A $set single ""; run C $set single ""; done
for set in test fresh; do run C $set single -r2; run A $set single -r2; done
for mode in albert-deepseek albert-gemma; do
    run A test $mode ""; run C test $mode ""
done
