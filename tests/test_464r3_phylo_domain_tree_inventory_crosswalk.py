"""Domain-tree identity crosswalk: with an inventory, each tip is joined through its source region GBK
to the package inventory (BGC alias and full contig filled) or held with a reason; held tips are not
staged. Without an inventory every tip is UNVERIFIED_NO_INVENTORY and the summary is written under a
name Mode B never reads."""
import csv
import subprocess
import sys
from pathlib import Path

from mamey import domain_tree as DT

ROOT = Path(__file__).resolve().parents[1]
GOOD = "M" + "AKLVEGD" * 50
CONTIG = "NODE_{n}_length_90000_cov_12.5"


def _gbk_dir(tmp_path, names):
    d = tmp_path / "gbk"
    d.mkdir()
    for n in names:
        (d / n).write_text("")
    return d


def _inventory(tmp_path, rows):
    p = tmp_path / "inventory.csv"
    with p.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["BGC_ID", "Contig", "antiSMASH_Region", "Source_GBK"])
        w.writerows(rows)
    return p


def _dom(n, region="region001"):
    return {"strain": "TST-1", "node": f"NODE_{n}", "region": region, "locus_tag": f"ctg{n}_1",
            "domain_id": f"d{n}", "translation": GOOD + str(n) * 0 + "K" * n}


def test_crosswalk_verifies_and_holds_with_reasons(tmp_path):
    gdir = _gbk_dir(tmp_path, ["TST-1_NODE_1.region001.gbk", "TST-1_NODE_2.region001.gbk",
                               "TST-1_NODE_3.region001.gbk", "TST-1_NODE_4.region002.gbk"])
    inv = _inventory(tmp_path, [
        ["BGC001", CONTIG.format(n=1), "region001", "NODE_1.region001.gbk"],
        ["BGC002", CONTIG.format(n=9), "region001", "TST-1_NODE_2.region001.gbk"],
        ["BGC004", CONTIG.format(n=4), "region003", "NODE_4.region002.gbk"],
    ])
    out = {d["node"]: d for d in DT.crosswalk_identity(
        [_dom(1), _dom(2), _dom(3), _dom(4, "region002"), _dom(5)], inv, gdir)}
    assert out["NODE_1"]["identity_state"] == "VERIFIED"
    assert out["NODE_1"]["bgc_alias"] == "BGC001" and out["NODE_1"]["full_contig"] == CONTIG.format(n=1)
    assert out["NODE_2"]["identity_hold"].startswith("CONTIG_MISMATCH")
    assert out["NODE_3"]["identity_hold"].startswith("NO_INVENTORY_ROW")
    assert out["NODE_4"]["identity_hold"].startswith("REGION_MISMATCH")
    assert out["NODE_5"]["identity_hold"].startswith("SOURCE_GBK_NOT_UNIQUE")
    assert all(out[k]["identity_state"] == "HELD" and out[k]["bgc_alias"] == "" for k in ("NODE_2", "NODE_3", "NODE_4", "NODE_5"))


def test_conflicting_duplicate_inventory_key_is_held(tmp_path):
    gdir = _gbk_dir(tmp_path, ["TST-1_NODE_1.region001.gbk"])
    inv = _inventory(tmp_path, [["BGC001", CONTIG.format(n=1), "region001", "NODE_1.region001.gbk"],
                                ["BGC099", CONTIG.format(n=1), "region001", "NODE_1.region001.gbk"]])
    (d,) = DT.crosswalk_identity([_dom(1)], inv, gdir)
    assert d["identity_state"] == "HELD" and d["identity_hold"].startswith("DUPLICATE_INVENTORY_KEY")


def test_held_tips_are_ledgered_not_staged(tmp_path):
    doms = [dict(_dom(i), identity_state="VERIFIED", bgc_alias=f"BGC00{i}", full_contig=CONTIG.format(n=i))
            for i in range(1, 5)]
    doms.append(dict(_dom(5), identity_state="HELD", identity_hold="NO_INVENTORY_ROW: x"))
    staged = DT.stage_domains(doms, "PKS_KS", tmp_path / "out")
    assert staged["n_staged"] == 4 and staged["n_identity_held"] == 1
    assert "NODE_5" not in Path(staged["fasta"]).read_text()
    rows = {r["header"].split("__")[1]: r for r in csv.DictReader(open(staged["provenance"]), delimiter="\t")}
    assert rows["NODE_5"]["status"] == "IDENTITY_HELD" and rows["NODE_5"]["identity_hold"] == "NO_INVENTORY_ROW: x"
    assert rows["NODE_1"]["bgc_alias"] == "BGC001" and rows["NODE_1"]["identity_state"] == "VERIFIED"


def test_without_inventory_every_tip_is_marked_unverified(tmp_path):
    staged = DT.stage_domains([_dom(i) for i in range(1, 5)], "PKS_KS", tmp_path / "out")
    rows = list(csv.DictReader(open(staged["provenance"]), delimiter="\t"))
    assert {r["identity_state"] for r in rows} == {"UNVERIFIED_NO_INVENTORY"}


def test_unverified_summary_is_not_on_the_display_path(tmp_path):
    p = DT.write_summary([{"domain_class": "PKS_KS", "strain": "TST-1", "node": "NODE_1",
                           "identity_state": "UNVERIFIED_NO_INVENTORY"}], tmp_path, "PKS_KS",
                         identity_verified=False)
    assert p.endswith("PKS_KS_domain_tree_summary.UNVERIFIED.tsv")
    assert not list(tmp_path.glob("**/*_domain_tree_summary.tsv"))   # the Mode B reader's glob
    p2 = DT.write_summary([{"domain_class": "PKS_KS", "strain": "TST-1", "bgc_id": "BGC001",
                            "full_contig": CONTIG.format(n=1), "identity_state": "VERIFIED"}], tmp_path, "PKS_KS")
    row = next(csv.DictReader(open(p2), delimiter="\t"))
    assert row["bgc_id"] == "BGC001" and row["full_contig"] == CONTIG.format(n=1)


def test_cli_inventory_option_holds_unjoined_tips(tmp_path):
    gdir = tmp_path / "gbk"
    gdir.mkdir()
    feat = ('     aSDomain        1..1053\n'
            '                     /aSDomain="PKS_KS"\n'
            '                     /locus_tag="ctg{n}_1"\n'
            '                     /domain_id="d{n}"\n'
            '                     /translation="{seq}"\n')
    for n in range(1, 6):
        (gdir / f"TST-1_NODE_{n}.region001.gbk").write_text(
            "LOCUS       x\nFEATURES             Location/Qualifiers\n" + feat.format(n=n, seq=GOOD + "K" * n) + "ORIGIN\n//\n")
    inv = _inventory(tmp_path, [[f"BGC00{n}", CONTIG.format(n=n), "region001", f"NODE_{n}.region001.gbk"]
                                for n in range(1, 5)])
    spec = tmp_path / "spec.json"
    spec.write_text('{"domain_class": "PKS_KS", "gbk_dir": "%s", "outdir": "%s", "title": "t", '
                    '"approved_by": "tester", "allow_no_outgroup": true}' % (gdir, tmp_path / "out"))
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "build_domain_tree.py"), str(spec),
                        "--inventory", str(inv), "--skip-inference"], text=True, capture_output=True)
    assert r.returncode == 0, r.stderr
    assert "4 staged" in r.stdout and "1 identity-held" in r.stdout
    r2 = subprocess.run([sys.executable, str(ROOT / "tools" / "build_domain_tree.py"), str(spec), "--skip-inference"],
                        text=True, capture_output=True)
    assert "UNVERIFIED_NO_INVENTORY" in r2.stderr
