from __future__ import annotations

from mamey.modeb_publication_gate import publication_quality_findings


def _card(*, table_break=False, omit=(), weaken_section=None) -> str:
    anchors = {
        5: ["Committed-step genes", "Reaction-level sequence", "Minimal-gene-set audit",
            "Strongest alternative", "Evidence for the alternative",
            "Evidence against the alternative", "Claim ceiling"],
        6: ["Direct tailoring candidates", "Broad metabolic context", "Conditional pathway order",
            "Non-diagnostic enzyme families", "Comparator conflicts", "Coupling evidence",
            "Discriminating tests"],
        7: ["Transport adjudication", "Resistance adjudication", "Regulation adjudication",
            "No exact-bound evidence versus biological absence"],
    }
    out = []
    for n in range(1, 49):
        if n in set(omit):
            continue
        out.append(f"## §{n} Section {n}")
        if n == 3:
            out.extend([
                "#### Boundary and completeness audit",
                "| Source | Observed boundary | Limitation | Effect on interpretation |",
                "|---|---|---|---|",
                "| sealed package manifest | interior region | antiSMASH boundary is predictive | no product claim transfers beyond displayed interval |",
            ])
        elif n == 4:
            # v9.7.373 (BREAK-3): both gates locate the §4 matrix by the shared title locator
            # (find_s4_matrix_block), so the fixture must carry the canonical named-match heading a
            # real card always has. Adding the heading preserves every assertion below; it just puts
            # the table where the shared locator looks.
            out.extend(["#### Complete named-match, channel-separated table",
                        "| locus | nr accession | matched protein | organism | identity |",
                        "|---|---|---|---|---|"])
            if table_break:
                out.append("")
            out.append("| ctg1_1 | WP_1 | enzyme | Nocardia testii | 90% |")
        elif n in anchors:
            for anchor in anchors[n]:
                shown = "Generic discussion" if weaken_section == n and anchor == anchors[n][0] else anchor
                out.extend([f"#### {shown}", "Evidence-grounded content for ctg1_1."])
        elif n == 9:
            out.extend([
                "#### Competing hypotheses",
                "| Hypothesis | Evidence for | Evidence against | Discriminating test | Current disposition |",
                "|---|---|---|---|---|",
                "| narrow peptide pathway | exact ctg1_1 architecture | product unmeasured | targeted deletion plus LC-MS | leading but unverified |",
                "| primary-metabolism island | common enzyme context | specialized-gene order | boundary-aware synteny test | retained alternative |",
            ])
        elif n == 20:
            out.extend([
                "#### Highest-information next action",
                "| Action | Evidence gap resolved | Measured or computed result | Decision change | Claim ceiling |",
                "|---|---|---|---|---|",
                "| delete ctg1_1 with complementation | locus attribution | replicated LC-MS feature difference | retain or reject the leading model | capacity remains unproven until measured |",
            ])
        elif n == 26:
            out.extend([
                "#### Pathway-grounded rationale",
                "The exact ctg1_1 locus model motivates carbon and phosphate perturbations.",
                "#### Condition matrix",
                "| Condition | Perturbation | Pathway rationale | Measured readout | Decision rule |",
                "|---|---|---|---|---|",
                "| low phosphate | phosphate reduction | test phosphate-linked regulation | LC-MS feature plus biomass | retain only reproducible genotype-linked change |",
                "| alternate carbon | glucose to glycerol | test carbon control of ctg1_1 | LC-MS/MS feature plus growth | prioritize a condition only after batch replication |",
                "#### Controls and claim ceiling",
                "Wild type, ctg1_1 perturbation and complemented controls are required; a condition-linked feature alone is not locus attribution.",
            ])
        elif n == 27:
            out.extend([
                "#### Candidate gene orientation",
                "| Gene | Physical membership | Candidate role | Evidence source | Class concordance | Allowed inference |",
                "|---|---|---|---|---|---|",
                "| ctg1_1 | EXACT_REGION | resistance-like candidate | antiSMASH plus BLASTp | UNRESOLVED | lead-priority context only |",
                "#### Claim ceiling",
                "ctg1_1 is not assigned as self-resistance without compound-class concordance.",
            ])
        elif n == 36:
            out.extend([
                "#### Overmerge / locus-splitting adjudication",
                "| Model | Genes or interval | Evidence for | Evidence against | Decision consequence |",
                "|---|---|---|---|---|",
                "| intact locus | ctg1_1 interval | compact gene order | predictive boundary only | analyze displayed interval provisionally |",
                "| split or overmerged locus | ctg1_1 plus flanks | neighboring metabolism | no cross-boundary sequence proof | quarantine outside genes |",
            ])
        elif n == 45:
            out.extend([
                "#### Cohort comparison denominator",
                "Two exact loci from two strains were compared.",
                "#### Cohort gene comparison",
                "| Comparator exact locus | Query genes | Comparator genes | Sequence / synteny evidence | Agreement and mismatch | Allowed inference |",
                "|---|---|---|---|---|---|",
                "| AS-2 / NODE_2_length_20000_cov_20.000000 / region001 / BGC002 | ctg1_1 | ctg2_1 | count-first protein comparison | gene order agrees; product untested | cohort gene-family navigation only |",
                "#### Cohort-comparison conclusion",
                "The two exact genes support cohort navigation, not product transfer.",
            ])
        elif n == 46:
            out.extend([
                "#### Type/reference comparison denominator",
                "One profile-compatible exact reference locus was compared.",
                "#### Type/reference gene comparison",
                "| Comparator exact locus | Query genes | Comparator genes | Profile compatibility | Divergence | Allowed inference |",
                "|---|---|---|---|---|---|",
                "| Reference strain / REF_CONTIG_1 / region001 / BGC002 | ctg1_1 | ref_0001 | antiSMASH profile compatible | accessory genes diverge | locus-family navigation only |",
                "#### Type/reference comparison conclusion",
                "The comparison supports navigation, not product identity or activity.",
            ])
        elif n == 47:
            out.extend([
                "#### Host-matched comparison denominator",
                "One unrelated host-matched reference locus was compared.",
                "#### Host-matched gene comparison",
                "| Comparator exact locus | Verified host metadata | Query genes | Comparator genes | Comparator rationale | Sequence / synteny evidence | Transfer limits | Allowed inference |",
                "|---|---|---|---|---|---|---|---|",
                "| Unrelated strain / REF_CONTIG_2 / region001 / BGC003 | verified host metadata receipt HM-1 | ctg1_1 | hostref_0001 | shared host, unrelated lineage | sequence similarity with order mismatch | host context cannot transfer function | comparison navigation only |",
                "#### Host-matched comparison conclusion",
                "Shared host metadata does not establish ecological function or product identity.",
            ])
        elif n == 28:
            out.extend(["#### Evidence-stream disposition", "| Stream | State | Effect |",
                        "|---|---|---|"])
            for stream in ("antiSMASH", "sealed Mamey", "MIBiG", "BiG-SCAPE", "ClusterBlast",
                           "RG-GMCI", "chitin", "resistance", "domain rarity", "literature",
                           "prevalence", "historical card", "V7 evidence",
                           "current channel-separated BLASTp"):
                out.append(f"| {stream} | ADMITTED | Bound effect stated. |")
            out.extend(["#### Historical source-loss reconciliation",
                        "| Source | Disposition | Detail |", "|---|---|---|",
                        "| historical card | RETAIN | Retained useful content. |",
                        "| V7 evidence | REFINE | Refined against current source. |",
                        "| historical locus map | NOT_APPLICABLE | No prior map. |",
                        "#### Section-by-section completeness and predecessor reconciliation",
                        "| Section | State | Evidence | Predecessor | Note |",
                        "|---|---|---|---|---|"])
            for section in range(1, 49):
                out.append(f"| §{section} | SUBSTANTIVE | named source | RETAIN | reconciled |")
        else:
            out.append("Reasoned.")
        out.append("")
    return "\n".join(out)


def _codes(card: str, roster=("ctg1_1",), *, quality_v2=False) -> set[str]:
    return {f["code"] for f in publication_quality_findings(
        card,
        canonical_loci=roster,
        check_substantive_quality_v2=quality_v2,
    )}


def test_complete_scaffold_passes():
    assert publication_quality_findings(_card(), canonical_loci=["ctg1_1"]) == []


def test_blank_line_after_separator_is_broken_and_later_row_does_not_rescue_it():
    assert "BROKEN_MARKDOWN_TABLE" in _codes(_card(table_break=True))


def test_all_48_sections_are_required_for_publication_profile():
    assert "PUBLICATION_SECTIONS_INCOMPLETE" in _codes(_card(omit={48}))


def test_long_prose_does_not_replace_section5_scaffold():
    card = _card(weaken_section=5) + (" prose" * 2000)
    assert "SECTION_5_SCIENTIFIC_SCAFFOLD" in _codes(card)


def test_sections6_and7_have_independent_scaffolds():
    assert "SECTION_6_SCIENTIFIC_SCAFFOLD" in _codes(_card(weaken_section=6))
    assert "SECTION_7_SCIENTIFIC_SCAFFOLD" in _codes(_card(weaken_section=7))


def test_canonical_gene_roster_is_external_to_card():
    assert "PUBLICATION_GENE_TABLE_ROSTER" in _codes(_card(), roster=("ctg1_1", "ctg1_2"))


def test_every_section_requires_predecessor_reconciliation():
    card = _card().replace("| §17 | SUBSTANTIVE | named source | RETAIN | reconciled |", "")
    assert "SECTION_RECONCILIATION_ROW" in _codes(card)


def test_detailed_stream_table_elsewhere_does_not_create_false_duplicates():
    card = _card() + (
        "\n## Detailed supporting-stream accounting\n\n"
        "| Stream | State | Detailed disposition |\n|---|---|---|\n"
        "| antiSMASH | ADMITTED | Exact domain detail retained outside the standardized table. |\n"
        "| sealed Mamey | ADMITTED | Deterministic routing detail retained. |\n"
    )
    assert publication_quality_findings(card, canonical_loci=["ctg1_1"]) == []


def test_reasoned_one_liners_do_not_satisfy_sections_26_46_or_47():
    card = _card()
    for section in (26, 46, 47):
        start = card.index(f"## §{section} Section {section}")
        body_start = card.index("\n", start) + 1
        next_start = card.index(f"## §{section + 1} Section {section + 1}", body_start)
        card = card[:body_start] + "Reasoned.\n\n" + card[next_start:]
    codes = _codes(card, quality_v2=True)
    assert "SECTION_26_PATHWAY_RATIONALE_MISSING" in codes
    assert "SECTION_26_CONDITION_MATRIX_MISSING" in codes
    assert "SECTION_46_COMPARATOR_TABLE_MISSING" in codes
    assert "SECTION_47_COMPARATOR_TABLE_MISSING" in codes


def test_v2_requires_alternatives_boundaries_and_highest_information_next_action():
    card = _card()
    for section in (3, 9, 20, 36):
        start = card.index(f"## §{section} Section {section}")
        body_start = card.index("\n", start) + 1
        next_start = card.index(f"## §{section + 1} Section {section + 1}", body_start)
        card = card[:body_start] + "Reasoned.\n\n" + card[next_start:]
    codes = _codes(card, quality_v2=True)
    assert "SECTION_3_BOUNDARY_AND_COMPLETENESS_AUDIT_MISSING" in codes
    assert "SECTION_9_COMPETING_HYPOTHESES_MISSING" in codes
    assert "SECTION_20_HIGHEST_INFORMATION_NEXT_ACTION_MISSING" in codes
    assert "SECTION_36_OVERMERGE_LOCUS_SPLITTING_ADJUDICATION_MISSING" in codes


def test_typed_unavailable_states_are_accepted_for_sections_26_46_and_47():
    card = _card()
    bodies = {
        26: "OSMAC_NOT_APPLICABLE_TYPED; reason=no fermentation selection in the bound project scope; sources=sealed package and owner selection receipt",
        46: "TYPE_REFERENCE_COMPARISON_NOT_AVAILABLE_TYPED; denominator=0 profile-compatible exact loci; sources=bound reference-panel receipt; reason=no comparable type/reference locus is admitted",
        47: "HOST_MATCHED_COMPARISON_NOT_AVAILABLE_TYPED; denominator=0 verified host-matched exact loci; sources=strain metadata receipt and reference-panel manifest; reason=no unrelated reference has verified matching host metadata",
    }
    for section, replacement in bodies.items():
        start = card.index(f"## §{section} Section {section}")
        body_start = card.index("\n", start) + 1
        next_start = card.index(f"## §{section + 1} Section {section + 1}", body_start)
        card = card[:body_start] + replacement + "\n\n" + card[next_start:]
    assert publication_quality_findings(
        card,
        canonical_loci=["ctg1_1"],
        check_substantive_quality_v2=True,
    ) == []


def test_substantive_quality_v2_is_prospective_not_retroactive():
    card = _card()
    for section in (26, 46, 47):
        start = card.index(f"## §{section} Section {section}")
        body_start = card.index("\n", start) + 1
        next_start = card.index(f"## §{section + 1} Section {section + 1}", body_start)
        card = card[:body_start] + "Reasoned.\n\n" + card[next_start:]
    assert not ({
        "SECTION_26_PATHWAY_RATIONALE_MISSING",
        "SECTION_46_COMPARATOR_TABLE_MISSING",
        "SECTION_47_COMPARATOR_TABLE_MISSING",
    } & _codes(card))
