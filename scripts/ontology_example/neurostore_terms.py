"""The NeuroStore studies whose abstracts carry each inhibition-task term
with a TF-IDF above 0.03, the threshold of ``mentions``, read from the
engine's cached TF-IDF table (``sys.argv[1]``)."""
import sys
import numpy as np

a = np.load(sys.argv[1])
terms = list(a["terms"])
col, value, indptr = a["col"], a["value"], a["indptr"]
study = np.repeat(np.arange(len(indptr) - 1), np.diff(indptr))
union = set()
for t in ["stroop task", "color word stroop", "simon task", "nogo task",
          "choice reaction time", "stop signal task", "stop signal"]:
    if t not in terms:
        print(repr(t), "not a term")
        continue
    s = set(study[(col == terms.index(t)) & (value > 0.03)])
    print(repr(t), len(s))
    if "stop" not in t:
        union |= s
print("union of the five tasks whose contrasts measure response "
      "inhibition:", len(union))
