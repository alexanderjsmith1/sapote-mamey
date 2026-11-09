# Tier Patch Receipt — v9.7.148c

> **Historical page.** It is a record of one old tier patch, not an instruction. It names a source archive and a build stamp but does not identify or hash the patched output, so it cannot show which bytes carried the patch or what the final version was. The file list below repeats names (for example `AGENTS.md` and `README.md`) without saying whether each repeat is a separate stage. Two paths in it, `docs/ISSUES_EXPERIENCED_DURING_DEVELOPMENT.md` and `validation_logs_v97148c/`, are not in the current tree; the issues log is now at `docs/history/retired_458/ISSUES_EXPERIENCED_DURING_DEVELOPMENT.md`. Current release status is in [RELEASE_MANIFEST](../../RELEASE_MANIFEST.md).

Tier: `CODE`  
Source: `sapote-mamey-v9.7.148c-CODE-20260629.zip`  
Build stamp target: `20260629v97148d`  
Authoritative bundle version: `9.7.148c`  
Engine: `1.9.100`

This tier was produced by applying the v9.7.148c audit-response patches
(BLOCK-A, BLOCK-B, F001) to the v9.7.148b CODE candidate, then the
v9.7.149 hygiene patches (R001–R004) to the v9.7.148c CODE candidate.
It was not merely renamed.

## Files changed in v9.7.148c (from v9.7.148b)

- RELEASE_MANIFEST.md
- CHANGELOG.md
- AGENTS.md
- TAG
- BUILD_STAMP.txt
- mamey/__init__.py
- AGENTS.md
- AGENTS.md
- AGENTS.md
- AGENTS.md
- README.md
- README.md
- docs/BUNDLE_CAPABILITIES.md
- docs/CHATGPT_EXECUTION_SLICE_v97147.md (cover_overlap_fix, compiled_report_build_order)
- docs/ISSUES_EXPERIENCED_DURING_DEVELOPMENT.md (new — full development issues log)

## Files changed in hygiene pass (R001–R004)

- RELEASE_MANIFEST.md (Derived sync anchors stamp; Functional scope heading)
- validation_logs_v97144b/ → validation_logs_v97148c/ (directory rename)
- TIER_PATCH_RECEIPT_v9.7.148c_CODE.md (this file, created)
