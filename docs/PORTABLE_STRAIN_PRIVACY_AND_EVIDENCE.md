# Portable strain privacy and evidence registry

Sapote-Mamey can be used with a collection in which genome availability, bioassay scope, fractionation depth, and release status vary by strain. These facts remain separate. A genome does not imply a screen, a screen does not imply a fraction, a fraction does not imply chemical identity, and strain-level evidence does not establish a BGC-level causal link.

## Privacy profiles

Copy [`examples/privacy/strain_privacy_profile.example.json`](../examples/privacy/strain_privacy_profile.example.json) and replace the generic names with your own opaque strain IDs and access tiers. The profile supports any number of named tiers. Only tiers with `"public_export": true` map to the existing `PUBLIC` package release class. Every other tier maps to `PRIVATE` at that package boundary.

The default tier must be non-public. A strain omitted from the exact assignment list remains non-public instead of inheriting a decision from an ID prefix or filename. A `--release PUBLIC` request cannot bypass the profile. Use `--release PRIVATE` only to make an already more restrictive export.

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

The validator checks schema shape, exact unique IDs, material-parent lineage, assay-to-material strain identity, profile-tier agreement, and state vocabulary. It prints an availability summary only. It does not import assay measurements into a genome run, score a BGC, or produce a scientific conclusion.

## Export boundary

This registry is an operator-controlled input. A public cut must still pass the release manifest, denylist, redaction, and leak-audit gates. Privacy assignment, evidence admission, biological validation, owner acceptance, and publication release remain independent decisions.
