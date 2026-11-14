"""Compare the committed atlas_coverage with the working one on real peaks."""
import sys
sys.path.insert(0, "/tmp/covbench/old")
import numpy as np, pandas as pd, nibabel as nib
import old_registry
from neurolang_apps.utils import engine_registry as er
coords = pd.read_csv("/Users/bot/neurolang-text2query-bench/neurolang_data/data-neurosynth_version-7_coordinates.tsv.gz", sep="\t")
n = int(sys.argv[1])
xyz = coords[["x", "y", "z"]].to_numpy(float)[:n]; st = coords["id"].to_numpy()[:n]
img = nib.load("/Users/bot/neurolang_data/neurosynth/schaefer_2018/Schaefer2018_100Parcels_17Networks_order_FSLMNI152_2mm.nii.gz")
names = {i: str(i) for i in range(1, 101)}
a = old_registry.atlas_coverage(img, names, xyz, st).set_index(["label", "study"]).probability
b = er.atlas_coverage(img, names, xyz, st).set_index(["label", "study"]).probability
j = pd.concat([a, b], axis=1, keys=["old", "new"])
print(len(a), len(b)); d = j[j.isna().any(axis=1) | ~np.isclose(j.old, j.new)]
print(d.head(20)); print(len(d))
