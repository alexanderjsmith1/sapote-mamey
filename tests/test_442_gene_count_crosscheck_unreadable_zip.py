"""An unreadable antiSMASH input ZIP must not look like missing region GBKs.

`write_gene_count_crosscheck` reads region GBKs from the input ZIP, its primary source; the sealed
package does not carry them. It used to swallow a ZIP read failure (`except Exception: pass`), so
every BGC then read "region GBK not found" and the omission check that reads this file was silently
disabled. The failure is now recorded and named; a readable ZIP produces the same output as before.
"""
import json
import zipfile

from mamey import degradation
from mamey.gene_by_gene import write_gene_count_crosscheck

GBK = """LOCUS       NODE_1  900 bp    DNA     linear   UNK
FEATURES             Location/Qualifiers
     CDS             1..300
                     /locus_tag="ctg1_1"
                     /product="hypothetical protein"
     CDS             400..900
                     /locus_tag="ctg1_2"
                     /product="ketosynthase"
ORIGIN
//
"""


def _package(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({
        "provenance": {"antismash_version": "8.0"},
        "bgcs": [{"bgc_id": "BGC001", "source_gbk": "NODE_1.region001.gbk", "edge_status": "Interior"}],
    }), encoding="utf-8")
    return pkg


def test_unreadable_zip_is_named_not_mistaken_for_missing_gbks(tmp_path):
    degradation.drain()
    pkg = _package(tmp_path)
    bad = tmp_path / "input.zip"
    bad.write_bytes(b"this is not a zip archive")
    out = write_gene_count_crosscheck(pkg, input_zip=bad)
    assert out["input_zip_unreadable"] == "BadZipFile"
    assert "input ZIP unreadable (BadZipFile)" in out["per_bgc"]["BGC001"]["note"]
    events = degradation.drain()
    assert [e["site"] for e in events] == ["gene_by_gene.write_gene_count_crosscheck.input_zip"]
    on_disk = json.loads((pkg / "gene_count_crosscheck.json").read_text(encoding="utf-8"))
    assert on_disk["input_zip_unreadable"] == "BadZipFile"


def test_readable_zip_output_is_unchanged(tmp_path):
    degradation.drain()
    pkg = _package(tmp_path)
    good = tmp_path / "input.zip"
    with zipfile.ZipFile(good, "w") as zf:
        zf.writestr("run/NODE_1.region001.gbk", GBK)
    out = write_gene_count_crosscheck(pkg, input_zip=good)
    assert "input_zip_unreadable" not in out
    assert out["per_bgc"]["BGC001"]["gbk_cds_count"] == 2
    assert degradation.drain() == []
