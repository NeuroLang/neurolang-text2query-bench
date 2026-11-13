#!/bin/bash
# Append the OpenRouter key's spend to a ledger, without printing the key:
#   scripts/or_spend.sh LEDGER LABEL
cd "$(dirname "$0")/.." || exit 1
source scripts/env.sh
curl -s -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/key |
python3 -c "
import json, sys, time
d = json.load(sys.stdin)['data']
rec = {'time': time.strftime('%Y-%m-%dT%H:%M:%S'), 'label': sys.argv[2],
       'usage': round(d['usage'], 4), 'limit_remaining': round(d['limit_remaining'], 4)}
open(sys.argv[1], 'a').write(json.dumps(rec) + '\n')
print(json.dumps(rec))
" "$1" "$2"
