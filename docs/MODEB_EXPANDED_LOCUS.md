# Include supported external loci in a Mode B card

Use this route when a `current50_v2` interpretation needs saved rescue evidence
outside its focal region. You need the complete assembly GenBank, matching
package, saved rescue results and reviewed rulings. The focal card identity
stays **strain / full node-or-contig / region / BGC alias**.

## Build the assembly inventory

Select the whole-assembly member from the ZIP, not a region GBK. This example
calls it `EXAMPLE.gbk`; replace that name with the actual archive member:

```bash
python tools/build_modeb_locus_inventory.py --input inputs/EXAMPLE.zip \
  --gbk-member EXAMPLE.gbk --package runs/EXAMPLE/package --strain EXAMPLE \
  --out reviews/EXAMPLE-inventory.json
```

The inventory binds the archive/member and package CDS table by hash. It records
contig, locus tag, one-based inclusive coordinates, strand, translated length,
normalized protein hash and region identity. Unflagged loci say
`no antiSMASH region / no BGC alias`.

Choose a new output file. The exporter refuses an input alias but can replace
an unrelated existing output. Keep the source files stable while it reads them.

## Emit and write the card

```bash
python mamey_run.py emit-modeb-template --package runs/EXAMPLE/package --bgc BGC001 \
  --contract current50_v2 --gap-rescue-dir inputs/EXAMPLE-rescue \
  --rescue-locus-inventory reviews/EXAMPLE-inventory.json \
  --out reviews/EXAMPLE-mode-b.md
```

If a separately reviewed gene-ruling table overrides the saved run, supply it
with `--rescue-gene-adjudication-tsv`. Its reference name and candidate locus must
bind exactly one external row. Pair reviews use the separate
`--rescue-verdicts-tsv` input. Keep original and effective rulings visible.

Write the emitted sections from the evidence. Preserve the canonical first-line
identity and machine-readable scope declaration. Section 50 must include the
complete selected CDS roster and separate evidence channels; repeated appearances
of one gene do not increase coverage.

## Understand the selected scope

External matches join through normalized protein hash and exact locus/location.
Effective SUPPORTED anchors select their CDS plus 2,500 bp on either side,
clipped to the contig. Overlapping or adjacent windows merge. Each overlapping
CDS is included whole, without recursively expanding the window; shared CDSs
count once and distant windows stay separate.

The roles are `CORE`, `SUPPORTED_ANCHOR` and `NEIGHBOUR_CONTEXT`. Neighborhood
context is not automatic pathway membership. Weaker matches and split-piece
rivals remain alternatives; they do not automatically select primary intervals.
The original core-region census remains separate from the expanded roster.

Sections 3 and 26 show interval identities. Section 50 carries geometry,
protein hashes and reference rulings. Carry the selected scope into the other
applicable interpretation sections and into any comparison's denominators.

## Verify expanded scope

After writing, run:

```bash
python mamey_run.py verify-modeb reviews/EXAMPLE-mode-b.md --contract current50_v2 \
  --package runs/EXAMPLE/package --bgc BGC001 --require-expanded-locus
```

`--require-expanded-locus` is necessary when expanded scope is required; ordinary
v2 verification also accepts core-only cards. The verifier reopens the pinned
GenBank, compares translations/locations and package membership, rebuilds the
selection, and checks the visible interval and per-gene rows. Missing declarations,
source drift, dropped genes and mismatched focal identity fail.

These checks bind the selected evidence and roster. Biochemical interpretation,
paralog resolution, physical continuity and figure meaning still need review.
Add `--report-json` to save a verification report, choosing a fresh path.

## Use the matching emitter

The native route above explicitly chooses `current50_v2`. The full50 wrapper
selects it when expanded-inventory or gene-adjudication inputs are supplied;
`--gap-rescue-dir` alone does not select that route, and the wrapper has no
`--contract` option.

`modeb-round` and `deliverable-queue` keep the full48 scaffold. Expanded-specific
inputs can produce per-card `EXPANDED_LOCUS_CONTRACT_REQUIRED` skips while an
index or empty worklist is still written. Check emitted counts.
`modeb-round --from-precompute` is unavailable and returns
`COHORT_PREFILL_SOURCE_BINDING_UNAVAILABLE`; it cannot replace this source-bound route.

See [saved gap-rescue inputs](MODEB_GAP_RESCUE_READER.md) for required files and
recovery. Keep inventory, source hashes, rulings, authored card and verification
findings together without duplicating the assembly archive or whole package.

<a id="offline-inventory-and-inputs"></a>
<a id="selection-and-interpretation"></a>
<a id="verification-and-limits"></a>
<a id="reader-admission-safeguards"></a>
<a id="owned-outputs-and-source-selection"></a>
