#!/bin/bash
# Run the brute-force certain-answer checkers on a NeuroLang tree, under
# PYTHONHASHSEED 0 and 1 (or $SEEDS; NORECURSIVE=1 skips the recursive family); outputs in $OUT/<label>_<check>_<hashseed>.txt.
#   scripts/hang/xrchain/brute_force.sh TREE LABEL OUT
TREE=$1 LABEL=$2 OUT=$3
P=$TREE/packages
export PYTHONPATH=$P/neurolang:$P/nl_core:$P/nl_expr:$P/neurolang_apps
PY=/Users/bot/neurolang-text2query-bench/.venv-dsparity/bin/python
H=$(dirname "$0")/..
mkdir -p "$OUT"
for hs in ${SEEDS:-0 1}; do
  export PYTHONHASHSEED=$hs
  $PY $H/ontosplit/random_check.py $hs 60 > $OUT/${LABEL}_onto1_$hs.txt 2>&1
  [ -z "$NORECURSIVE" ] && $PY $H/ontosplit/random_check2.py $hs 60 4 recursive > $OUT/${LABEL}_onto2r_$hs.txt 2>&1
  $PY $H/ontosplit/random_check2.py $hs 60 4 acyclic > $OUT/${LABEL}_onto2a_$hs.txt 2>&1
  $PY $H/propaxioms/random_check.py $hs 60 all > $OUT/${LABEL}_prop_$hs.txt 2>&1
  $PY $H/propaxioms/random_check.py $hs 60 all --rules > $OUT/${LABEL}_proprules_$hs.txt 2>&1
done
echo done > $OUT/${LABEL}_DONE
