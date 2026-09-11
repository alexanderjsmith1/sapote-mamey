# Gate-clean Mode B authoring route

This recipe bridges the canonical §1–§48 template to a publication-gate-clean authored candidate.
It governs tooling and evidence presentation; it does not establish scientific correctness,
owner acceptance, release, or publication approval.

## 1. Emit; do not hand-build the section scaffold

```bash
python mamey_run.py emit-modeb-template --package <package_dir> --bgc <BGC_ID>
```

The result is an authoring scaffold. It should pass the structure gate, but it is intentionally
not publication-gate-clean while prompts and evidence-dependent states remain unresolved.

## 2. Fill the canonical §4 matrix

Retain this heading exactly:

```markdown
#### Complete named-match, channel-separated table
```

Keep one contiguous table with exactly one row per independently bound displayed gene. Keep full
nr, NCBI ClusteredNR, and local Swiss-Prot in separate columns. State the matched accession, protein,
organism, identity, aligned length, query coverage, and typed evidence state. Do not insert a blank
line between the table separator and first data row. Missing, unreturned, error, or unbound evidence
is a workflow state—not a biological no-hit.

## 3. Fill the three §28 accountability tables

Typed states must be plain table-cell text, not Markdown code spans. For example, use `ADMITTED` as
the cell content in the source file, without surrounding backticks.

### Evidence streams

Provide exactly one row for each stream: antiSMASH, sealed Mamey, MIBiG, BiG-SCAPE, ClusterBlast,
RG-GMCI, chitin, resistance, domain rarity, literature, prevalence, historical card, V7 evidence,
and current channel-separated BLASTp. Each row uses exactly one of:

`ADMITTED`, `CONTEXT_ONLY`, `SUPERSEDED`, `UNBOUND`, `ABSENT_IN_SCOPE`.

The final cell must state how that stream changes—or does not change—the interpretation.

### Historical sources

Provide exactly one row for historical card, V7 evidence, and historical locus map. Each row uses
exactly one disposition:

`RETAIN`, `REFINE`, `WITHDRAW_WITH_REASON`, `NOT_APPLICABLE`.

Each row also states the retained, refined, withdrawn, or non-applicable content and reason.

### Section reconciliation

Provide one row for every §1–§48. Each row needs at least five cells: section; `SUBSTANTIVE` or
`REASONED_NOT_APPLICABLE`; named evidence; one historical-source disposition; and a non-empty
reconciliation note.

## 4. Preserve the §5–§7 reasoning anchors

- §5: Committed-step genes; Reaction-level sequence; Minimal-gene-set audit; Strongest alternative;
  Evidence for the alternative; Evidence against the alternative; Claim ceiling.
- §6: Direct tailoring candidates; Broad metabolic context; Conditional pathway order;
  Non-diagnostic enzyme families; Comparator conflicts; Coupling evidence; Discriminating tests.
- §7: Transport adjudication; Resistance adjudication; Regulation adjudication; No exact-bound
  evidence versus biological absence.

These are reasoning prompts, not permission to add filler. Name the genes and measured evidence being
discussed, or give a reasoned not-applicable disposition.

## 5. Derive cohort and synthesis sections from source receipts

The writer may see this public field contract, but must not create or approve the source receipts.
If a required source-specific receipt is unavailable or fails validation, record the exact typed hold
and the missing input. Do not replace an unmeasured comparison with plausible prose, and do not turn
missing evidence into a biological negative.

- §39 Cross-strain sequence identity: name the complete query and comparator identities; state whether
  the scope is one component or the whole locus; identify the algorithm and version; and report global
  identity, overlap identity, query coverage, and comparator coverage with their separate denominators.
- §40 BiG-SCAPE family / cohort placement: name the completed run, cutoff, canonical qualified-family
  identifier, resolved complete identity for every admitted member, family size, and private/public/mixed
  cohort scope. A path or bare BGC alias is not a complete member identity.
- §42 Horizontal transfer evidence: report the exact query interval, declared baseline population, query
  and baseline ACGT denominators, GC comparison, and coordinate-bound mobile-context observations. Keep
  horizontal transfer `UNRESOLVED` without phylogenetic evidence; state a non-transfer alternative and a
  gene-tree/species-tree test that could distinguish them.
- §48 Cross-cohort synthesis and claim ceiling: use the complete validated upstream receipt inventory,
  not card prose. State a supported leading model, a distinct supported alternative that contradicts it,
  the strongest unresolved evidence, the most restrictive upstream claim ceiling, and exactly one
  highest-information action with both support and refute consequences for the leading model.

These requirements are public reproducibility rules. Private scoring weights, phrase dictionaries,
benchmark or holdout identities, section thresholds, repeated-phrase fingerprints, and per-feature score
deltas are not authoring inputs.

## 6. Gate the actual saved candidate

```python
from pathlib import Path
from mamey.modeb_publication_gate import publication_quality_findings

card_path = Path("<authored-card.md>")
findings = publication_quality_findings(
    card_path.read_text(encoding="utf-8"),
    canonical_loci=<independently_bound_gene_roster>,
)
assert findings == []
```

Run this after saving. A zero-finding in-memory draft does not prove the bytes on disk passed, and a
zero-finding publication gate does not confer scientific correctness or publication approval.
