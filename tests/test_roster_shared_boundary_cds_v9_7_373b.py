"""v9.7.373b — Codex one-to-many roster-membership correction (roster HOLD fix).

A boundary CDS can legitimately belong to TWO adjacent/overlapping BGC region
records that share it. The prior last-write `home[lt] = bg` dict silently dropped
such a gene from the earlier BGC's per-BGC roster (Codex read-only census: 8
per-BGC undercounts across 6 packages, each losing exactly one shared gene).

These tests lock in the corrected behaviour:
  1. the shared locus appears in BOTH per-BGC rosters (no undercount);
  2. single-home genes are unaffected and still bind to their one BGC;
  3. the locus->home map carries the SET of homes for a shared gene while keeping
     a bare string for single-home genes (legacy-context back-compat);
  4. the LOCUS_BGC_MISMATCH guard does not falsely flag the shared gene under
     EITHER of its declared homes.
"""

from mamey.authored_verify import _bgc_context_from_package
from mamey.modeb_structure_gate import _locus_bgc_mismatch_findings

_HEADER = "bgc_id,rank,locus_tag,contig,bgc_start,bgc_end,cds_start,cds_end"
# ctg37_25 is the SHARED boundary CDS: it is a member row of BOTH BGC031 and BGC032.
_ROWS = [
    "BGC031,1,ctg37_24,ctg37,1000,9000,1000,1500",
    "BGC031,2,ctg37_25,ctg37,1000,9000,8500,9000",   # boundary CDS, also in BGC032
    "BGC032,1,ctg37_25,ctg37,8500,15000,8500,9000",  # same CDS, neighbouring region
    "BGC032,2,ctg37_26,ctg37,8500,15000,10000,10500",
]


def _make_pkg(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "AS-162_gene_by_gene_all_bgcs.csv").write_text(
        "\n".join([_HEADER, *_ROWS]) + "\n", encoding="utf-8")
    return pkg


def test_shared_cds_in_both_rosters(tmp_path):
    pkg = _make_pkg(tmp_path)
    ctx31 = _bgc_context_from_package(str(pkg), "BGC031")
    ctx32 = _bgc_context_from_package(str(pkg), "BGC032")
    # the shared gene must be present in BOTH rosters — no undercount either way
    assert ctx31["known_locus_tags"] == ["ctg37_24", "ctg37_25"]
    assert ctx32["known_locus_tags"] == ["ctg37_25", "ctg37_26"]


def test_locus_home_carries_set_for_shared_string_for_single(tmp_path):
    pkg = _make_pkg(tmp_path)
    ctx = _bgc_context_from_package(str(pkg), "BGC031")
    home = ctx["locus_home"]
    # shared gene -> set of both homes
    assert home["ctg37_25"] == {"BGC031", "BGC032"}
    # single-home gene -> bare string (legacy-context back-compat preserved)
    assert home["ctg37_24"] == "BGC031"
    assert home["ctg37_26"] == "BGC032"


def test_shared_cds_not_flagged_under_either_home(tmp_path):
    pkg = _make_pkg(tmp_path)
    ctx = _bgc_context_from_package(str(pkg), "BGC031")
    # cited under BGC031 -> fine (one of its homes)
    assert _locus_bgc_mismatch_findings("ctg37_25 sits in BGC031.", ctx) == []
    # cited under BGC032 -> also fine (its other declared home)
    assert _locus_bgc_mismatch_findings("ctg37_25 sits in BGC032.", ctx) == []


def test_genuine_misattribution_still_flagged(tmp_path):
    pkg = _make_pkg(tmp_path)
    ctx = _bgc_context_from_package(str(pkg), "BGC031")
    # ctg37_24 belongs ONLY to BGC031; citing it under BGC032 is a real mismatch
    findings = _locus_bgc_mismatch_findings("ctg37_24 sits in BGC032.", ctx)
    assert any(f["code"] == "LOCUS_BGC_MISMATCH" for f in findings)
