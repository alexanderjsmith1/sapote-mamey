"""Registry for the next-ten Sapote–Mamey patches.

This is intentionally lightweight: patch chat can wire these names into the real CLI,
docs, validators, and release receipts.
"""

NEXT_TEN_PATCHES = [
    "FIGURE_RENDERER_V2",
    "EFLS_REWIRE",
    "COMPARATOR_ANTISMASH_INGEST",
    "DIRECTED_STUDY_WORKBOOK",
    "LCMS_HANDLE_REGISTRY_V2",
    "CITATION_WORKORDER_RESOLVER",
    "MODEB_FULL20_VALIDATOR",
    "BACKGROUND_CONTROL_BRANCH",
    "DUAL_LLM_HANDOFF_RECEIPT",
    "LEGACY_FEATURE_MATRIX_GATE",
]

BEE_STRAIN_REGRESSION_SPEC = {
    "SetA": ["NODE_96", "NODE_107", "NODE_24", "NODE_249"],
    "SetB": ["NODE_456", "NODE_58"],
    "excluded_background": {
        "BGC011": "streptophenazine purified; active antifungal likely elsewhere"
    },
}
