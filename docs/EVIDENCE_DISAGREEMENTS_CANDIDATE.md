# Gene evidence disagreement review candidate

Run `python tools/evidence_disagreements.py --selection selection.json` from a
patched extracted bundle, using Python 3.11 or newer. The private server binds
only loopback, default port 8767. Use `--port` to change it. `--audit new.json`
writes a deterministic bounded source-review receipt; existing outputs are refused.

Selection schema is `mamey.disagreement-selection/1`. Required fields are an
explicit `population` label, `contract` with relative `path` and SHA-256, and
`sources` entries named `census`, `nr`, `ClusteredNR`, `SwissProt`, `domain`, and
`MIBiG`. Every source requires configurable `root`, contained relative `manifest`
and `manifest_sha256`. Relative roots resolve from the selection directory.
Use only frozen source manifests supported by the shared reader session.

The view conserves census gene occurrences, including overlap, and verifies the
selected channels' census dependency hashes. Missing expanded boundary genes
remain outside this denominator. Search projections require full locus identity,
protein hash, tag and length, with assembly identity checked where supplied.
Domains retain source geometry/sequence holds. KnownClusterBlast reference rows
remain held context without alignment-sequence proof.

Review cues distinguish unspecified versus more specific annotation, partial
domain/module scope, unresolved wording, missing searches and recorded no-hit.
No keyword combination implies biological contradiction. Explicit opposed
structured assertions need the same predicate, term, scope and source provenance;
the source adapters do not invent such assertions. All cues require human review.

Inspect the drawer and paginated retained hits/reference alignments for raw
statements, counterevidence, source files/hashes and metric holds. Each search's
lowest retained rank is only a review representative. The view does not adjudicate
all hit pairs or emit an admitted evidence index. Current50 requirement mapping
does not imply section completeness. This is a candidate, not integrated software
or scientific/release acceptance.
