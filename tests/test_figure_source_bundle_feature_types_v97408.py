"""v9.7.408 — the figure source bundle reads the modules table by feature_type (Codex hostile audit Q2/Q5).

Fails-before on sealed .407: the `antismash` tool-name token from aSModule rows was counted as a domain,
the `UNMAPPED` pseudo-id became an extra BGC, and ACTIVE_SITE_PAIRING rows were invisible so active-site
evidence read STRUCTURALLY_UNAVAILABLE while typed rows sat in the same file."""
from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

from mamey.interactive_figures.figure_source_bundle import build_source_bundle


def _csv(fields, rows):
    buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=fields); w.writeheader(); w.writerows(rows); return buf.getvalue()


def _package(path: Path, strain: str) -> None:
    inventory = _csv(["BGC_ID", "Boundary", "Length_kb", "Products", "KCB_top", "KCB_score", "TTA_tier", "Resistance_tier", "claim_ceiling", "product_claim_ceiling"],
                     [{"BGC_ID": "BGC001", "Boundary": "Interior", "Length_kb": "10", "Products": "PKS", "KCB_top": "", "KCB_score": ""}])
    cds = _csv(["bgc_id", "contig", "locus_tag", "start", "end", "length_aa", "gene_functions"],
               [{"bgc_id": "BGC001", "contig": "c1", "locus_tag": "g1", "start": "1", "end": "900", "length_aa": "300", "gene_functions": "biosynthetic"}])
    mods = _csv(["bgc_id", "mapping_status", "feature_type", "domain", "substrate_consensus"], [
        {"bgc_id": "BGC001", "mapping_status": "MAPPED", "feature_type": "aSDomain", "domain": "PKS_KS", "substrate_consensus": ""},
        {"bgc_id": "BGC001", "mapping_status": "MAPPED", "feature_type": "aSDomain", "domain": "PKS_AT", "substrate_consensus": "mal"},
        {"bgc_id": "BGC001", "mapping_status": "MAPPED", "feature_type": "aSModule", "domain": "antismash", "substrate_consensus": ""},
        {"bgc_id": "BGC001", "mapping_status": "MAPPED", "feature_type": "ACTIVE_SITE_PAIRING", "domain": "nrpspksdomains_g1_PKS_KS.1", "substrate_consensus": ""},
        {"bgc_id": "BGC001", "mapping_status": "MAPPED", "feature_type": "NRPS_PKS_CONSENSUS", "domain": "nrpspksdomains_g1_PKS_AT.1", "substrate_consensus": ""},
        {"bgc_id": "UNMAPPED", "mapping_status": "UNMAPPED_NO_COORDINATES", "feature_type": "aSDomain", "domain": "PCP", "substrate_consensus": ""},
    ])
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(f"package/{strain}_2_inventory.csv", inventory)
        z.writestr(f"package/{strain}_cds_table.csv", cds)
        z.writestr(f"package/{strain}_3_antismash_modules.csv", mods)


def _widget(package):
    return {"meta": {"sourceRelease": "synthetic"}, "strains": {"S1": {
        "governance": "GOVERNED", "package": str(package), "bgcRows": 1, "uniquePhysicalGenes": 1, "machineryGenes": 1,
        "classes": {"PKS": {"total": 1, "edge": 0, "full": 1, "interior": 0}},
        "machinery": {"Biosynthetic core": [300]},
        "hostContext": {"group": "BEE", "source": "test", "hostSpecies": "bee", "location": "x"}}}}


def _read(outdir: Path, name: str):
    return list(csv.DictReader(open(outdir / name, encoding="utf-8")))


def test_domains_are_aSDomain_rows_only_and_pseudo_id_is_not_a_bgc(tmp_path):
    pkg = tmp_path / "S1_pkg.zip"; _package(pkg, "S1")
    widget = tmp_path / "w.json"; widget.write_text(json.dumps(_widget(pkg)), encoding="utf-8")
    out = tmp_path / "bundle"; build_source_bundle(widget, tmp_path, out)
    mod_path = next(out.rglob("MODULE_SUBSTRATE_BGC_SUMMARY.csv")); dom_path = next(out.rglob("MODULE_DOMAIN_CALLS.csv"))
    mods = _read(mod_path.parent, mod_path.name); doms = _read(dom_path.parent, dom_path.name)
    assert [r["bgc_id"] for r in mods] == ["BGC001"], "UNMAPPED is a state, never a BGC row"
    row = mods[0]
    assert row["distinct_domains"] == "2", row
    assert row["asdomain_rows"] == "2" and row["asmodule_rows"] == "1" and row["active_site_pairing_rows"] == "1" and row["consensus_rows"] == "1"
    assert "antismash" not in {r["domain"] for r in doms}, "a tool-name marker is not a domain"


def test_active_site_state_comes_from_typed_rows_when_deep_data_is_absent(tmp_path):
    pkg = tmp_path / "S1_pkg.zip"; _package(pkg, "S1")
    widget = tmp_path / "w.json"; widget.write_text(json.dumps(_widget(pkg)), encoding="utf-8")
    out = tmp_path / "bundle"; build_source_bundle(widget, tmp_path, out)
    ext_file = next(out.rglob("BGC_EXTENDED_EVIDENCE.csv"))
    ext = _read(ext_file.parent, ext_file.name)
    row = next(r for r in ext if r["bgc_id"] == "BGC001")
    assert row["active_site_rows"] == "1"
    assert row["active_site_state"] == "POPULATED"
    assert row["active_site_source"] == "antismash_modules:ACTIVE_SITE_PAIRING"
