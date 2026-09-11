# Interactive widget deliverables

`render-widgets` turns a sealed Mamey package into a portable, dependency-free
interactive reader bundle. It accepts an unpacked `package/` directory or a
`*_Complete_Package.zip` and writes a **separate sibling deliverable**:

```bash
python mamey_run.py render-widgets \
  --package AS-XXX_SapoteMamey_v9.7.342_engine1.9.119_Complete_Package.zip
```

Use `--outdir PATH` to select another output directory. The output path is
rejected if it is the package directory or is nested inside it.

## Delivered views

1. BGC priority explorer — configurable AB/AF/novelty/length axes, boundary and
   tier filters, KCB-aware search, vector SVG and filtered CSV export.
2. Domain architecture explorer — package-native PKS/NRPS/release-domain counts
   with metric selection and SVG/CSV export.
3. CCTT and KCB evidence explorer — diagnostic triggers and similarity anchors
   shown beside standing-rule and mis-anchor guards.
4. RG-GMCI relationship explorer — confidence/score filtering with an explicit
   no-physical-linkage ceiling.
5. Evidence completeness explorer — package/gate/claim-safety states and the
   missing-data worklist, without treating missing evidence as a biological zero.

Open `OPEN_WIDGETS.html`; every page is self-contained and works over `file://`
without a web server, external JavaScript, or network access.

## Publication handoff

The bundle includes `PUBLICATION_HANDOFF.md` and
`publication_metadata.json`. These record caption and methods templates,
citation status, the source-package fingerprint, export formats, and the claim
ceiling. Charts export as editable SVG and filtered data export as CSV. The
handoff marks unresolved dataset and biological citations as `citation_needed`;
it never manufactures references.

## Gate semantics

This command is post-seal and reader-side. It does not re-run antiSMASH,
re-score BGCs, author Mode B judgments, modify the package, or upgrade package,
release, biological, figure, or publication status. A widget `PASS` means only
that the reader bundle was written reproducibly from the named source artifacts.
