# ACCEPTANCE_TESTS_MODE_B_FULL20_CONTRACT.md

## Contract tests to add or maintain

### Test 1 — Full Mode B requires all 20 exact corrective-protocol sections

Given a Mode B markdown card labelled `Full Mode B`, validation fails unless all 20 exact section names from `mamey/data/mode_b/modeb_full20_corrective_contract.json` are present in order.

Expected result: FAIL for `§1–§8` only.  
Expected result: FAIL for `§1–§10` only.  
Expected result: FAIL for the obsolete title `Manual BLASTP evidence, if present` at §7.  
Expected result: PASS for all 20 exact current sections.

### Test 2 — LLMs cannot make up sections

The section list is locked. A renderer or assistant may not rename `§7. Transport, resistance, and regulation` to a BLASTP section, may not move BLASTP/HMMER out of §16, and may not substitute older section titles.

### Test 3 — Candidate card cannot masquerade as Full Mode B

A candidate card may pass as `candidate_card`, but must fail if metadata says `treatment_status = full Mode B` and the 20 exact sections are absent.

### Test 4 — Integrated table is supplemental only

A report consisting only of an integrated evidence table, target-region summary, or core-like gene table must fail Full Mode B validation unless the 20 exact sections are also present and §4 contains prose interpretation.

### Test 5 — Fragments retain shell, not silence

A fragment-level card may contain short sections, but the 20 section headings must remain present, with unavailable evidence stated. Missing headings fail. Empty unavailable sections fail if they omit the reason.

## Current exact titles

1. **Identity and node/region**
2. **Why this BGC was selected**
3. **Boundary and assembly status**
4. **Gene-by-gene interpretation**
5. **Core biosynthetic logic**
6. **Tailoring and maturation logic**
7. **Transport, resistance, and regulation**
8. **Comparator/KCB interpretation**
9. **Alternative hypotheses**
10. **Fragmentation and co-capture risks**
11. **Product-family interpretation**
12. **Bee/microbe ecological interpretation**
13. **Antibacterial/antifungal relevance**
14. **What cannot be claimed**
15. **Missing evidence**
16. **BLASTP/HMMER next steps**
17. **LC-MS / fermentation implications**
18. **Figure/locus-map notes**
19. **Final Mode B judgement**
20. **Next actions**
