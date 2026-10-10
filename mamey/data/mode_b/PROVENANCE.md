# Mode B machine contract data provenance

The historically named `modeb_full30_corrective_contract.json` contains schema `modeb_corrective_full48_v1` and the full48 finished profile. It is the default loaded by `mamey/modeb_structure_gate.py` and default native authoring helpers. The filename's “full30” is historical; use its schema/profile and actual section list rather than inferring a count from the filename.

This is **one** current profile. `modeb_current50_v2_contract.json` defines the opt-in current50_v2 profile, selected explicitly by native emission/verification. Carry the same selection through both operations. A default full48 check does not prove current50_v2 acceptance; fixed48 document renderers have a separate contract and must not be used to truncate a selected 50-section card.

Read [the profile matrix](../../../docs/MODEB_PROFILE_MATRIX.md), [native user walkthrough](../../../docs/MODE_B_USER_WALKTHROUGH.md) and [current docs index](../../../CURRENT_DOCS_INDEX.md). The earlier `docs/CURRENT_DOCS_INDEX.md` path does not exist in this cut; the index is at bundle root.

Contract JSON owns its exact section titles/order and selected requirements. Generated contract documentation belongs to its declared generator; assistants must not substitute invented sections or count a scaffold/evidence appendix as completed authored prose. Verify actual identity, evidence and selected-profile content, and retain source/artifact hashes and unresolved holds. Structural PASS is not scientific adoption.

The retired standalone 20-section contract at `legacy/modeb_full20_corrective_contract_legacy_v97144.json` remains historical. A specialized legacy scaffold may still use 20-section checks; that does not make it the current finished native profile. Keep historical artifacts rather than silently migrating their claims.

The default full48 profile spans §1–§48; the explicitly selected current50 route remains a distinct contract.
