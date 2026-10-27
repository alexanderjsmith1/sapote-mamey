> **Historical page.** Replaced by [the reference-BGC structural validator page](../REFERENCE_BGC_STRUCTURAL_VALIDATOR.md). It records why the v9.7.390 cut renamed this component.

# Reference-BGC validator: v9.7.390 naming migration

The generic Sapote-Mamey component and its generated artifacts use `reference_bgc_*` names. A `WAC` token is retained only when it is part of an actual strain designation or cited source identity. It is not a Sapote-Mamey subsystem, validation standard, contributor attribution, or product affiliation.

`tools/seed_reference_library.py` accepts the pre-v9.7.390 structural-CSV filename for one deprecation window when the generic default is absent. That fallback is input-only, emits a warning, and does not change the primary command or output names. The earlier validator script name is not retained as an executable wrapper because the tool was operator-only and not cut-wired; retaining a branded command would perpetuate the misleading public interface.
