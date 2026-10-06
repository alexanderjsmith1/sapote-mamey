"""Mode B contract current50 v2 (3 Oct): fifty sections, GECCO in §22, the contigs rescued into the BGC in
§26, literature with relevance in §48-§49, and the data evidence table as the very last section, §50."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mamey import modeb_template_emitter as emitter  # noqa: E402
from mamey.modeb_current50_v2 import V2_PATH, load_contract, v2_findings  # noqa: E402
from mamey.modeb_full50_contract import ROW  # noqa: E402
from mamey.modeb_structure_gate import lint_card  # noqa: E402


def test_contract_has_fifty_sections_in_order_with_the_new_ones():
    c = load_contract("current50_v2")
    assert c["schema_version"] == "modeb_current50_v2" and c["section_count"] == 50
    assert [s["number"] for s in c["sections"]] == list(range(1, 51))
    t = {s["number"]: s["title"] for s in c["sections"]}
    assert t[22].startswith("GECCO") and t[26] == "Contigs rescued into the BGC"
    assert t[48].startswith("Biosynthetic gene") and t[49].startswith("Genus") and t[50] == "Data evidence table"
    assert "RiPP" in t[21] and "OSMAC" in t[23]


def test_v1_and_the_48_profile_are_untouched_and_full48_stays_the_default():
    assert load_contract(None) is None and load_contract("full48") is None
    v1 = json.loads((V2_PATH.parent / "modeb_full50_contract.json").read_text())
    assert v1["schema_version"] == "modeb_current50_v1"


def test_markdown_copy_parses_with_the_consumer_regex():
    rows = ROW.findall((ROOT / "docs" / "MODEB_CURRENT50_V2_CONTRACT.md").read_text())
    assert [int(n) for n, _ in rows] == list(range(1, 51))


def test_emitted_template_has_fifty_headings_and_passes_the_structure_gate(tmp_path):
    c = load_contract("current50_v2")
    t = emitter.emit_card_template(tmp_path, "BGC001", contract=c)
    heads = [int(n) for n in re.findall(r"^## §(\d+) ", t, re.M)]
    assert heads == list(range(1, 51))
    assert "§1–§50" in t and "§1–§48 in order" not in t
    assert not [f for f in lint_card(t, contract=c) if f["severity"] == "ERROR"]
    s50 = t.split("## §50 ")[1]
    assert "Gene table" in s50 and "Gene table" not in t.split("## §4 ")[1].split("## §5 ")[0]


def test_fresh_template_is_not_a_finished_card(tmp_path):
    t = emitter.emit_card_template(tmp_path, "BGC001", contract=load_contract("current50_v2"))
    codes = {f["code"] for f in v2_findings(t)}
    assert {"V2_DEFERRAL", "V2_LITERATURE_NO_CITATION"} <= codes


def _card(lit48="Smith et al. 2020, doi:10.1093/nar/gkaf334. Relevance: the cyclase family of ctg1_2.",
          lit49="PMID 12345678. Relevant to the genus context of this locus.", last=50, table=True, extra=""):
    secs = []
    for n in range(1, 51):
        body = {48: lit48, 49: lit49}.get(n, f"Finding for section {n}.")
        if n == 50 and table:
            body = "| gene | GECCO p |\n|---|---|\n| ctg1_2 | 0.91 |"
        secs.append((n, f"## §{n} Title {n}\n\n{body}{extra if n == 7 else ''}\n"))
    if last != 50:
        secs.append((last, f"## §{last} Appendix\n\ntext\n"))
    return "\n".join(s for _, s in secs)


def test_a_complete_card_passes_the_v2_checks():
    assert v2_findings(_card()) == []


def test_literature_needs_a_citation_and_its_relevance():
    codes = {f["code"] for f in v2_findings(_card(lit48="Some papers discuss cyclases. Relevance: high."))}
    assert "V2_LITERATURE_NO_CITATION" in codes
    codes = {f["code"] for f in v2_findings(_card(lit49="PMID 12345678."))}
    assert "V2_LITERATURE_NO_RELEVANCE" in codes


def test_the_evidence_table_must_be_last_and_be_a_table():
    assert "V2_EVIDENCE_TABLE_NOT_LAST" in {f["code"] for f in v2_findings(_card(last=12))}
    assert "V2_EVIDENCE_TABLE_MISSING" in {f["code"] for f in v2_findings(_card(table=False))}


def test_deferrals_are_refused():
    for text in (" Regulators were not evaluated.", " TODO add BLASTp.", " <!-- Author: fill -->"):
        assert "V2_DEFERRAL" in {f["code"] for f in v2_findings(_card(extra=text))}


def test_cli_offers_the_contract_on_emit_and_verify():
    for cmd in ("emit-modeb-template", "verify-modeb"):
        out = subprocess.run([sys.executable, str(ROOT / "mamey_run.py"), cmd, "--help"], capture_output=True,
                             text=True, cwd=ROOT).stdout
        assert "current50_v2" in out


# r5, from the first card authored on this contract: the emitter left the contract sha and full contig name out
# of the header, the §4 BLASTp-table warning fired although v2 keeps that table in §50, the banner said §1-§48,
# and PHANTOM_LOCUS refused a gene the rescue table found outside every region.

def test_v2_header_carries_full_identity_and_contract_sha():
    from mamey.modeb_current50_v2 import contract_sha256, header_line
    import hashlib
    assert contract_sha256() == hashlib.sha256(V2_PATH.read_bytes()).hexdigest()
    line = header_line("AS-XXX", "NODE_7_length_9000_cov_12.5", "region001", "BGC001")
    assert "canonical_identity: AS-XXX / NODE_7_length_9000_cov_12.5 / region001 / BGC001" in line
    assert f"contract_sha256: {contract_sha256()}" in line and "FINISHED_FULL50_CURRENT50_V2" in line
    head = emitter._header_block({"strain_id": "AS-XXX", "node": "NODE_7", "contig": "NODE_7_length_9000_cov_12.5",
                                  "region": "region001", "bgc_id": "BGC001"}, load_contract("current50_v2"))
    assert head.startswith(line) and "# Mode B — AS-XXX / NODE_7_length_9000_cov_12.5 / region001 / BGC001" in head
    old = emitter._header_block({"strain_id": "AS-XXX", "node": "NODE_7", "bgc_id": "BGC001"}, emitter.load_contract())
    assert "canonical_identity" not in old


def test_v2_blastp_table_is_read_in_section_50():
    from mamey.modeb_current50_v2 import blastp_table_findings
    with_id = _card().replace("| gene | GECCO p |\n|---|---|\n| ctg1_2 | 0.91 |",
                              "| gene | nr closest match | identity |\n|---|---|---|\n| ctg1_2 | WP_000001.1 | 81.0% |")
    assert blastp_table_findings(with_id) == []
    assert [f["code"] for f in blastp_table_findings(_card())] == ["EVIDENCE_GAP"]


def test_rescue_table_admits_same_strain_loci_for_existence_only(tmp_path):
    from mamey.modeb_current50_v2 import rescue_context_loci
    tsv = tmp_path / "gap_rescue.tsv"
    tsv.write_text("best_locus\tbest_region_identity\n"
                   "ctg9_6\tAS-XXX / NODE_9_length_8000_cov_50.1 (no antiSMASH region)\n"
                   "ctg4_2\tAS-YYY / NODE_4_length_5000_cov_20.0 / region001 / BGC002\n"
                   "\t\n", encoding="utf-8")
    md = "# Mode B — AS-XXX / NODE_7_length_9000_cov_12.5 / region001 / BGC001\n"
    loci, notes = rescue_context_loci(md, [tsv])
    assert loci == {"ctg9_6"} and len(notes) == 1 and "ctg4_2" in notes[0]


def test_verify_cli_offers_the_rescue_table_flag():
    out = subprocess.run([sys.executable, str(ROOT / "mamey_run.py"), "verify-modeb", "--help"], capture_output=True,
                         text=True, cwd=ROOT).stdout
    assert "--rescue-tsv" in out
