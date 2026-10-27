# Portable strain privacy and evidence registry

Sapote-Mamey can be used with a collection in which genome availability, bioassay scope, fractionation depth, and release status vary by strain. These facts remain separate. A genome does not imply a screen, a screen does not imply a fraction, a fraction does not imply chemical identity, and strain-level evidence does not establish a BGC-level causal link.

## Privacy profiles

Copy [`examples/privacy/strain_privacy_profile.example.json`](../examples/privacy/strain_privacy_profile.example.json) and replace the generic names with your own opaque strain IDs and access tiers. The profile supports any number of named tiers. Only tiers with `"public_export": true` map to the existing `PUBLIC` package release class. Every other tier maps to `PRIVATE` at that package boundary.

The default tier must be non-public. A strain omitted from the exact assignment list remains non-public instead of inheriting a decision from an ID prefix or filename. A `--release PUBLIC` request cannot bypass the profile: a nonpublic tier remains PRIVATE and records `public_override_refused_by_profile`; this resolution is not necessarily a failing run. Inspect the actual package assignment state and release field. Use `--release PRIVATE` only to make an already more restrictive export.

Run a Mamey extraction with a profile using:

```bash
python mamey_run.py run --strain isolate-001 --input-zip isolate-001.zip \
  --privacy-profile privacy/strain_privacy_profile.json
```

The generated package keeps its established binary `release` field for existing consumers and adds the profile's named privacy tier and assignment state per BGC. A profile is operator policy, not scientific evidence and not publication approval.

## Heterogeneous evidence registry

Copy [`examples/privacy/strain_evidence_registry.example.tsv`](../examples/privacy/strain_evidence_registry.example.tsv). The registry preserves a minimal lineage: a `material` row declares an extract or fraction, `parent_material_id` points to the material it came from, and one `assay` row names the panel and target tested against that exact material. This supports unequal pathogen panels and multiple flash/HPLC branch depths without collapsing them into a strain-level positive.

Each material retains its actual level: `crude_extract`, `flash_fraction`, or `hplc_fraction`. A fraction must name a non-root parent. An assay must point to an existing material from the same strain and carry its actual `replicate_state`; `SINGLETON` is not silently converted to replication. `RESULTS_BOUND` means only that a result record has been bound; it does not make a result potent, purified, or genetically attributable.

Validate both registry files before relying on them:

```bash
python tools/validate_portfolio_registry.py \
  --privacy-profile privacy/strain_privacy_profile.json \
  --evidence-registry evidence/strain_evidence_registry.tsv
```

The validator checks required nonblank headers/values, unique record/material IDs, evidence/material/assay-state vocabularies, parent existence, fraction non-root parents, assay-to-material strain agreement, and profile-tier agreement. It also refuses cyclic parent lineage and parents from another strain. It does not check `replicate_state` against a vocabulary or open each `source_locator`. A PASS is therefore a limited metadata check, not complete lineage or result-source verification. It prints an availability summary only. It does not import assay measurements into a genome run, score a BGC, or produce a scientific conclusion.

For a recorded result, separately verify the source bytes and replicate meaning before scientific use. Preserve unresolved source/lineage states rather than inferring them from RESULTS_BOUND.

A `--project-registry` input is a separate registry format. Current extraction refuses pairing it with `--privacy-profile`; the registry records policy/context while the profile owns named-tier/binary release resolution. See [the project catalog guide](PROJECT_CATALOG.md) for that separate workflow, and [project-registry validation limits](PROJECT_CATALOG.md#project-registry-validation-and-receipt-limits) for what its loader checks.

## Export boundary

This registry is an operator-controlled input. A public cut must still pass the release manifest, denylist, redaction, and leak-audit gates. Privacy assignment, evidence admission, biological validation, owner acceptance, and publication release remain independent decisions.
