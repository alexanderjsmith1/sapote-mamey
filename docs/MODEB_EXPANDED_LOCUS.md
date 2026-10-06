# Mode B interpretation across supported rescue contigs

This candidate extends the existing current50_v2 emitter and verifier. It preserves
the accepted 50-section contract and its SHA-256. It reads existing offline evidence;
it performs no sequence search and assigns no numerical rescue probability.

The focal four-part identity remains the card identifier. Core counts and expanded
interpretation counts are separate. An effective gene-level SUPPORTED ruling is an
anchor for selecting bounded neighbourhood context, not proof that every neighbouring
CDS is a pathway member. Pair-level findings remain a separate evidence layer.
This patch infers zero physical contig joins and no product or production.

## Offline inventory and inputs

Build a translated-CDS inventory from an explicitly selected whole-assembly GenBank
member and the private package's CDS table:

```sh
python tools/build_modeb_locus_inventory.py --input assembly.zip \
  --gbk-member strain.gbk --package package_copy --strain AS-XXX --out inventory.json
python mamey_run.py emit-modeb-template --package package_copy --bgc BGC001 \
  --contract current50_v2 --gap-rescue-dir rescue_folder \
  --rescue-gene-adjudication-tsv reviewed_gene_rulings.tsv \
  --rescue-locus-inventory inventory.json --out MODE_B.md
python mamey_run.py verify-modeb MODE_B.md --contract current50_v2 \
  --package package_copy --bgc BGC001 --require-expanded-locus
```

The explicit gene-adjudication file overrides the conventional automatic lookup.
Its reference name and candidate locus must bind exactly one external rescue row;
an optional contig field must agree with that row. Run and effective rulings are
both retained. An absent explicit file or binding conflict creates a source hold.
`--rescue-verdicts-tsv` continues to carry pair-level reviews independently.
Use the native `emit-modeb-template --contract current50_v2` route above or the
full50 wrapper with expanded-specific source flags; it automatically selects native
`current50_v2` for those inputs. The wrapper exposes no `--contract` flag.
`modeb-round` and `deliverable-queue` expose these source flags but emit the default
legacy scaffold profile; they do not select current50_v2. Supplying expanded inputs
to those batch routes creates a typed CONTRACT_REQUIRED refusal, so use the native
explicit-v2 route for an expanded work order.

The inventory stores exact contig, locus tag, one-based inclusive coordinates,
strand, translated length, normalized AA SHA-256 and full region identity. It pins
the assembly archive/member and package CDS table. Literal GenBank LOCUS names are
retained where ACCESSION/VERSION identifiers lose zeroes in decimal coverage.
Unflagged loci explicitly say `no antiSMASH region / no BGC alias`.

## Selection and interpretation

The complete focal CDS roster must match package gene facts. External rescue rows
join through both normalized AA SHA-256 and exact locus/location, never an alias
alone. Effective SUPPORTED anchors select their own CDS plus 2,500 bp on each side,
clipped to the contig. Overlapping seed windows merge. Every overlapping CDS is
included whole, even if it extends beyond the seed boundary; there is no recursive
extension. Distant windows remain separate, and a shared CDS is counted once.

Roles are CORE, SUPPORTED_ANCHOR and NEIGHBOUR_CONTEXT. Weaker reference finds remain
in an alternatives table. Repeated PKS modules and many-to-one reference placements
do not become independent pathway genes or a completed megasynthase.
Saved split-piece rivals bind exact inventory locations and require their canonical
AA sequence in the pinned query collection. The split table supplies no query ID;
this verifies existence in that collection, not a reconstructed per-piece alignment.
Such rows remain rival context and never select primary intervals automatically.

Scope context routes into sections 3, 5, 6, 7, 8, 10, 19, 22, 26, 36, 37, 38, 43, 44
and 50, including sections whose original core-only applicability predicate is false.
Sections 3 and 26 carry interval identities; section 50 preserves the complete CDS
roster with geometry, AA hashes and run/effective reference rulings. Authors must
replace scaffolding with scientific synthesis over that scope and add each gene's
separate evidence channels. GECCO probability, called membership and reference
annotations remain separate. Authored PCoA comparisons and plots must cover the selected interpretation scope and
retain embedded-observation versus regional-census denominators. This patch supplies
scope and authoring requirements; figure generation uses its separate reviewed workflow.

## Verification and limits

The saved card carries a machine-readable scope declaration. Verification checks
source hashes and rebuilds the selection from pinned inventory/rescue inputs; a
dropped hidden gene cannot be hidden by rehashing the declaration. It also checks
visible interval identities in sections 3, 26 and 50 and each exact-identity AA-hash
gene row in section 50. Missing declarations, source drift, unbound inputs or dropped
selected genes fail. Ordinary v2 cards without the new inventory remain compatible.
Validated selected/alternative loci extend the genomic-existence context for the
same card strain and package. They do not extend the core gene roster or its BGC
membership map. Genuine unflagged rescued neighbours therefore avoid a false
PHANTOM_LOCUS error while wrong-strain, wrong-package or unbound declarations
cannot grant existence.
The channel matrix has an explicit selected-CDS roster separate from the package's
core membership roster. Coverage counts unique genes in that primary named-match
matrix; scope, reference and domain tables cannot inflate the denominator by repeating
the same genes. The core census remains the deterministic package count.

The structural verifier cannot establish correctness of biochemical interpretation,
validate the operator's source selection, resolve paralogs, prove physical linkage
or validate figure meaning. Independent source and scientific review are required.
A work order requiring expanded scope must invoke `verify-modeb --contract current50_v2
--require-expanded-locus`. This independently refuses an absent declaration even if
both the emitted cue and declaration have been removed. The default remains compatible
with ordinary core-only v2 cards.
No full engine suite, release seal or scientific adoption is implied by targeted tests.

## Reader admission safeguards

The verifier reparses the pinned whole-assembly GenBank member with the same offline
CDS reader used by the exporter, then compares the complete translation, location,
strand and contig-length inventory independently. It also reconciles canonical
region membership against the pinned package CDS rows. A duplicate ZIP member,
missing source CDS, changed member hash or fabricated inventory row creates a hold.
These checks bind recorded translations; they do not validate gene function.

The exporter refuses outputs that alias either input by path or inode. Inputs must
remain stable during the read; this is not arbitrary concurrent-writer containment.
Selected locus tags must be unambiguous for the per-gene evidence matrix. Section
headings and visible rosters inside comments, code fences or indented examples
cannot satisfy scope evidence. Context admission requires the first-line canonical
identity to match the focal scope, plus the actual selected package and BGC.

Expanded-specific emitter flags require `--contract current50_v2`; a legacy emitter
refuses them explicitly. The full50 wrapper selects native `current50_v2` when those
flags are supplied and preserves its existing 50 sections without legacy remapping.
Without expanded-specific flags, the wrapper retains its existing migration route.
