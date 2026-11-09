# Include supported external loci in a Mode B card

Use this route when a `current50_v2` interpretation needs saved rescue evidence
outside its focal region. You need:

- the antiSMASH ZIP and the matching package;
- saved gap-rescue results, made by `python mamey_run.py gap-rescue`. That command is heavy and runs one genome at a time. See the [gap-rescue guide](MODEB_GAP_RESCUE_READER.md) for what it needs and what it writes;
- any reviewed gene rulings.

The focal card identity stays **strain / full node-or-contig / region / BGC alias**. Terms are in the [glossary](GLOSSARY.md).

## Build the assembly inventory

Select the whole-assembly GenBank member from the ZIP, not a region GBK. To list the members, run
`unzip -l inputs/EXAMPLE.zip`. The whole-assembly member is the one `.gbk` file that is not a region file.
antiSMASH names region files with `.regionNNN.gbk` (for example `.region001.gbk`), so skip those.
Give the member name exactly as `unzip -l` prints it, including any folder. The command refuses a
name that matches no member or more than one. This example calls it `EXAMPLE.gbk`; replace that
name with the member you found:

```bash
python tools/build_modeb_locus_inventory.py --input inputs/EXAMPLE.zip \
  --gbk-member EXAMPLE.gbk --package runs/EXAMPLE/package --strain EXAMPLE \
  --out reviews/EXAMPLE-inventory.json
```

The command prints one JSON line when it succeeds, with the keys `inventory` (the output path),
`sha256` and `translated_CDS` (the gene count). It fails if the member does not contain every gene in
the package's CDS table, or if a gene's coordinates or length disagree with that table.

That is the only coverage check. The command does not read a separate list of the assembly's contigs,
so it cannot show that the member holds every contig, including contigs with no translated CDS. The
inventory records this in `coverage_check`: `package_cds_reconciled` is `true`,
`contigs_with_translated_cds` gives the count it read, and `whole_assembly_contig_coverage` is
`NOT_VERIFIED_NO_INDEPENDENT_CONTIG_ROSTER`. Compare that count with the assembly's contig count
yourself if whole-assembly coverage matters.

The inventory file binds the archive, the member and the package CDS table by hash. For each gene it
records the contig, locus tag, one-based inclusive coordinates, strand, translated length,
normalized protein hash and region identity. Genes outside any region say
`no antiSMASH region / no BGC alias`.

`--out` must be a new file. The command refuses an existing file, or a path that is one of its inputs,
before it reads anything, and leaves that file unchanged. It writes the inventory to a hidden
temporary file in the same folder and links it into place only when it is complete, so a failure
leaves no file at `--out`. If the run is killed, look for a leftover `.<name>.*.tmp` file in that
folder and inspect it before you remove it. Keep the source files unchanged while it reads them.

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
An effective SUPPORTED anchor selects its CDS plus 2,500 bp on either side,
clipped to the contig. Overlapping or adjacent windows merge. Each overlapping
CDS is included whole, without widening the window again. A shared CDS
counts once. Distant windows stay separate.

Example: one anchor CDS spans 10,000 to 10,900 on a contig. Its window is 7,500 to 13,400. A
second anchor at 13,500 to 14,000 has the window 11,000 to 16,500. The windows overlap, so they
merge into 7,500 to 16,500. Every CDS that overlaps that span is selected whole.

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
index or empty worklist is still written. Check the emitted counts.

See [saved gap-rescue inputs](MODEB_GAP_RESCUE_READER.md) for required files and
recovery. Keep inventory, source hashes, rulings, authored card and verification
findings together without duplicating the assembly archive or whole package.
