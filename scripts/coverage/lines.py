"""Time the steps of the neighbourhood and reduction on one chunk of real peaks."""
import time
import numpy as np, pandas as pd, nibabel as nib
coords = pd.read_csv("/Users/bot/neurolang-text2query-bench/neurolang_data/data-neurosynth_version-7_coordinates.tsv.gz", sep="\t")
img = nib.load("/Users/bot/neurolang_data/neurosynth/schaefer_2018/Schaefer2018_100Parcels_17Networks_order_FSLMNI152_2mm.nii.gz")
peaks = coords[["x", "y", "z"]].to_numpy(float)[:4096]; owners = coords["id"].to_numpy()[:4096]
sigma = 10 / np.sqrt(8 * np.log(2)); radius_mm = 3 * sigma
data = np.asanyarray(img.dataobj).astype(np.int64); shape = np.array(data.shape); affine = img.affine
inverse = np.linalg.inv(affine); spacing = np.linalg.norm(affine[:3, :3], axis=0)
reach = np.ceil(radius_mm / spacing).astype(int) + 1
offsets = np.stack(np.meshgrid(*(np.arange(-r, r + 1) for r in reach), indexing="ij"), -1).reshape(-1, 3)
steps = offsets @ affine[:3, :3].T
keep = np.linalg.norm(steps, axis=1) <= radius_mm + np.linalg.norm(affine[:3, :3] @ [.5, .5, .5])
offsets, steps = offsets[keep], steps[keep]; print("offsets", len(offsets))
T = {}
def tick(name, t=[time.time()]):
    now = time.time(); T[name] = now - t[0]; t[0] = now
centres = np.round(nib.affines.apply_affine(inverse, peaks)); shift = nib.affines.apply_affine(affine, centres) - peaks; tick("centres")
squared = np.square(steps[None] + shift[:, None]).sum(axis=-1); tick("squared")
peak, offset = np.nonzero(squared <= radius_mm ** 2); tick("nonzero")
voxels = centres.astype(int)[peak] + offsets[offset]; tick("voxels")
inside = np.all((voxels >= 0) & (voxels < shape), axis=-1); peak, offset, voxels = peak[inside], offset[inside], voxels[inside]; tick("inside")
flat = np.ravel_multi_index(tuple(voxels.T), data.shape); tick("flat")
values = data.ravel()[flat]; labelled = values > 0; peak, offset = peak[labelled], offset[labelled]; tick("labelled")
values, flat, own, dist = values[labelled], flat[labelled], owners[peak], np.sqrt(squared[peak, offset]); tick("yield")
names, codes = np.unique(own, return_inverse=True); tick("unique studies")
key = codes * data.size + flat; order = np.lexsort((dist, key)); tick("lexsort")
first = order[np.diff(key[order], prepend=-1) != 0]; tick("first")
pairs, pair = np.unique(codes[first] * 101 + values[first], return_inverse=True); tick("unique pairs")
w = np.bincount(pair, np.exp(-dist[first] ** 2 / (2 * sigma ** 2))); tick("bincount")
print(len(dist), {k: round(v, 3) for k, v in T.items()})
