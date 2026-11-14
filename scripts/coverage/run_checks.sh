#!/bin/bash
# Query timing, bank tests on real data, neurostore cached build re-timing.
export HOME=/tmp/tf/home
D=/Users/bot/neurolang-text2query-bench/neurolang_data
PY=/Users/bot/NeuroLang-llmex/.venv/bin/python
NEW=$(ls -d /Users/bot/NeuroLang-coverage/packages/* | tr '\n' :)
OLD=$(ls -d /Users/bot/NeuroLang-master-cov/packages/* | tr '\n' :)
cd /tmp/covbench
echo "== query timing"; PYTHONPATH=$NEW $PY /tmp/covbench/query_timing.py $D 2>&1 | grep -v -i warn
for engine in neurosynth neurostore; do
  echo "== bank test $engine"
  NEUROLANG_TEST_DATA_DIR=$D PYTHONPATH=$NEW $PY -m pytest -q -p no:randomly -p no:cacheprovider \
    /Users/bot/NeuroLang-coverage/packages/neurolang_apps/neurolang_apps/utils/llm/tests/test_examples.py \
    -k "test_bank_queries_are_valid_on_the_engine and $engine" --rootdir /tmp/covbench 2>&1 | tail -15
done
echo "== neurostore before, cached (2)"; PYTHONPATH=$OLD $PY /tmp/covbench/precompute.py $D neurostore cache 2>&1 | grep -v -i warn | head -2
echo "== neurostore after, cached (2)"; PYTHONPATH=$NEW $PY /tmp/covbench/precompute.py $D neurostore cache 2>&1 | grep -v -i warn | head -2
echo CHECKS DONE
