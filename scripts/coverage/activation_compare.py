"""Compare master's atlas_activation pairs with this branch's on the real peaks, 6 mm."""
import sys
sys.path.insert(0, "/tmp/covbench/old")
import pandas as pd, nibabel as nib
import importlib.util
spec = importlib.util.spec_from_file_location("master_registry", "/Users/bot/NeuroLang-master-cov/packages/neurolang_apps/neurolang_apps/utils/engine_registry.py")
old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
from neurolang_apps.utils import engine_registry as er
c = pd.read_csv("/Users/bot/neurolang-text2query-bench/neurolang_data/data-neurosynth_version-7_coordinates.tsv.gz", sep="\t")
xyz, st = c[["x", "y", "z"]].to_numpy(float), c["id"].to_numpy()
for f in ["schaefer_2018/Schaefer2018_100Parcels_17Networks_order_FSLMNI152_2mm.nii.gz",
          "tian/Tian_Subcortex_S2_3T_2009cAsym.nii.gz", "destrieux_2009/destrieux2009_rois_lateralized.nii.gz"]:
    img = nib.load("/Users/bot/neurolang_data/neurosynth/" + f)
    names = {i: str(i) for i in range(1, 200)}
    a = set(old.atlas_activation(img, names, xyz, st, 6.0)); b = set(er.atlas_activation(img, names, xyz, st, 6.0))
    print(f.split("/")[0], len(a), len(b), "only master", len(a - b), "only branch", len(b - a))
