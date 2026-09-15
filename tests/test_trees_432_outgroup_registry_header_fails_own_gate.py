"""TREES_432 — outgroup_registry.get_16s wrote a header carrying the accession twice
(`>Gordonia_Gordonia_bronchialis_DSM_43247_NR_074529_1_NR_119065.1  [outgroup for ...]`), which
phylo_place's own admission gate rejects as MULTIPLE_FASTA_DEFINITIONS_OR_ACCESSIONS, so no
per-genus panel whose registry row names an accession could be built. Now: an accession named in
the registry row is fetched directly (the ruling wins over the name-based pick), the header is
`>{acc} {DB title} [outgroup for {ingroup}]` with the accession once, a stale cache file is
re-validated against the same gate, and a genus mismatch between row and record is refused.
"""
import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.phylo_place import screen_reference_definitions  # noqa: E402

OFFICIAL = ROOT.parents[2] / "OFFICIAL_DATA" / "OUTGROUP_REGISTRY.tsv"
HEADER = "tree_scope\tingroup_taxon\tfamily\toutgroup_genus\toutgroup_species_strain\tassembly_accession\tstatus\trationale\n"
ROWS = [
    "genus\tSaccharopolyspora\tPseudonocardiaceae\tPseudonocardia\tPseudonocardia thermophila ATCC 19285 (NR_118886.1)\t16S_local_RefSeq\tLOCKED\truled",
    "genus\tStreptomyces\tStreptomycetaceae\tGordonia\tGordonia bronchialis DSM 43247 NR_074529.1\t16S_local_RefSeq\tLOCKED\truled",
    "genus\tKribbella\tNocardioidaceae\tNocardioides\tNocardioides albus\tGCF_014191915.1\tLOCKED\tno accession in row",
    "genus\tBadgenus\tX\tActinopolyspora\tActinopolyspora halophila (NR_179169.1)\t16S_local_RefSeq\tLOCKED\tgenus mismatch fixture",
]
FAKE_DB = {
    "NR_118886": ("NR_118886.1", "Pseudonocardia thermophila strain ATCC 19285 16S ribosomal RNA, partial sequence"),
    "NR_074529": ("NR_074529.1", "Gordonia bronchialis DSM 43247 16S ribosomal RNA, partial sequence"),
    # Scores higher than NR_074529.1 under _pick_accession (NR_ +3, strain token "43247" +5, "type strain" +2,
    # longer title tie-break), so the name-based pick prefers it and the ruled accession must still win.
    "NR_119065": ("NR_119065.1", "Gordonia bronchialis strain DSM 43247 = NCTC 10667 type strain 16S ribosomal RNA, partial sequence"),
    "NR_000009": ("NR_000009.1", "Nocardioides albus strain KCTC 9186 16S ribosomal RNA, partial sequence"),
    "NR_179169": ("NR_179169.1", "Phytoactinopolyspora halophila strain YIM 93513 16S ribosomal RNA, partial sequence"),
}
SEQ = "ACGT" * 400


def _load(tmp_path, monkeypatch, rows=ROWS, db=FAKE_DB):
    reg = tmp_path / "registry.tsv"
    reg.write_text(HEADER + "\n".join(rows) + "\n")
    monkeypatch.setenv("OUTGROUP_REGISTRY", str(reg))
    spec = importlib.util.spec_from_file_location("outgroup_registry_trees432", ROOT / "tools" / "outgroup_registry.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.CACHE = str(tmp_path / "cache")
    monkeypatch.setattr(mod, "_blastdbcmd", lambda: "/fake/blastdbcmd", raising=False)
    fetched = []

    def fetch(bdc, acc):
        fetched.append(acc)
        hit = db.get(acc.split(".")[0])
        return (hit[0], hit[1], SEQ) if hit else None
    monkeypatch.setattr(mod, "_fetch_entry", fetch, raising=False)
    monkeypatch.setattr(mod, "_title_index", lambda: {v[0]: v[1] for v in db.values()}, raising=False)
    monkeypatch.setattr(mod, "_fetched", fetched, raising=False)
    return mod


def _header(path):
    return Path(path).read_text().splitlines()[0]


def test_split_ruled_accession():
    spec = importlib.util.spec_from_file_location("og_split_432", ROOT / "tools" / "outgroup_registry.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    assert mod.split_ruled_accession("Pseudonocardia thermophila ATCC 19285 (NR_118886.1)") == \
        ("Pseudonocardia thermophila ATCC 19285", "NR_118886.1")
    assert mod.split_ruled_accession("Gordonia bronchialis DSM 43247 NR_074529.1") == \
        ("Gordonia bronchialis DSM 43247", "NR_074529.1")
    assert mod.split_ruled_accession("Nocardioides albus") == ("Nocardioides albus", "")


def test_accession_bearing_row_writes_single_accession_header_that_passes_the_gate(tmp_path, monkeypatch):
    og = _load(tmp_path, monkeypatch)
    fa = og.get_16s("Saccharopolyspora", quiet=True)
    assert os.path.basename(fa) == "Pseudonocardia_Pseudonocardia_thermophila_ATCC_19285.fasta"  # no accession in the name
    assert _header(fa) == (">NR_118886.1 Pseudonocardia thermophila strain ATCC 19285 16S ribosomal RNA, "
                           "partial sequence [outgroup for Saccharopolyspora]")
    assert screen_reference_definitions(fa) == []
    assert og.header_admissible(fa) == (True, "")


def test_ruled_accession_wins_over_the_name_based_pick(tmp_path, monkeypatch):
    og = _load(tmp_path, monkeypatch)
    # the name-based pick prefers the richer NCTC 10667 title (NR_119065.1); the ruling is NR_074529.1
    pick = og._pick_accession(og._title_index(), "Gordonia", "Gordonia bronchialis DSM 43247")
    assert pick[1] == "NR_119065.1"
    fa = og.get_16s("Streptomyces", quiet=True)
    assert og._fetched == ["NR_074529.1"]
    assert _header(fa).startswith(">NR_074529.1 Gordonia bronchialis DSM 43247 ")
    assert _header(fa).endswith("[outgroup for Streptomyces]")
    assert screen_reference_definitions(fa) == []


def test_row_without_accession_still_uses_the_name_based_pick(tmp_path, monkeypatch):
    og = _load(tmp_path, monkeypatch)
    fa = og.get_16s("Kribbella", quiet=True)
    assert og._fetched == ["NR_000009.1"]
    assert screen_reference_definitions(fa) == []


def test_genus_mismatch_between_row_and_record_is_refused(tmp_path, monkeypatch):
    og = _load(tmp_path, monkeypatch)
    with pytest.raises(og.RegistryAuthorityError, match="OUTGROUP_ACCESSION_GENUS_MISMATCH"):
        og.get_16s("Badgenus", quiet=True)
    assert not list((tmp_path / "cache" / "16S").glob("*.fasta"))


def test_stale_two_accession_cache_file_is_rewritten_not_served(tmp_path, monkeypatch):
    og = _load(tmp_path, monkeypatch)
    cache = tmp_path / "cache" / "16S"; cache.mkdir(parents=True)
    stale = cache / "Gordonia_Gordonia_bronchialis_DSM_43247.fasta"
    stale.write_text(">Gordonia_Gordonia_bronchialis_DSM_43247_NR_074529_1_NR_119065.1  [outgroup for Streptomyces; "
                     "Gordonia bronchialis strain NCTC 10667]\n" + SEQ + "\n")
    assert screen_reference_definitions(str(stale)) and og.header_admissible(str(stale))[0] is False
    fa = og.get_16s("Streptomyces", quiet=True)
    assert Path(fa) == stale
    assert _header(fa).startswith(">NR_074529.1 ")
    assert screen_reference_definitions(fa) == []


def test_gate_still_rejects_genuinely_multi_record_deflines(tmp_path):
    bad = tmp_path / "bad.fasta"
    bad.write_text(">NR_109504.1 Amycolatopsis dongchuanensis strain YIM 75904 16S ribosomal RNA, partial sequence "
                   ">NR_118259.1 Amycolatopsis dongchuanensis strain YIM 75904 16S ribosomal RNA, partial sequence\n"
                   + SEQ + "\n>Gordonia_bronchialis_DSM_43247_NR_074529_1_NR_119065.1  [outgroup for Streptomyces]\n"
                   + SEQ + "\n>NR_074529.1 Gordonia bronchialis DSM 43247 16S ribosomal RNA [outgroup for Streptomyces]\n"
                   + SEQ + "\n")
    rejected = screen_reference_definitions(str(bad))
    assert [r for _h, r in rejected] == ["MULTIPLE_FASTA_DEFINITIONS_OR_ACCESSIONS"] * 2
    assert all("NR_074529.1 Gordonia" not in h for h, _r in rejected)


def _official_rows():
    if not OFFICIAL.is_file():
        return []
    seen, out = set(), []
    for ln in OFFICIAL.read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("#") or ln.startswith("tree_scope"):
            continue
        c = ln.split("\t")
        key = (c[0], c[1])
        if key not in seen:
            seen.add(key); out.append(ln)
    return out


@pytest.mark.skipif(not OFFICIAL.is_file(), reason="OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv not on this machine")
@pytest.mark.parametrize("row", _official_rows(), ids=lambda r: "/".join(r.split("\t")[:2]))
def test_every_official_registry_row_yields_an_admissible_header(tmp_path, monkeypatch, row):
    c = row.split("\t")
    scope, taxon, og_genus, species_strain = c[0], c[1], c[3], c[4]
    spec = importlib.util.spec_from_file_location("og_official_432", ROOT / "tools" / "outgroup_registry.py")
    probe = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)
    name, acc = probe.split_ruled_accession(species_strain)
    acc = acc or "NR_000001.1"
    db = {acc.split(".")[0]: (acc, f"{name} 16S ribosomal RNA, partial sequence")}
    og = _load(tmp_path, monkeypatch, rows=[row], db=db)
    fa = og.get_16s(taxon, scope=scope, quiet=True)
    assert screen_reference_definitions(fa) == [], _header(fa)
    assert _header(fa).count(">") == 1 and _header(fa).count(acc) == 1
    assert "outgroup" in _header(fa)
