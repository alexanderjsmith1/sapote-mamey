# Sapote-Mamey Naming Contract

**Public project / repository:** `sapote-mamey`

**Public bundle name:** **Sapote-Mamey Bundle**

**Sapote** is the umbrella natural-products interpretation framework: literature review, ecology, claim calibration, workbook/reporting standards, manuscript support, and project synthesis.

**Mamey** is the executable BGC-analysis module inside Sapote-Mamey: antiSMASH parsing, source-derived scans, BGC inventory, Mode-B handoff, RG-GMCI/fragmentation review support, workbook write-back, and lead-prioritization outputs.

Reports should write: "This analysis used the Mamey BGC module within the Sapote-Mamey bundle."

Avoid treating Sapote and Mamey as competing tools. Avoid public-facing informal mode names.

## Product name versus executable identity

The public name is a presentation convention, not a runtime/version selector. Preserve bundle version, engine version, build token and source/input hashes separately. In this baseline `BUILD_STAMP.txt` records bundle 9.7.447, engine 1.9.172 and build 20261003v97447a; `TAG` is a matching text label. Their presence is not proof of release acceptance or unchanged source bytes. The local launcher tracks cut and source digest for bytecode provenance (`mamey_run.py:23–67,140–152`).

Use [short-ID provenance](SHORT_ID_REGISTRY.md) for historical display conventions while retaining exact native identities. Documentation/license names do not determine personal-data disclosure or scientific acceptance. `LICENSE` and `LICENSE-DOCS.txt` remain the shipped license metadata; `tools/check_license_docs.py:30–66` checks declared target presence only, not third-party/source permissions or a legal conclusion. Do not rewrite grant files as a documentation fix.
