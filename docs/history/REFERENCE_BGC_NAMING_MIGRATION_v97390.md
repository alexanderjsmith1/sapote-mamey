> **Historical page.** Replaced by [the reference-BGC structural validator page](../REFERENCE_BGC_STRUCTURAL_VALIDATOR.md). It records why the v9.7.390 cut renamed this component.

# Reference-BGC validator: v9.7.390 naming migration

The generic Sapote-Mamey component and its generated artifacts use `reference_bgc_*` names. A `WAC` token is retained only when it is part of an actual strain designation or cited source identity, and in one input filename kept for compatibility (next paragraph). It is not a Sapote-Mamey subsystem, validation standard, contributor attribution, or product affiliation.

`tools/seed_reference_library.py` still accepts the pre-v9.7.390 structural-CSV filename, `resources/reference_seed_inputs/wac_validation_structural.csv`, when no nonempty CLI or `MAMEY_SEED_STRUCT` environment path is given and the generic default `reference_bgc_structural.csv` is absent (`tools/seed_reference_library.py:38-49`); it prints a `DEPRECATION` warning. The code comment marks it for removal after the deprecation window. That fallback is input-only, emits a warning, and does not change the primary command or output names. The earlier validator script name is not retained as an executable wrapper because the tool was operator-only and not cut-wired; retaining a branded command would perpetuate the misleading public interface.
