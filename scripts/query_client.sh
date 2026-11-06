#!/bin/bash
# scripts/query_client.sh NAME (with scripts/query_server.py /tmp/nlq running) 'datalog'  -> waits for result
n=$1; shift
rm -f /tmp/nlq/$n.out
printf '%s\n' "$1" > /tmp/nlq/$n.tmp && mv /tmp/nlq/$n.tmp /tmp/nlq/$n.dl
until [ -f /tmp/nlq/$n.out ]; do sleep 0.5; done
cat /tmp/nlq/$n.out
