"""tools/chitinase_hmm_confirm.py fetches its profiles from a Pfam-A.hmm whose ACC lines carry versions.

A released Pfam-A.hmm stores ACC lines like PF00704.35, and hmmfetch's SSI index matches keys exactly, so
build_profiles() asking for the bare PROFILES keys (PF00704 ...) refused on every genome: "hmmfetch failed:
HMM PF00704 not found in SSI index". Found by the M5 (Mosses/MOSS_CHITIN_2026-10-13/method_identity_check/
RESULT_METHOD_IDENTITY_CHECK.md) on the local 30,134-profile Pfam-A.hmm. The fix resolves each bare key
to the file's own ACC before fetching. Thresholds and profile set are unchanged.

The HMMER tests build a small Pfam-style file with hmmbuild (one profile per PROFILES entry, versioned or
bare ACC) and skip if hmmbuild/hmmfetch are not on PATH. The resolver test needs no HMMER.
"""
import importlib.util
import os
import shutil
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "tools", "chitinase_hmm_confirm.py")
spec = importlib.util.spec_from_file_location("chitinase_hmm_confirm_452", SRC)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

HMMER = shutil.which("hmmbuild") and shutil.which("hmmfetch")
SEQS = ("MKTLLAVAGAWLLGSAVAQDKTWE", "MKSLLAVAGAWLIGSAVAQDRTWE")


def _pfam_file(tmp_path, versioned=True, drop=None):
    """One tiny profile per PROFILES accession; ACC is PFxxxxx.N (released Pfam) or bare PFxxxxx."""
    parts = []
    for i, acc in enumerate(m.PROFILES):
        if acc == drop:
            continue
        sto = tmp_path / f"p{i}.sto"
        sto.write_text(f"# STOCKHOLM 1.0\n#=GF ID fam{i}\n#=GF AC {acc}{'.' + str(10 + i) if versioned else ''}\n"
                       f"s1 {SEQS[0]}\ns2 {SEQS[1]}\n//\n")
        out = tmp_path / f"p{i}.hmm"
        subprocess.run(["hmmbuild", "-n", f"fam{i}", "--amino", str(out), str(sto)],
                       check=True, stdout=subprocess.DEVNULL)
        parts.append(out.read_text())
    pf = tmp_path / "Pfam-A.hmm"
    pf.write_text("".join(parts))
    subprocess.run(["hmmfetch", "--index", str(pf)], check=True, stdout=subprocess.DEVNULL)
    return str(pf)


def test_resolver_maps_bare_keys_to_the_files_versioned_acc(tmp_path):
    pf = tmp_path / "x.hmm"
    pf.write_text("NAME  Glyco_hydro_18\nACC   PF00704.35\n//\nNAME  Other\nACC   PF99999.1\n//\n")
    assert m.resolve_accessions(str(pf), ["PF00704", "PF00182"]) == ["PF00704.35", "PF00182"]


@pytest.mark.skipif(not HMMER, reason="hmmbuild/hmmfetch not on PATH")
def test_versioned_release_fetches_every_profile(tmp_path):
    pf = _pfam_file(tmp_path, versioned=True)
    assert m.build_profiles(pf, str(tmp_path / "chitin.hmm")) == len(m.PROFILES)


@pytest.mark.skipif(not HMMER, reason="hmmbuild/hmmfetch not on PATH")
def test_unversioned_file_still_fetches(tmp_path):
    pf = _pfam_file(tmp_path, versioned=False)
    assert m.build_profiles(pf, str(tmp_path / "chitin.hmm")) == len(m.PROFILES)


@pytest.mark.skipif(not HMMER, reason="hmmbuild/hmmfetch not on PATH")
def test_a_profile_missing_from_the_release_still_refuses(tmp_path):
    pf = _pfam_file(tmp_path, versioned=True, drop="PF06483")
    with pytest.raises(m.ChitinaseConfirmError):
        m.build_profiles(pf, str(tmp_path / "chitin.hmm"))
