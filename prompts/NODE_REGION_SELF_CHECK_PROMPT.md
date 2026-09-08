# PASTE THIS AT THE START of any Mode B / BGC review or report task

*(For a plain Claude/ChatGPT chat holding Sapote-Mamey cards — no hooks or CLI run there, so this
prompt is the enforcement. Paste it before you ask for any cross-strain read, lead shortlist, or AF/AB
report. A short RE-CHECK version to paste before the chat ships is at the bottom.)*

---

**HARD RULE — display every individual BGC with its complete exact-locus identity.**

Every reference must carry all four components, in this order:

`strain / full node-or-contig / region / BGC alias`

The BGC alias is a source-scoped display label, not a stable join key. A node/region pair without its
strain can collide across strains; a strain plus alias can point to different loci across runs; and an
identity without the source-scoped alias does not satisfy the display contract. Dropping any component
can produce a wrong scientific attribution.

**If any component is unavailable, STOP and record an identity hold. Do not guess, shorten the
node/contig, or fall back to the alias.**

For every locus named in prose, tables, filenames, headings, and ranked shortlists, use the complete
display:

```text
<strain> / <full node-or-contig> / <region> / <BGC alias>
e.g. DEMO-STRAIN-01 / NODE_000001_length_50000_cov_30.0 / region001 / BGC001
```

Take all four fields from the package's controlling identity record or exact-locus crosswalk and confirm
that they agree with the card and its source files. A protein sequence can identify a protein, but it does
not replace the complete BGC display identity. A family name is a similarity navigator, never a
product-identity or activity claim; AB/AF values are deterministic routing priors, not measured activity.

**Before you output anything, self-check every individual BGC reference:**

1. Does it show strain, the full node/contig, region, and source-scoped BGC alias in the required order?
2. Is the node/contig complete rather than shortened, and are all four fields copied from one bound
   source record?
3. If any field is missing or conflicting, did you stop with an explicit identity hold instead of
   inferring a value?
4. Are distinct complete identities kept separate even when they share an alias, node name, or region
   number?
5. Is the coverage denominator stated up front for any ranked or comparative result?

If you have the bundle and a shell, `mamey verify-citations <your_report.md>` is a useful supplemental
check for missing node/region citations. It is narrower than this four-component contract: a clean result
does **not** establish that strain and source-scoped alias are present or correctly bound. Perform the
four-component self-check above as well.

---

## RE-CHECK (paste this right before the chat delivers)

> Before you give me the report: scan every individual BGC reference in prose, tables, filenames,
> headings, and shortlists. Confirm that each displays `strain / full node-or-contig / region / BGC alias`
> in that order and that all four components came from one bound source record. If any component
> is missing or conflicting, stop with an identity hold; do not guess or fall back to the alias. Confirm
> that no distinct complete identities were merged under a shared alias, node name, or region number.
