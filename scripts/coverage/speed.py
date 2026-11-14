"""Profile atlas_coverage on a slice of the real peaks (schaefer)."""
import sys, time, cProfile, pstats
import numpy as np, pandas as pd, nibabel as nib
from neurolang_apps.utils import engine_registry as er
coords = pd.read_csv("/Users/bot/neurolang-text2query-bench/neurolang_data/data-neurosynth_version-7_coordinates.tsv.gz", sep="\t")
print(coords.columns.tolist(), len(coords))
n = int(sys.argv[1])
xyz = coords[["x", "y", "z"]].to_numpy(float)[:n]; st = coords["id"].to_numpy()[:n]
img = nib.load("/Users/bot/neurolang_data/neurosynth/schaefer_2018/Schaefer2018_100Parcels_17Networks_order_FSLMNI152_2mm.nii.gz")
names = {i: str(i) for i in range(1, 101)}
t = time.time()
cProfile.run("rows = er.atlas_coverage(img, names, xyz, st)", "/tmp/covbench/prof")
print(len(rows), time.time() - t)
pstats.Stats("/tmp/covbench/prof").sort_stats("cumtime").print_stats(12)
