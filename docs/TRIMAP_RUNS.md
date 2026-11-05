# Run TriMap and t-SNE layouts

TriMap and t-SNE draw a 2-D layout from a table of points. Protein space pages and BGCs in Space use them beside PCA. This page covers where TriMap is installed, how to check it before a long run, the one known crash and its fix, and the settings to reuse.

To redraw coordinates that already exist, use [Embedding replay](EMBEDDING_REPLAY.md) instead. Replay does not need TriMap or numba.

## Where it is installed

TriMap is not in the main bundle environment. It lives in its own virtual environment on the operator workstation:

```bash
Tools/venvs/trimap/bin/python3
```

The environment was made from the `phylo` conda Python (3.12.7). It holds these versions:

| Package | Version |
|---|---|
| trimap | 1.2.0 |
| annoy | 1.17.3 |
| numba | 0.68.0 |
| llvmlite | 0.50.0 |
| numpy | 2.5.4 |
| scipy | 1.18.1 |
| scikit-learn | 1.9.1 |

Check the versions with `Tools/venvs/trimap/bin/python3 -m pip list` before quoting them. Another machine needs its own environment. Install `trimap` with pip into a fresh virtual environment; pip brings annoy and numba with it.

## Check it first

Run this smoke test before any long run. It takes a few seconds:

```bash
NUMBA_THREADING_LAYER=workqueue Tools/venvs/trimap/bin/python3 -c "
import numpy as np, trimap
x = np.random.rand(500, 50).astype('float32'); np.random.seed(1)
print(trimap.TRIMAP(apply_pca=False, n_iters=50).fit_transform(x).shape)"
```

It prints `(500, 2)`. Anything else, or no output, means the run would fail too.

## The known crash: numba's default threading layer

On the operator workstation, TriMap ends with `Segmentation fault` (exit code 139) and no Python traceback. With `-X faulthandler` the crash is inside the `trimap_` module of the TriMap package, in `generate_triplets_known_knn` at the `find_p` call, which numba compiles.

The cause is numba's default threading layer, `omp`. The `workqueue` layer runs cleanly. These do not fix it: a fresh `NUMBA_CACHE_DIR`, or `NUMBA_OPT=0`. annoy is not the cause; it runs on its own and inside TriMap once the layer is set.

The fix is one environment variable, set before numba is imported:

```bash
export NUMBA_THREADING_LAYER=workqueue
```

In a script, set it at the top, before `import trimap`:

```python
import os
os.environ.setdefault("NUMBA_THREADING_LAYER", "workqueue")
import trimap
```

Record the layer in the run receipt. `numba.threading_layer()` reports the layer in use after the first parallel function runs.

A crash with no traceback is easy to misread. A process that exits 139 inside a pipe can also look like it finished with no output. Run once without a pipe and check `echo $?`.

## Identical points make TriMap diverge

TriMap can finish without an error and still return a broken layout. Check the coordinates before drawing. A good layout spans a few hundred units. A diverged one reaches 1e6 to 1e12, and plotting squeezes almost every point into a thin band.

The cause is rows with identical input values. TriMap scales each point by its mean distance to neighbors 3 to 5. When several neighbors sit at distance 0, that scale collapses and the layout diverges. BGCs in Space hit this: 6,972 of 101,447 BiG-SLiCE regions shared their feature vector with another region, and the first full run reached about 1e12.

The fix:

1. Find rows that are exactly identical in the input (compare the raw values, not rounded coordinates).
2. Run TriMap on the distinct rows only.
3. Give each duplicate the position of its identical twin. Identical inputs belong at the same point.
4. Record the number of distinct rows in the receipt.

After that, pass exact neighbors (below). On a 20,000-point test of distinct rows, annoy's approximate neighbors still diverged (about 1e6), while exact neighbors converged (largest coordinate about 281).

```python
keys = {}
first = np.array([keys.setdefault(row.tobytes(), i) for i, row in enumerate(X)])
uniq = np.unique(first)
pos = {i: k for k, i in enumerate(uniq)}
y_unique = run_trimap(X[uniq])
y = y_unique[[pos[i] for i in first]]
```

## Settings to reuse

The protein space run 7 layouts used these TriMap settings (`TRIMAP_<SET>.json` in its kit). Reuse them unless the owner asks for others:

| Setting | Value |
|---|---|
| `n_dims` | 2 |
| `n_inliers` | 12 |
| `n_outliers` | 4 |
| `n_random` | 3 |
| `n_iters` | 400 |
| seed | `np.random.seed(20261008)` set just before TriMap |

TriMap 1.2.0 has no seed argument, and numba's random numbers are not controlled. Its layout is therefore not bit-reproducible. Say so in the receipt and Methods. The point positions change slightly between runs; the neighborhoods do not.

Run 7 passed a distance matrix (`use_dist_matrix=True`). For feature vectors, pass a 50-component PCA with `apply_pca=False`. You can also pass exact neighbors in place of annoy's approximate ones, as `knn_tuple=(neighbors, distances)`. Give each point its 62 nearest neighbors (`n_inliers` + 50) from scikit-learn `NearestNeighbors`, with the point itself first. BGCs in Space does this.

For t-SNE, use scikit-learn `TSNE` (Barnes-Hut) on the same 50 components. Use perplexity 30, `init="pca"` and `random_state=20261008`.

## Size and time

TriMap on about 6,300 points took 6 s on the M5 (run 7, KS). t-SNE is the slow step on large sets. Barnes-Hut time grows a little faster than the number of points. Run large sets under `nice -n 15` with at most 4 threads (`n_jobs=4` for t-SNE and neighbors). Time a 5,000-point sample first, and stop if the estimate passes an hour.

## What a run must record

- the Python path and the package versions above;
- `NUMBA_THREADING_LAYER` and the layer reported;
- the TriMap and t-SNE settings, the seed statement and the input (distance matrix, PCA components or exact neighbors);
- the number of points and the seconds per layout;
- input file SHA-256 values.

## Reading the layouts

t-SNE and TriMap keep near neighbors together but distort large distances. Gaps between groups and group sizes do not measure difference. Read distances from PCA, or from the distances themselves. A point near another is similar in its input features. That is not a shared product.
