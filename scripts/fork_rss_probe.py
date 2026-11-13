"""
Does the assistant's per-query memory guard (validation._in_child, the RSS
of the forked child) count the parent's memory a query only reads?

    python scripts/fork_rss_probe.py [GB] [LIMIT_MB]

A parent array of GB gigabytes; a child that sums it (reads, allocates
nothing) under a limit of LIMIT_MB, then a child that allocates GB.
"""
import sys

import numpy as np

from neurolang_apps.utils.llm import validation

gb = float(sys.argv[1]) if len(sys.argv) > 1 else 3
limit = float(sys.argv[2]) if len(sys.argv) > 2 else 2048
data = np.ones(int(gb * 2**30 / 8))
for name, function in (
    ("read the parent's array", lambda: float(data.sum())),
    ("allocate as much", lambda: float(np.ones_like(data).sum())),
):
    try:
        validation._in_child(function, 600, limit)
        print(f"{name}: ran under {limit:.0f} MB")
    except validation.QueryTooLarge:
        print(f"{name}: stopped, over {limit:.0f} MB")
