"""v9.7.45 (B-8/F-9) — dedicated AB/AF lead boards.

The antibacterial/antifungal lead board previously lived only as AB_auto/AF_auto columns in the triage
board, ranked by one general Rank. `axis_lead_board_rows` produces a pre-sorted single-axis view: clean
leads first, standing-rule / primary-metabolism rows marked in `Downgrade` and sunk to the bottom (not
dropped). This is what makes the saccharide-led raw board (e.g. one AS strain) present a usable #1 lead.
"""
from mamey.lead_board import axis_lead_board_rows, AXIS_LEAD_BOARD_HEADERS


class _T:
    def __init__(self, bgc_id, ab, af, tier="Medium", standing="", pm=False, crank=None, mobile=""):
        self.bgc_id = bgc_id; self.ab_score = ab; self.af_score = af; self.lead_tier = tier
        self.standing_rule_flag = standing; self.primary_metabolism_flag = pm; self.corrected_rank = crank
        self.mobile_element_flag = mobile


class _B:
    def __init__(self, bgc_id, contig, products, kcb=""):
        self.bgc_id = bgc_id; self.contig = contig; self.node_id = contig
        self.products = products; self.kcb_top = kcb


def _fixture():
    triage = [
        _T("BGC021", 58.9, 10.0, standing="saccharide-exclusion"),   # raw top AB but downgraded
        _T("BGC032", 52.3, 35.3),                                    # clean lead
        _T("BGC007", 44.3, 39.3),                                    # clean; top AF
        _T("BGC099", 60.0, 5.0, pm=True),                            # primary-metab, downgraded
    ]
    bgcs = {b.bgc_id: b for b in [
        _B("BGC021", "NODE_9", ["saccharide"]),
        _B("BGC032", "NODE_52", ["NRPS", "halogenated"]),
        _B("BGC007", "NODE_18", ["NRP-metallophore", "NRPS"]),
        _B("BGC099", "NODE_3", ["other"]),
    ]}
    return triage, bgcs


def test_ab_board_clean_lead_first_downgraded_sunk():
    triage, bgcs = _fixture()
    rows = axis_lead_board_rows(triage, bgcs, "ab")
    # clean leads first, by score desc: BGC032 (52.3) then BGC007 (44.3)
    assert rows[0]["BGC_ID"] == "BGC032"
    assert rows[1]["BGC_ID"] == "BGC007"
    # both downgraded rows are at the bottom regardless of their raw score (58.9 / 60.0)
    bottom = {rows[-1]["BGC_ID"], rows[-2]["BGC_ID"]}
    assert bottom == {"BGC021", "BGC099"}
    assert all(r["Downgrade"] for r in rows[-2:])
    assert rows[0]["Board_rank"] == 1 and rows[-1]["Board_rank"] == 4


def test_downgrade_reason_recorded():
    triage, bgcs = _fixture()
    rows = axis_lead_board_rows(triage, bgcs, "ab")
    by_id = {r["BGC_ID"]: r for r in rows}
    assert by_id["BGC021"]["Downgrade"] == "saccharide-exclusion"
    assert by_id["BGC099"]["Downgrade"] == "primary_metabolism"
    assert by_id["BGC032"]["Downgrade"] == ""


def test_af_axis_uses_af_score():
    triage, bgcs = _fixture()
    rows = axis_lead_board_rows(triage, bgcs, "af")
    # clean rows only: BGC007 (39.3) > BGC032 (35.3)
    clean = [r for r in rows if not r["Downgrade"]]
    assert clean[0]["BGC_ID"] == "BGC007"
    assert clean[0]["Score"] == 39.3


def test_headers_present():
    assert AXIS_LEAD_BOARD_HEADERS[0] == "Board_rank"
    assert "Downgrade" in AXIS_LEAD_BOARD_HEADERS and "Score" in AXIS_LEAD_BOARD_HEADERS


# BC2-408 (rebased): mobile_element_flag is the third corrected_rank-gating exclusion signal
# alongside standing_rule_flag/primary_metabolism_flag (scoring.py's own three-flag gate). Before
# this fix, a mobile-dominant/uncorroborated row's Downgrade cell was silently blank and it sorted
# among genuine clean leads by score alone -- exactly the class of bug the AUDIT_378 sweep fixed in
# card_verdicts.py/boundary_audit.py/domain_level.py/cli.py/serialize.py, but missed here (see
# af_dossier.py's own docstring, which names this exact omission).

def test_mobile_element_flag_row_is_downgraded_and_sunk():
    triage, bgcs = _fixture()
    # A mobile-dominant ICE region: high raw AB score, but flagged and correctly excluded from
    # corrected_rank by scoring.py -- must be visibly marked and sunk here too, same as the other
    # two exclusion reasons already covered above.
    triage.append(_T("BGC200", 70.0, 15.0, mobile="conjugation,integrase", crank=None))
    bgcs["BGC200"] = _B("BGC200", "NODE_44", ["lanthipeptide-class-v"])
    rows = axis_lead_board_rows(triage, bgcs, "ab")
    by_id = {r["BGC_ID"]: r for r in rows}
    assert by_id["BGC200"]["Downgrade"] == "conjugation,integrase"
    # Sunk to the bottom despite the highest raw AB score in the fixture (70.0) -- the whole
    # point of the Downgrade-first sort key.
    bottom_ids = {rows[-1]["BGC_ID"], rows[-2]["BGC_ID"], rows[-3]["BGC_ID"]}
    assert "BGC200" in bottom_ids
    assert by_id["BGC200"]["Downgrade"] != ""
    # A genuine clean lead (no flag at all) still reads an empty Downgrade cell, unaffected.
    assert by_id["BGC032"]["Downgrade"] == ""
