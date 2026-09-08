"""Tests for tools/phylo_autopilot.py — the upload -> routed/gated-tree front door.

Pure logic (classification, genus routing, BLAST-output parsing, reference-set assembly) is unit
tested with NO database and NO ML: the BLAST/DB calls are injected as fake runners. This is the
contract that matters — that a non-actinomycete 16S is flagged rather than forced onto an
actinomycete backbone, and that the tree-approval gate cannot be skipped.
"""
from __future__ import annotations

import importlib.util
import os
import types

import pytest

_TOOL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "tools", "phylo_autopilot.py")


def _load():
    spec = importlib.util.spec_from_file_location("_phylo_autopilot", _TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


AP = _load()


def _fake_run(stdout="", returncode=0, stderr=""):
    def run(cmd, capture_output=True, text=True):
        return types.SimpleNamespace(stdout=stdout, returncode=returncode, stderr=stderr)
    return run


# ---- genus routing (the heart of it) --------------------------------------------------------------
@pytest.mark.parametrize("genus,expect", [
    ("Streptomyces", "STREPTOMYCES"),
    ("Streptomyces sp.", "STREPTOMYCES"),
    ("Nocardia", "NOCARDIA"),
    ("Micromonospora", "RARE_ACTINO"),
    ("Pseudonocardia", "RARE_ACTINO"),
    ("Brachybacterium", "OFF_TARGET_ACTINO"),
    ("[Mycobacterium]", "OFF_TARGET_ACTINO"),
    ("Pseudescherichia", "FLAG_OTHER"),   # an enterobacterium: must NOT enter an actino tree
    ("Taibaiella", "FLAG_OTHER"),          # Bacteroidota contaminant
    ("Devosia", "FLAG_OTHER"),
])
def test_route_genus(genus, expect):
    assert AP.route_genus(genus) == expect


def test_flag_other_gets_no_reference_group():
    assigned = {"AS-61": {"genus": "Pseudescherichia", "pident": 99.0, "aln_len": "1400", "title": "x"},
                "AS-1": {"genus": "Micromonospora", "pident": 99.0, "aln_len": "1400", "title": "y"}}
    refs = AP.genera_for_reference(assigned)
    assert "rare_genera" in refs and "Micromonospora" in refs["rare_genera"]
    # the contaminant contributes to no group at all
    assert all("Pseudescherichia" not in v for v in refs.values())


# ---- input classification -------------------------------------------------------------------------
def _write(tmp_path, name, records):
    p = tmp_path / name
    p.write_text("".join(f">{h}\n{s}\n" for h, s in records))
    return str(p)


def test_classify_rrna_single(tmp_path):
    f = _write(tmp_path, "q.fasta", [("AS-1", "ACGT" * 350)])   # ~1.4 kb single nucleotide locus
    assert AP.classify_input(f) == "rrna"


def test_classify_rrna_multifasta(tmp_path):
    # many 16S in one file (one per strain) must stay 'rrna', not be mistaken for a genome
    f = _write(tmp_path, "many16s.fasta", [(f"AS-{i}", "ACGT" * 350) for i in range(20)])
    assert AP.classify_input(f) == "rrna"


def test_classify_genome(tmp_path):
    f = _write(tmp_path, "g.fna", [(f"contig{i}", "ACGT" * 5000) for i in range(8)])  # 20 kb contigs
    assert AP.classify_input(f) == "genome"


def test_classify_protein(tmp_path):
    f = _write(tmp_path, "p.faa", [("prot1", "MKLPQEFILW" * 20)])  # protein-only letters present
    assert AP.classify_input(f) == "protein"


# ---- BLAST parsing (best hit per query) -----------------------------------------------------------
def test_parse_blast_genus_keeps_best_hit():
    # genus-leading (real `blastn -outfmt 6 stitle`) AND accession-leading (blastdbcmd %t) both work
    txt = ("AS-1\tStreptomyces griseus strain X 16S\t99.5\t1400\n"
           "AS-1\tStreptomyces coelicolor Y\t98.0\t1400\n"
           "AS-2\tNR_3 Micromonospora echinospora Z\t97.2\t1350\n")
    got = AP.parse_blast_genus(txt)
    assert got["AS-1"]["genus"] == "Streptomyces" and got["AS-1"]["pident"] == 99.5
    assert got["AS-2"]["genus"] == "Micromonospora"   # leading NR_ accession skipped


# ---- reference auto-build (fake DB) ---------------------------------------------------------------
def test_build_reference_fasta_selects_by_genus(tmp_path):
    titles = ("A1\tMicromonospora echinospora ATCC 1\n"
              "A2\tMicromonospora aurantiaca ATCC 2\n"
              "A3\tStreptomyces griseus ATCC 3\n"
              "A4\tPseudonocardia thermophila ATCC 4\n")
    seqs = ">A1 Micromonospora\nACGT\n>A2 Micromonospora\nACGT\n"

    calls = {}

    def runner(cmd, capture_output=True, text=True):
        if "-entry" in cmd and cmd[cmd.index("-entry") + 1] == "all":
            return types.SimpleNamespace(stdout=titles, returncode=0, stderr="")
        if "-entry_batch" in cmd:
            calls["batch"] = open(cmd[cmd.index("-entry_batch") + 1]).read().split()
            return types.SimpleNamespace(stdout=seqs, returncode=0, stderr="")
        return types.SimpleNamespace(stdout="", returncode=0, stderr="")

    out = str(tmp_path / "ref.fasta")
    n = AP.build_reference_fasta(["Micromonospora"], "DB", out, cap_per_genus=30,
                                 sentinels=(), outgroup=(), runner=runner)
    assert n == 2
    assert set(calls["batch"]) == {"A1", "A2"}   # only the Micromonospora accessions were fetched


# ---- routing table --------------------------------------------------------------------------------
def test_write_routing_table(tmp_path):
    assigned = {"AS-1": {"genus": "Streptomyces", "pident": 99.0, "aln_len": "1400", "title": "t"}}
    out = str(tmp_path / "r.tsv")
    AP.write_routing_table(assigned, out)
    body = open(out).read().splitlines()
    assert body[0].startswith("query\ttophit_genus")
    assert "STREPTOMYCES\tstreptomyces" in body[1]


# ---- the gate cannot be skipped -------------------------------------------------------------------
def test_run_16s_refuses_without_approval(tmp_path, capsys):
    q = _write(tmp_path, "q.fasta", [("AS-1", "ACGT" * 350)])
    rc = AP.main(["run-16s", "--query", q, "--db", "DB", "--group", "rare_genera",
                  "--outdir", str(tmp_path / "o")])
    assert rc == 1
    assert "tree-approval gate" in capsys.readouterr().err


def test_run_16s_passes_bootstrap_to_phylo_place(tmp_path, monkeypatch):
    """The placement-appropriate bootstrap must reach the phylo_place command (the dial-in fix)."""
    q = _write(tmp_path, "q.fasta", [("AS-1", "ACGT" * 350), ("AS-2", "ACGT" * 350)])
    monkeypatch.setattr(AP, "assign_genus", lambda *a, **k: {
        "AS-1": {"genus": "Micromonospora", "pident": 99.0, "aln_len": "1400", "title": "t"},
        "AS-2": {"genus": "Micromonospora", "pident": 98.0, "aln_len": "1400", "title": "t"}})
    monkeypatch.setattr(AP, "build_reference_fasta", lambda *a, **k: 5)
    seen = {}

    def fake_run(cmd, *a, **k):
        seen["cmd"] = cmd
        return types.SimpleNamespace(returncode=0)
    monkeypatch.setattr(AP.subprocess, "run", fake_run)
    rc = AP.main(["run-16s", "--query", q, "--db", "DB", "--group", "rare_genera",
                  "--outdir", str(tmp_path / "o"), "--approved-by", "tester", "--bootstrap", "7"])
    assert rc == 0
    assert "--bootstrap" in seen["cmd"] and seen["cmd"][seen["cmd"].index("--bootstrap") + 1] == "7"
