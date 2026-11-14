#!/bin/bash
# Engine builds before/after, cached and uncached, on the bench data.
export HOME=/tmp/tf/home
D=/Users/bot/neurolang-text2query-bench/neurolang_data
PY=/Users/bot/NeuroLang-llmex/.venv/bin/python
NEW=$(ls -d /Users/bot/NeuroLang-coverage/packages/* | tr '\n' :)
OLD=$(ls -d /Users/bot/NeuroLang-master-cov/packages/* | tr '\n' :)
for engine in neurosynth neurostore; do
  echo "== $engine after, first cached build (computes coverage)"; PYTHONPATH=$NEW $PY /tmp/covbench/precompute.py $D $engine cache
  echo "== $engine after, cached"; PYTHONPATH=$NEW $PY /tmp/covbench/precompute.py $D $engine cache
  echo "== $engine before, cached"; PYTHONPATH=$OLD $PY /tmp/covbench/precompute.py $D $engine cache
done
echo "== neurosynth after, uncached"; PYTHONPATH=$NEW $PY /tmp/covbench/precompute.py $D neurosynth nocache
echo "== neurosynth before, uncached"; PYTHONPATH=$OLD $PY /tmp/covbench/precompute.py $D neurosynth nocache
echo DONE
