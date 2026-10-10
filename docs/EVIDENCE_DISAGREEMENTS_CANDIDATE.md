# Gene evidence disagreement review candidate

Run `python tools/evidence_disagreements.py --selection selection.json` from a
patched extracted bundle, using Python 3.12 or newer. The private server binds
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

## Service, audit and portable-output limits

`mamey/evidence_disagreements.html` is an API client served by this tool, not a standalone data export. Browser search and retained-hit/reference pagination use25-row pages. The surface has no download exporter, correction writer or evidence-index acceptance route. Missing/binding-hold and recorded-no-hit cues remain distinct; a filter yielding no rows is not biological absence. See [HTML evidence views](HTML_EVIDENCE_VIEWS.md).

The audit selects up to five distinct available records using source-state predicates; it does not refuse when fewer are available. Its `five_records` key is a historical name, not proof that all five source-state cases were audited. `SOURCE_BOUND_ENGINEERING_REVIEW_ONLY` is a bounded mechanical snapshot, not complete-population review, cross-channel adjudication or section acceptance. Source stability hashes are rechecked before writing the audit (`mamey/evidence_disagreements.py:206–218`).

The output existence precheck is followed by direct `write_text`, not exclusive/atomic creation; no parent directory is created and a failure can leave partial bytes. The saved audit includes source/session receipts and selected records, but does not bind the selection-file hash, builder/template hashes or its own output hash. Record these in an external receipt and use a fresh candidate path. A successful startup, API response or zero exit from audit mode does not prove scientific acceptance. Serving checks source stamps on requests, while full digest checking is explicit at audit completion; frozen inputs and trusted local source dependencies remain prerequisites (`57–92,206–245`).
