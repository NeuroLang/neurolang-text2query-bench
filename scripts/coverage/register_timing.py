"""Time reading the kept coverage arrays and registering them as probabilistic facts."""
import glob, sys, time
import numpy as np, pandas as pd
from neurolang.frontend import NeurolangPDL
nl = NeurolangPDL()
for path in sorted(glob.glob(sys.argv[1] + "/atlas_coverage-*.npz")):
    t = time.time()
    with np.load(path) as a:
        rows = pd.DataFrame({"probability": a["probabilities"].astype(float),
                             "label": a["names"][a["codes"]], "study": a["studies"]})
    t1 = time.time()
    nl.add_probabilistic_facts_from_tuples(rows, name="f" + path[-10:-4])
    print(path[-30:], len(rows), f"read {t1 - t:.2f}s register {time.time() - t1:.2f}s")
