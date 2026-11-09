# Run TriMap and t-SNE layouts

TriMap and t-SNE draw a 2-D layout from a table of points. The protein-space pages show them beside PCA. This page covers how to install TriMap, check it before a long run, fix its one known crash, avoid a bad layout, and record the run.

The bundle's renderers do not fit these layouts. They draw coordinates you saved. To redraw saved coordinates, use [Embedding replay](EMBEDDING_REPLAY.md). Replay does not need TriMap or numba.

## 1. Install TriMap

TriMap is not in the main bundle environment. Put it in its own virtual environment so it cannot change the bundle's packages. The folder name below is an example.

```bash
python3 -m venv ~/venvs/trimap
~/venvs/trimap/bin/python3 -m pip install trimap
~/venvs/trimap/bin/python3 -m pip list
```

`pip install trimap` brings annoy (approximate neighbors), numba (compiles the inner loops), numpy, scikit-learn and PyTorch (`torch>=2.1`), per the package metadata of trimap 1.2.0. scikit-learn is used by the exact-neighbor and t-SNE steps below. Expect about 1 GB on disk, mostly PyTorch, so check free space first. Record the versions that `pip list` prints.

## 2. Check it first

Run this smoke test before any long run. It takes a few seconds.

```bash
NUMBA_THREADING_LAYER=workqueue ~/venvs/trimap/bin/python3 -c "
import numpy as np, trimap
np.random.seed(1); x = np.random.rand(500, 50).astype('float32')
print(trimap.TRIMAP(apply_pca=False, n_iters=50).fit_transform(x).shape)"
```

Success prints `(500, 2)`. The seed fixes only the test input; it does not control TriMap's own random steps (section 5).

Anything else, or no output, means TriMap did not run in this environment as it is set up. Keep the full error and the `pip list` versions, and fix that before a long run. A pass shows only that this small test ran; a larger run can still fail for other reasons.

## 3. If TriMap exits with code 139

On some machines TriMap ends with `Segmentation fault` (exit code 139) and no Python traceback. Where this was seen, the crash came from numba's default threading layer, `omp`, and the `workqueue` layer ran cleanly. Exit 139 only says the process crashed; it can have other causes. If `workqueue` does not stop it, keep the error output and versions and look for the cause before changing anything else. Set the layer before numba is imported. Set it for every real run, even if the smoke test passes without it:

```bash
export NUMBA_THREADING_LAYER=workqueue
```

In a script, set it at the top, before `import trimap`:

```python
import os
os.environ.setdefault("NUMBA_THREADING_LAYER", "workqueue")
import trimap
```

A fresh `NUMBA_CACHE_DIR` or `NUMBA_OPT=0` does not help. After the first parallel call, `numba.threading_layer()` reports the layer in use. Record it.

A process that exits 139 inside a pipe can look like it finished with no output. Run once without a pipe and check `echo $?`.

## 4. Identical points make TriMap diverge

TriMap can finish with no error and still return a broken layout. Check the coordinates before you draw: look for non-finite values, a range far beyond your other runs on similar data, and a plot that squeezes nearly every point into a thin band. In the runs seen here, good layouts spanned a few hundred units and diverged ones reached millions or more. The range depends on the data and settings, so a small range does not by itself show a good layout.

One cause seen here is rows with identical input values. TriMap scales each point by its mean distance to neighbors 3 to 5. When several neighbors sit at distance 0, that scale collapses. This showed up in a large set of biosynthetic regions where some rows had the same feature vector as another row.

The fix:

1. Find rows that are exactly identical in the input. Compare raw values, not rounded coordinates.
2. Run TriMap on the distinct rows only.
3. Give each duplicate the position of its identical twin.
4. Record the number of distinct rows in the receipt.

Then pass exact neighbors (section 5). In a test on distinct rows, annoy's approximate neighbors still diverged, while exact neighbors converged.

```python
keys = {}
first = np.array([keys.setdefault(row.tobytes(), i) for i, row in enumerate(X)])
uniq = np.unique(first)
pos = {i: k for k, i in enumerate(uniq)}
y_unique = run_trimap(X[uniq])
y = y_unique[[pos[i] for i in first]]
```

`run_trimap` stands for your own function that fits TriMap and returns an array of coordinates.

## 5. Settings

These are a tested starting point for protein-space layouts:

| Setting | Value |
|---|---|
| `n_dims` | 2 |
| `n_inliers` | 12 |
| `n_outliers` | 4 |
| `n_random` | 3 |
| `n_iters` | 400 |

TriMap has no seed argument, and numba's random numbers are not controlled. The layout is therefore not exactly reproducible. Say so in the receipt and in Methods. Point positions change between runs, and neighborhoods can change too. Before you read a group from a layout, fit it at least twice and compare each point's nearest neighbors across the runs. Record that check with the run.

What to pass as input:

- **A distance matrix:** `use_dist_matrix=True`.
- **Feature vectors:** pass a 50-component PCA with `apply_pca=False`.
- **Exact neighbors:** pass `knn_tuple=(neighbors, distances)`. Get 62 nearest neighbors per point (the 12 from `n_inliers` plus 50) from scikit-learn `NearestNeighbors`, with the point itself first.

For t-SNE, use scikit-learn `TSNE` (Barnes-Hut) on the same 50 components. Use perplexity 30 and `init="pca"`. Set `random_state` to a value you record. Unlike TriMap, t-SNE accepts a seed.

## 6. Size and time

t-SNE is the slow step on large sets. Barnes-Hut time grows a little faster than the number of points. Run large sets under `nice -n 15` with at most 4 threads (`n_jobs=4` for t-SNE and neighbors). Time a 5,000-point sample first, and stop if the estimate passes an hour.

## 7. What a run must record

- the Python path and the package versions;
- `NUMBA_THREADING_LAYER` and the layer reported;
- the TriMap and t-SNE settings, the seed statement and the input (distance matrix, PCA components or exact neighbors);
- the number of points, the number of distinct rows, and the seconds per layout;
- the coordinate check and the neighbor comparison between repeat runs;
- the SHA-256 of each input file.

## 8. Reading the layouts

t-SNE and TriMap try to keep near neighbors together and distort large distances. Gaps between groups and group sizes do not measure difference. Read distances from PCA or from the distances themselves. A point near another may be similar in its input features; check the input distances before saying so. Nearness is not a shared product.
