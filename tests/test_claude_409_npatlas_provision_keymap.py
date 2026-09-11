"""TESTS_CLAUDE_409_npatlas_provision_keymap.py -- the NP Atlas provisioner/consumer key-map fix.

Bug closed
----------
`tools/npatlas_provision.py` -> `mamey/npatlas_provision.py::provision` wrote each NP Atlas v2024_09
record VERBATIM. The raw schema keys differ from what `mamey/npatlas_resolver.py` reads:
  raw `original_name`               -> resolver reads `name`
  raw `origin_reference`            -> resolver reads `reference`
  raw `npclassifier.class_results`  -> resolver reads `npclassifier.class`
so a "successful" provision built an EMPTY resolver index (every `c.get("name")` was None -> every
record skipped) and B6_Compound_Reference stayed empty. The fix adds a deterministic, offline
`normalize_record` pass (and a synthetic scalar `phylum` derived from the nested
`origin_organism.taxon.ancestors[]`, so the actino split is a plain declarative clause), wired into
`provision(..., normalize=True)` and the `--normalize` / `--phylum` CLI flags.

Fail-before / pass-after
------------------------
On the pristine .408 bundle: `normalize_record` / `_taxon_phylum` do not exist, `provision` has no
`normalize` kwarg, and the CLI has no `--normalize` / `--phylum` flags -- so every "pass-after" test
here errors or fails. After the patch they pass. The verbatim-stays-empty test documents the bug and
holds in both states (verbatim behaviour is deliberately unchanged).

Synthetic fixtures only: fake NPAIDs/compound names, tmp_path-only paths, no real strain identifiers,
no absolute local paths in assertions -- mirrors tests/test_npatlas_provision_v97405.py.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
PY = sys.executable

from mamey import npatlas_provision as prov
from mamey import npatlas_resolver as resolver


# ---------------------------------------------------------------------------
# fixtures -- RAW NP Atlas v2024_09 schema (the keys the official download uses)
# ---------------------------------------------------------------------------
def _raw_actino_record(npaid: str, name: str, genus: str, phylum: str = "Actinobacteria") -> dict:
    return {
        "npaid": npaid,
        "original_name": name,          # raw key -- resolver reads `name`
        "mol_formula": "C35H53NO9",
        "mol_weight": 631.80,
        "exact_mass": 631.3720,
        "m_plus_h": 632.3793,
        "m_plus_na": 654.3612,
        "inchikey": "AAAAAAAAAAAAAA-BBBBBBBBBB-C",
        "inchi": "InChI=1S/fake",
        "smiles": "CCO",
        "synonyms": [],
        "npclassifier": {               # raw *_results keys -- resolver reads class/pathway/...
            "class_results": ["Macrolide lactams"],
            "pathway_results": ["Polyketides"],
            "superclass_results": ["Macrolides"],
            "isglycoside": False,
        },
        "origin_reference": {           # raw key -- resolver reads `reference`
            "doi": "10.7164/antibiotics.51.123",
            "pmid": 12345678,
            "year": 1998,
            "journal": "J. Fake Antibiotics",
            "title": "A synthetic actino metabolite",
        },
        "origin_organism": {
            "genus": genus,
            "species": "fictus",
            "type": "Bacterium",
            "taxon": {
                "name": genus,
                "rank": "genus",
                "ancestors": [
                    {"name": "Bacteria", "rank": "domain"},
                    {"name": phylum, "rank": "phylum"},   # phylum lives in the ANCESTOR LIST
                    {"name": "Actinomycetia", "rank": "class"},
                ],
            },
        },
    }


def _raw_nonactino_record(npaid: str, name: str) -> dict:
    r = _raw_actino_record(npaid, name, "Pseudomonas", phylum="Proteobacteria")
    return r


def _write_raw_source(tmp_path: Path, records: list[dict]) -> Path:
    src = tmp_path / "npatlas_raw.json"           # bare top-level array = official download shape
    src.write_text(json.dumps(records), encoding="utf-8")
    return src


def _load_resolver_index(monkeypatch, npatlas_dir: Path) -> dict:
    """Point the resolver at `npatlas_dir` and return a freshly-loaded index (lru caches cleared)."""
    monkeypatch.setenv(resolver._NPATLAS_ENV_VAR, str(npatlas_dir))
    resolver._load_index.cache_clear()
    resolver._class_counts.cache_clear()
    return resolver._load_index()


# ---------------------------------------------------------------------------
# unit: the key-map itself
# ---------------------------------------------------------------------------
def test_taxon_phylum_reads_nested_ancestor_list():
    rec = _raw_actino_record("NPA-SYN-1", "synthomycin A", "Synthomyces")
    assert prov._taxon_phylum(rec) == "Actinobacteria"
    assert prov._taxon_phylum(_raw_nonactino_record("NPA-SYN-2", "pseudol")) == "Proteobacteria"
    assert prov._taxon_phylum({}) is None
    assert prov._taxon_phylum({"origin_organism": {"taxon": {"rank": "phylum", "name": "Actinomycetota"}}}) == "Actinomycetota"


def test_normalize_record_maps_raw_2024_09_keys():
    out = prov.normalize_record(_raw_actino_record("NPA-SYN-1", "Synthomycin A", "Synthomyces"))
    # the three keys the resolver actually reads
    assert out["name"] == "Synthomycin A"
    assert out["reference"]["doi"] == "10.7164/antibiotics.51.123"
    assert out["reference"]["pmid"] == 12345678
    assert out["reference"]["year"] == 1998
    assert out["npclassifier"]["class"] == ["Macrolide lactams"]
    assert out["npclassifier"]["pathway"] == ["Polyketides"]
    assert out["npclassifier"]["is_glycoside"] is False
    # scalar molecule fields carried through, plus the synthetic phylum
    assert out["mol_formula"] == "C35H53NO9"
    assert out["exact_mass"] == 631.3720
    assert out["npaid"] == "NPA-SYN-1"
    assert out["phylum"] == "Actinobacteria"
    # raw keys are gone from the normalized record
    assert "original_name" not in out
    assert "origin_reference" not in out


def test_normalize_record_is_idempotent():
    once = prov.normalize_record(_raw_actino_record("NPA-SYN-1", "synthomycin A", "Synthomyces"))
    twice = prov.normalize_record(once)
    assert twice["name"] == "synthomycin A"
    assert twice["npclassifier"]["class"] == ["Macrolide lactams"]
    assert twice["reference"]["doi"] == "10.7164/antibiotics.51.123"
    assert twice["phylum"] == "Actinobacteria"


# ---------------------------------------------------------------------------
# the bug: a VERBATIM provision builds an EMPTY resolver index (documents the defect)
# ---------------------------------------------------------------------------
def test_verbatim_provision_yields_empty_resolver_index(tmp_path, monkeypatch):
    src = _write_raw_source(tmp_path, [
        _raw_actino_record("NPA-SYN-1", "synthomycin A", "Synthomyces"),
        _raw_actino_record("NPA-SYN-2", "synthomycin B", "Synthomyces"),
    ])
    npdir = tmp_path / "np_verbatim"
    out = npdir / "all_actinobacteria_npatlas_ref.json"
    receipt = prov.provision(str(src), str(out), [], normalize=False)
    assert receipt.included_count == 2            # records WERE written
    idx = _load_resolver_index(monkeypatch, npdir)
    assert idx == {}                              # ...but the resolver cannot read them (the bug)
    assert resolver.npatlas_available() is False


# ---------------------------------------------------------------------------
# the fix: a NORMALIZED provision builds a POPULATED resolver index
# ---------------------------------------------------------------------------
def test_normalized_provision_populates_resolver_index(tmp_path, monkeypatch):
    src = _write_raw_source(tmp_path, [
        _raw_actino_record("NPA-SYN-1", "synthomycin A", "Synthomyces"),
        _raw_actino_record("NPA-SYN-2", "synthomycin B", "Synthomyces"),
    ])
    npdir = tmp_path / "np_normalized"
    out = npdir / "all_actinobacteria_npatlas_ref.json"
    receipt = prov.provision(str(src), str(out), [], normalize=True)
    assert receipt.included_count == 2
    assert receipt.normalized is True

    idx = _load_resolver_index(monkeypatch, npdir)
    assert len(idx) == 2                          # POPULATED (was 0 verbatim)
    assert resolver.npatlas_available() is True

    # a real B6-style resolve now returns molecule-level chemistry
    row = resolver.compound_reference_row("STRAIN-X", "BGC001",
                                          "BGC0000001.1 | synthomycin A | knowncluster", 9999)
    assert row is not None
    assert row["resolved"] == "YES"
    assert row["mol_formula"] == "C35H53NO9"
    assert row["npclassifier_class"] == "Macrolide lactams"
    assert row["primary_doi"] == "10.7164/antibiotics.51.123"
    # class-frequency grounding also works off the normalized npclassifier.class list
    assert "Macrolide lactams" in resolver.class_in_actinobacteria_sentence("Macrolide lactams")


def test_actino_split_via_phylum_clause(tmp_path, monkeypatch):
    """`--normalize` + an `in` clause on the synthetic `phylum` keeps only actinobacterial records."""
    src = _write_raw_source(tmp_path, [
        _raw_actino_record("NPA-SYN-1", "synthomycin A", "Synthomyces"),
        _raw_actino_record("NPA-SYN-2", "synthomycetota X", "Synthospora", phylum="Actinomycetota"),
        _raw_nonactino_record("NPA-SYN-3", "pseudomonin"),
    ])
    npdir = tmp_path / "np_actino"
    out = npdir / "all_actinobacteria_npatlas_ref.json"
    clause = prov.clause_from_dict({"field": "phylum", "op": "in",
                                    "value": ["Actinobacteria", "Actinomycetota"]})
    receipt = prov.provision(str(src), str(out), [clause], normalize=True)
    assert receipt.included_count == 2            # the two actino records; Proteobacteria excluded
    assert receipt.excluded_count == 1
    idx = _load_resolver_index(monkeypatch, npdir)
    assert set(idx.keys()) == {"synthomycin a", "synthomycetota x"}


# ---------------------------------------------------------------------------
# CLI front door: --normalize / --phylum
# ---------------------------------------------------------------------------
def test_cli_normalize_and_phylum_flags(tmp_path, monkeypatch):
    src = _write_raw_source(tmp_path, [
        _raw_actino_record("NPA-SYN-1", "synthomycin A", "Synthomyces"),
        _raw_nonactino_record("NPA-SYN-3", "pseudomonin"),
    ])
    npdir = tmp_path / "np_cli"
    out = npdir / "all_actinobacteria_npatlas_ref.json"
    proc = subprocess.run(
        [PY, str(TOOLS / "npatlas_provision.py"), "provision",
         "--source", str(src), "--out", str(out),
         "--dataset-version", "v2024_09",
         "--normalize", "--phylum", "Actinobacteria", "--phylum", "Actinomycetota"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    receipt = json.loads(proc.stdout)
    assert receipt["normalized"] is True
    assert receipt["included_count"] == 1         # only the actino record survives the phylum clause

    idx = _load_resolver_index(monkeypatch, npdir)
    assert len(idx) == 1
    assert "synthomycin a" in idx
