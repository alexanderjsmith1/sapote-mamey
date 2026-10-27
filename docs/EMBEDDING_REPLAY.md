# Saved TriMap and tSNE coordinate replay

This optional tool redraws existing coordinates. It does not fit TriMap or t-SNE,
calculate distances, infer biological function or certify a publication figure.
It needs the existing plotting environment, but does not need the TriMap or numba
packages. Keep fitting, model preparation and stability validation separate.

From the bundle root:

```bash
python tools/protein_embedding_replay.py --manifest /path/replay.json --validate-only
python tools/protein_embedding_replay.py --manifest /path/replay.json --out /path/new_output
```

Paths in the manifest resolve relative to that manifest, so the same small input
set can be relocated without editing producer source. Absolute paths can reference
large evidence in place. Every input needs its exact lowercase SHA-256. No input
or existing output is overwritten.

```json
{
  "schema": "sapote.embedding-replay.v1",
  "method": "trimap",
  "generation": "original-run-and-set-name",
  "coordinates": {"path": "TRIMAP_SET.tsv", "sha256": "REPLACE_WITH_64_HEX_CHARACTERS"},
  "metadata": {"path": "METADATA_SET.tsv", "sha256": "REPLACE_WITH_64_HEX_CHARACTERS"},
  "exclusions": {"path": "EXCLUDED_IDS.txt", "sha256": "REPLACE_WITH_64_HEX_CHARACTERS"},
  "columns": {"id": "id", "x": "TRIMAP1", "y": "TRIMAP2", "group": "source"},
  "palette": {"reference": "#666666", "isolate": "#0072B2", "MIBiG": "#3A78B5"},
  "group_order": ["reference", "MIBiG", "isolate"],
  "expected_points": 100
}
```

The displayed palette keys must match the metadata group values exactly. The
group_order list gives the draw and legend order, with background groups first
and foreground groups last; it must include every group exactly once. This
example is a schema illustration, not an analysis manifest. Replace all hashes,
group keys, the generation and the count with bound source values. For the saved
t-SNE tables use method `tsne` and their actual coordinate columns (for example
`x` and `y`). Coordinates and metadata must have identical unique ID rosters.
The metadata can be an existing PCoA table carrying the same IDs and source groups;
its PCoA coordinates are not used or compared by this tool.

EXCLUDED_IDS.txt contains one exact point ID per line. An empty file explicitly
means no omissions; there are no implicit strain or origin exclusions. Convert
existing scientific selection rules to a reviewed ID list outside this tool and
retain that conversion's source bindings. Do not infer cohort membership from a
strain name. The tool rejects unknown or duplicate excluded IDs, missing groups,
nonfinite coordinates, malformed rows, roster differences and wrong expected
drawn-point counts before creating output.

The output contains PDF, SVG and 300-dpi PNG displays, POINTS.tsv including omitted
points and reasons, and REPLAY_RECEIPT.json. Counts are coordinate rows, not the
number of proteins represented by a centroid. The ledger retains numeric values;
input hashes preserve the exact original text and metadata. Figure axes have no
explained-variance percentages. Input and direct producer hashes are checked again
before the final receipt. A failure leaves any partial artwork without a successful
receipt. PDF bytes can differ with export metadata, fonts or plotting versions;
membership and input bindings are the replay contract.

Group color and presence are display choices supplied by the manifest. This
initial adapter does not reproduce historical identity fills, per-strain labels,
nearest-neighbor statistics or every publication layout. Such
extensions need their own explicit input contracts and tests. A successful replot
does not validate the original fitting environment, stochastic stability or any
scientific interpretation.
