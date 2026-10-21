"""v9.7.455 data-home card: User Strain Master init, inbox, store, check and lookup.

Every fixture is a fake master built in tmp_path. Strain IDs are synthetic and built at runtime.
Fail-before for every test: on the .454 source, ``mamey.strain_master`` does not exist and
``mamey.strain_data_home`` has no ``strain_master_record`` or ``master=`` argument, so the module
fails to import (collection error). Pass-after: each test's own docstring says what it proves.
"""
from __future__ import annotations

import datetime
import json
import os
import zipfile
from pathlib import Path

import pytest

from mamey import strain_master as sm
from mamey.strain_data_home import strain_data_home, strain_master_record

A, B, C = ("AS-" + str(970 + i) for i in range(3))   # synthetic
NOW = datetime.datetime(2026, 10, 19, 12, 0)
CHECKS = "2 ok: recounted 2 rows with awk; 3 ok: IDs copied from the source row; 4 ok: no ruling touches these rows; 6 ok: no claim, no private path"
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _no_env(monkeypatch):
    monkeypatch.delenv("SAPOTE_STRAIN_MASTER", raising=False)


def _master(tmp_path, direct=False, raw_stores=()):
    m = tmp_path / "M"
    sm.init_master(str(m), name="Test master", raw_stores=raw_stores)
    if direct:
        cfg = json.loads((m / "strain_master.json").read_text())
        cfg["direct_store"] = True
        (m / "strain_master.json").write_text(json.dumps(cfg))
    return m


def _work(tmp_path, name="ani.tsv", text=None):
    w = tmp_path / "work"
    w.mkdir(exist_ok=True)
    p = w / name
    p.write_text(text if text is not None else f"strain\tani\n{A}\t95.1\n{C}2\t90.0\n")
    return p


def _statuses(report):
    return {c["name"].split(" (")[0]: c["status"] for c in report["checks"]}


def test_init_builds_layout_and_a_new_master_checks_clean(tmp_path):
    """Pass-after: init writes LAYOUT.md, CHANGELOG.md, the inbox ledger and a README in every
    folder, and the generic check on the fresh master is a clean PASS. It refuses an occupied folder."""
    m = _master(tmp_path)
    for f in ("00 README.md", "LAYOUT.md", "CHANGELOG.md", "strain_master.json", "00 Inbox/INBOX_LEDGER.tsv",
              "01 Strains/Source tables/README.md", "03 Genomes/Source tables/README.md",
              "04 Gene clusters/Mamey packages/README.md", "05 Trees/Source tables/README.md"):
        assert (m / f).is_file(), f
    report = sm.check(str(m), now=NOW)
    assert report["result"] == "PASS", sm.check_report_lines(report)
    with pytest.raises(sm.StrainMasterError, match="OCCUPIED"):
        sm.init_master(str(m))


def test_inbox_submit_verify_apply_records_readme_and_changelog(tmp_path):
    """Pass-after: the one way in. submit copies bytes into 00 Inbox/<id>/ with a manifest and a
    SUBMITTED ledger row; the submitter cannot verify; a different chat accepts with numbered checks;
    apply writes the copy, its README row (SHA-256, original path, builder) and one CHANGELOG line,
    and moves the submission's records to Done/. The ledger uses the first master's columns."""
    m = _master(tmp_path)
    src = _work(tmp_path)
    sub = sm.submit([{"src": str(src), "folder": "03 Genomes/ANI", "what": "ANI table", "builder": "fastANI 1.34"}],
                    submitter="chat-a", topic="ANI table", summary="ANI values behind Fig 2", reproduce=["2 rows"],
                    master=str(m), now=NOW)
    assert (m / "00 Inbox" / sub["id"] / "MANIFEST.tsv").is_file()
    assert not (m / "03 Genomes/ANI/ani.tsv").exists()           # nothing in the data folder yet
    with pytest.raises(sm.StrainMasterError, match="SELF_VERIFY"):
        sm.verify(sub["id"], verifier="chat-a", accept=True, checks=CHECKS, master=str(m), now=NOW)
    with pytest.raises(sm.StrainMasterError, match="NEED_CHECKS"):
        sm.verify(sub["id"], verifier="chat-b", accept=True, checks="2 ok: recount", master=str(m), now=NOW)
    with pytest.raises(sm.StrainMasterError, match="NOT_ACCEPTED"):
        sm.apply_submission(sub["id"], chat="chat-b", master=str(m), now=NOW)
    sm.verify(sub["id"], verifier="chat-b", accept=True, checks=CHECKS, master=str(m), now=NOW)
    res = sm.apply_submission(sub["id"], chat="chat-b", master=str(m), now=NOW)
    assert res["status"] == "APPLIED"
    dest = m / "03 Genomes/ANI/ani.tsv"
    assert dest.read_bytes() == src.read_bytes()
    readme = (m / "03 Genomes/ANI/README.md").read_text()
    sha = sm._sha(src.read_bytes())
    assert f"| `ani.tsv` | `{sha}` | `work/ani.tsv` | ANI table. Built by fastANI 1.34. |" in readme
    log = (m / "CHANGELOG.md").read_text()
    assert f"· new · `03 Genomes/ANI/ani.tsv` · sha256 {sha}" in log and "verified by chat-b" in log
    done = sorted(os.listdir(m / "00 Inbox/Done" / sub["id"]))
    assert done == ["APPLIED.md", "MANIFEST.tsv", "SUBMISSION.md", "VERIFICATION.md"]
    assert not (m / "00 Inbox" / sub["id"]).exists()
    header = (m / "00 Inbox/INBOX_LEDGER.tsv").read_text().splitlines()[0].split("\t")
    assert header == list(sm.LEDGER_COLUMNS)
    assert sm.inbox_status(str(m))[0]["status"] == "APPLIED"
    assert src.read_bytes()                                     # original left in place
    assert sm.check(str(m), now=NOW)["result"] == "PASS"


def test_returned_submission_and_inbox_bookkeeping_failures(tmp_path):
    """Pass-after: a returned submission moves to Returned/ with VERIFICATION.md. The check fails on a
    submission folder without a ledger row and on an ACCEPTED one left a day or more."""
    m = _master(tmp_path)
    s1 = sm.submit([{"src": str(_work(tmp_path)), "folder": "03 Genomes/ANI", "what": "ANI"}],
                   submitter="chat-a", topic="one", summary="w", master=str(m), now=NOW)
    sm.verify(s1["id"], verifier="chat-b", accept=False, checks="2: counts do not reproduce", master=str(m), now=NOW)
    assert (m / "00 Inbox/Returned" / s1["id"] / "VERIFICATION.md").is_file()
    s2 = sm.submit([{"src": str(_work(tmp_path, "b.tsv")), "folder": "03 Genomes/ANI", "what": "B"}],
                   submitter="chat-a", topic="two", summary="w", master=str(m), now=NOW)
    sm.verify(s2["id"], verifier="chat-b", accept=True, checks=CHECKS, master=str(m), now=NOW)
    (m / "00 Inbox" / "stray_submission").mkdir()
    report = sm.check(str(m), now=NOW + datetime.timedelta(days=2))
    inbox = next(c for c in report["checks"] if c["name"].startswith("inbox"))
    assert inbox["status"] == "FAIL"
    assert "00 Inbox/stray_submission: no ledger row" in inbox["lines"]
    assert any("accepted more than a day ago" in ln for ln in inbox["lines"])


def test_record_edit_applies_at_its_home_only_when_old_value_holds(tmp_path):
    """Pass-after: a record edit names cells in a record home from the settings; a file outside the
    homes is refused at submit; apply refuses when the cell no longer holds the old value; a good
    edit changes only that cell, keeps a .bak copy and writes a CHANGELOG line."""
    m = _master(tmp_path)
    cfg = json.loads((m / "strain_master.json").read_text())
    cfg["record_homes"] = ["../Records"]
    (m / "strain_master.json").write_text(json.dumps(cfg))
    rec = tmp_path / "Records" / "STRAIN_METADATA.tsv"
    rec.parent.mkdir()
    rec.write_text(f"strain\tgenus\n{A}\tMycobacterium\n{B}\tStreptomyces\n")
    cs = tmp_path / "work" / "edits.tsv"
    cs.parent.mkdir(exist_ok=True)

    def changeset(path, old):
        cs.write_text("file\tkey_column\tkey\tfield\told\tnew\truling\n"
                      f"{path}\tstrain\t{A}\tgenus\t{old}\tMycolicibacterium\truling R1\n")
    changeset(tmp_path / "elsewhere.tsv", "Mycobacterium")
    with pytest.raises(sm.StrainMasterError, match="NOT_A_RECORD_HOME"):
        sm.submit([], submitter="chat-a", topic="genus", summary="s", kind="record-edit", changeset=str(cs),
                  master=str(m), now=NOW)
    changeset(rec, "Mycobacteria")                               # wrong old value
    s = sm.submit([], submitter="chat-a", topic="genus bad", summary="s", kind="record-edit", changeset=str(cs),
                  master=str(m), now=NOW)
    sm.verify(s["id"], verifier="chat-b", accept=True, checks=CHECKS, master=str(m), now=NOW)
    with pytest.raises(sm.StrainMasterError, match="OLD_VALUE_DIFFERS"):
        sm.apply_submission(s["id"], chat="chat-b", master=str(m), now=NOW)
    assert "Mycobacterium" in rec.read_text()
    changeset(rec, "Mycobacterium")
    s = sm.submit([], submitter="chat-a", topic="genus good", summary="s", kind="record-edit", changeset=str(cs),
                  master=str(m), now=NOW + datetime.timedelta(minutes=1))
    sm.verify(s["id"], verifier="chat-b", accept=True, checks=CHECKS, master=str(m), now=NOW)
    sm.apply_submission(s["id"], chat="chat-b", master=str(m), now=NOW)
    assert rec.read_text() == f"strain\tgenus\n{A}\tMycolicibacterium\n{B}\tStreptomyces\n"
    assert (tmp_path / "Records" / "STRAIN_METADATA.tsv.bak_2026-10-19_1200_inbox").is_file()
    assert "record edit genus good: 1 cell(s)" in (m / "CHANGELOG.md").read_text()


def test_store_unchanged_then_replaced_moves_old_copy_to_superseded(tmp_path):
    """Pass-after: storing the same bytes again changes nothing and logs nothing; new bytes replace
    the copy, the old copy moves to Superseded/<date>_<name> with a README row, and the check passes."""
    m = _master(tmp_path, direct=True)
    src = _work(tmp_path)
    sm.store(str(src), "03 Genomes/ANI", "ANI", master=str(m), now=NOW)
    log1 = (m / "CHANGELOG.md").read_text()
    assert sm.store(str(src), "03 Genomes/ANI", "ANI", master=str(m), now=NOW)["action"] == "unchanged"
    assert (m / "CHANGELOG.md").read_text() == log1
    old = src.read_bytes()
    src.write_text(f"strain\tani\n{A}\t95.2\n")
    res = sm.store(str(src), "03 Genomes/ANI", "ANI", master=str(m), now=NOW)
    assert res["action"] == "replaced"
    assert (m / "03 Genomes/ANI/Superseded/2026-10-19_ani.tsv").read_bytes() == old
    readme = (m / "03 Genomes/ANI/README.md").read_text()
    assert "`Superseded/` holds earlier copies" in readme and "2026-10-19_ani.tsv" in readme
    assert sm.check(str(m), now=NOW)["result"] == "PASS"


def test_store_zip_member(tmp_path):
    """Pass-after: one ZIP member is copied byte for byte and its origin names the ZIP and member."""
    m = _master(tmp_path, direct=True)
    z = tmp_path / "work" / "drop.zip"
    z.parent.mkdir()
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("out/NEAREST_KS.tsv", "a\tb\n")
    res = sm.store(str(z), "04 Gene clusters/Protein space", "KS nearest", member="out/NEAREST_KS.tsv",
                   master=str(m), now=NOW)
    assert (m / "04 Gene clusters/Protein space/NEAREST_KS.tsv").read_text() == "a\tb\n"
    assert res["origin"] == "`work/drop.zip` → `out/NEAREST_KS.tsv`"


def test_refuses_writes_outside_the_root(tmp_path):
    """Pass-after: '..', absolute and inbox folders, a reserved name, a symlinked folder that leaves
    the root, no master and direct store without opting in are all refused, and nothing outside the
    master is written."""
    m = _master(tmp_path, direct=True)
    src = _work(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    for folder in ("../outside", str(outside), "03 Genomes/../../outside", "00 Inbox/Done", "03 Genomes"):
        with pytest.raises(sm.StrainMasterError, match="BAD_FOLDER|OUTSIDE_ROOT"):
            sm.store(str(src), folder, "x", master=str(m))
    with pytest.raises(sm.StrainMasterError, match="BAD_NAME"):
        sm.store(str(src), "03 Genomes/ANI", "x", name="../ani.tsv", master=str(m))
    (m / "03 Genomes/ANI/link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(sm.StrainMasterError, match="OUTSIDE_ROOT"):
        sm.store(str(src), "03 Genomes/ANI/link", "x", master=str(m))
    with pytest.raises(sm.StrainMasterError, match="NO_MASTER"):
        sm.store(str(src), "03 Genomes/ANI", "x")
    assert list(outside.iterdir()) == []
    m2 = tmp_path / "M2"
    sm.init_master(str(m2))
    with pytest.raises(sm.StrainMasterError, match="INBOX_REQUIRED"):
        sm.store(str(src), "03 Genomes/ANI", "x", master=str(m2))


def test_layout_refuses_and_check_fails_on_unlisted_folders(tmp_path):
    """Pass-after: a folder outside LAYOUT.md is refused at submit and store, and a folder made by
    hand at the top level or inside an area fails the layout check."""
    m = _master(tmp_path, direct=True)
    src = _work(tmp_path)
    with pytest.raises(sm.StrainMasterError, match="NOT_IN_LAYOUT"):
        sm.store(str(src), "03 Genomes/Stray", "x", master=str(m), create=True, intro="y")
    with pytest.raises(sm.StrainMasterError, match="NOT_IN_LAYOUT"):
        sm.submit([{"src": str(src), "folder": "03 Genomes/Stray", "what": "x"}], submitter="chat-a",
                  topic="t", summary="w", master=str(m))
    sm.store(str(src), "05 Trees/Tree one", "tree inputs", master=str(m), create=True, intro="One tree")   # '*' area
    assert "`Tree one/`" in (m / "05 Trees/README.md").read_text()
    (m / "03 Genomes/Stray").mkdir()
    (m / "08 Extra").mkdir()
    layout = next(c for c in sm.check(str(m), now=NOW)["checks"] if c["name"].startswith("layout"))
    assert layout["status"] == "FAIL"
    assert "03 Genomes/Stray/: folder not in the layout" in layout["lines"]
    assert "08 Extra/: top-level folder not in the layout" in layout["lines"]


def test_check_catches_hand_edits_and_unlisted_files(tmp_path):
    """Pass-after: a copy edited by hand fails both the README checksum and the CHANGELOG check; a
    file dropped in without a record fails the checksum check."""
    m = _master(tmp_path, direct=True)
    sm.store(str(_work(tmp_path)), "03 Genomes/ANI", "ANI", master=str(m), now=NOW)
    (m / "03 Genomes/ANI/ani.tsv").write_text("edited\n")
    (m / "03 Genomes/TYGS dDDH/loose.tsv").write_text("x\n")
    report = sm.check(str(m), now=NOW)
    lines = [ln for c in report["checks"] for ln in c["lines"]]
    assert report["result"] == "FAIL"
    assert "03 Genomes/ANI/ani.tsv: checksum differs" in lines
    assert "03 Genomes/ANI/ani.tsv: changed since its last logged import" in lines
    assert "03 Genomes/TYGS dDDH/loose.tsv: on disk, not in the README" in lines


def test_check_reads_first_instance_shapes(tmp_path):
    """Pass-after: the generic check reads the first master's existing tables: a wider header
    (Bytes, Matching copy elsewhere), files in subfolders listed by relative path, a subfolder with
    its own README checked on its own, and a Superseded section. No LAYOUT.md is a FAIL with a reason."""
    m = tmp_path / "Old"
    raw = m / "02 Bioassays/Raw plate reader"
    (raw / "96-well").mkdir(parents=True)
    (raw / "96-well/p1.txt").write_text("plate\n")
    sha = sm._sha(b"plate\n")
    (raw / "README.md").write_text("# Raw\n\n| File | SHA-256 | Bytes | Matching copy elsewhere |\n|---|---|---|---|\n"
                                   f"| `96-well/p1.txt` | `{sha}` | 6 | none |\n")
    sub = m / "03 Genomes/ANI/checks"
    sub.mkdir(parents=True)
    (sub / "README.md").write_text("# checks\n\nfree text, no table\n")
    (sub / "pair.txt").write_text("x\n")
    (m / "03 Genomes/ANI/README.md").write_text("# ANI\n\n| File | SHA-256 | Copied from | What it is |\n|---|---|---|---|\n\n"
                                               "`Superseded/` holds earlier copies:\n\n| File | SHA-256 | Why |\n|---|---|---|\n"
                                               f"| `old.tsv` | `{sha}` | replaced |\n")
    report = sm.check(str(m), now=NOW)
    st = _statuses(report)
    assert st["files match their README checksums"] == "PASS", sm.check_report_lines(report)
    assert st["layout matches LAYOUT.md"] == "FAIL"


def test_where_finds_type_strain_and_falls_back_to_raw_store(tmp_path):
    """Pass-after: lookup by folder name, area path and output kind; a strain found by file name and
    by mention inside a registered table (whole token only); a strain the master lacks falls back
    to the configured raw store's flavored antiSMASH home."""
    raw = tmp_path / "Raw"
    z = raw / "_ANTISMASH_CANONICAL/strict" / f"{B}.zip"
    z.parent.mkdir(parents=True)
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr(f"{B}.json", "{}")
    m = _master(tmp_path, direct=True, raw_stores=["../Raw"])
    sm.store(str(_work(tmp_path)), "03 Genomes/ANI", "ANI", master=str(m), now=NOW)
    sm.store(str(_work(tmp_path, f"{A}_bigscape.tsv", "x\n")), "04 Gene clusters/BiG-SCAPE", "families",
             master=str(m), now=NOW)
    for t in ("ANI", "03 Genomes/ANI", "ani"):
        assert strain_master_record(t, master=str(m))["folder"] == "03 Genomes/ANI"
    assert strain_master_record("mamey_package", master=str(m))["folder"] == "04 Gene clusters/Mamey packages"
    r = strain_master_record("ANI", strain=A, master=str(m))
    assert r["status"] == "FOUND" and r["files_mentioning"] == [{"file": "ani.tsv", "lines": 1}]
    assert strain_master_record("ANI", strain=A[:-1], master=str(m))["status"] == "NOT_IN_MASTER"   # a shorter ID is a different strain
    r = strain_master_record("BiG-SCAPE", strain=A, master=str(m))
    assert [x["file"] for x in r["strain_records"]] == [f"{A}_bigscape.tsv"]
    r = strain_master_record("antiSMASH", strain=B, master=str(m))
    assert r["status"] == "NOT_IN_MASTER"
    assert r["raw_stores"][0]["canonical_antismash"] == {"strict": str(raw / "_ANTISMASH_CANONICAL/strict") + f"/{B}.zip"}
    assert strain_master_record("Nope", master=str(m))["status"] == "NO_SUCH_TYPE"
    assert strain_master_record("ANI")["status"] == "NOT_CONFIGURED"


def test_strain_data_home_master_first_then_legacy(tmp_path, monkeypatch):
    """Pass-after: with a master configured (argument or SAPOTE_STRAIN_MASTER), a README-registered
    antiSMASH ZIP there wins; an unregistered ZIP is ignored; a strain the master lacks resolves
    from the legacy homes; with no master, strain_master is None and legacy resolution is unchanged."""
    legacy = tmp_path / "W"
    for s in (A, B):
        p = legacy / "strain_data" / s / "antiSMASH" / f"{s}.zip"
        p.parent.mkdir(parents=True)
        with zipfile.ZipFile(p, "w") as zf:
            zf.writestr(f"{s}.json", "{}")
    m = _master(tmp_path, direct=True)
    held = tmp_path / "work" / f"{A}.zip"
    held.parent.mkdir()
    with zipfile.ZipFile(held, "w") as zf:
        zf.writestr(f"{A}.json", '{"held": 1}')
    sm.store(str(held), "antismash_zip", "antiSMASH result", master=str(m), now=NOW)
    with zipfile.ZipFile(m / "04 Gene clusters/antiSMASH" / f"{C}.zip", "w") as zf:     # not registered
        zf.writestr(f"{C}.json", "{}")
    h = strain_data_home(A, root=str(legacy), master=str(m))
    assert h["antismash_zip"] == str(m / "04 Gene clusters/antiSMASH" / f"{A}.zip")
    assert h["resolved_from"]["antismash_zip"] == "strain_master"
    hb = strain_data_home(B, root=str(legacy), master=str(m))
    assert hb["resolved_from"]["antismash_zip"] == "legacy" and hb["antismash_zip"].startswith(str(legacy))
    assert strain_data_home(C, root=str(legacy), master=str(m))["antismash_zip"] is None
    plain = strain_data_home(A, root=str(legacy))
    assert plain["strain_master"] is None and plain["antismash_zip"].startswith(str(legacy))
    monkeypatch.setenv("SAPOTE_STRAIN_MASTER", str(m))
    assert strain_data_home(A, root=str(legacy))["resolved_from"]["antismash_zip"] == "strain_master"


def test_adopt_writes_only_the_settings_file(tmp_path):
    """Pass-after: adopt adds strain_master.json to an existing folder and touches nothing else;
    a second adopt is refused."""
    old = tmp_path / "Old"
    (old / "01 Strains").mkdir(parents=True)
    (old / "01 Strains/README.md").write_text("# s\n")
    before = sorted(p.relative_to(old).as_posix() for p in old.rglob("*"))
    sm.adopt_master(str(old), raw_stores=["../Raw"])
    after = sorted(p.relative_to(old).as_posix() for p in old.rglob("*"))
    assert sorted(set(after) - set(before)) == ["strain_master.json"]
    with pytest.raises(sm.StrainMasterError, match="ALREADY_ADOPTED"):
        sm.adopt_master(str(old))


def test_cli_exit_codes(tmp_path, capsys):
    """Pass-after: `strain-master check` exits 0 on PASS and 1 on FAIL; a refusal exits 2; submit
    and status run through the CLI with the first master's flags."""
    from mamey import cli
    m = _master(tmp_path)
    assert cli.main(["strain-master", "check", "--master", str(m)]) == 0
    assert "RESULT: PASS" in capsys.readouterr().out
    src = _work(tmp_path)
    assert cli.main(["strain-master", "submit", "--master", str(m), "--chat", "chat-a", "--topic", "ani",
                     "--target", "03 Genomes/ANI", "--summary", "s", "--what", "ANI", str(src)]) == 0
    assert cli.main(["strain-master", "status", "--master", str(m)]) == 0
    assert "SUBMITTED" in capsys.readouterr().out
    assert cli.main(["strain-master", "store", "--master", str(m), "--target", "03 Genomes/ANI", "--what", "x",
                     str(src)]) == 2                                   # direct store is off
    assert "INBOX_REQUIRED" in capsys.readouterr().out
    (m / "08 Extra").mkdir()
    assert cli.main(["strain-master", "check", "--master", str(m)]) == 1


def test_antismash_zip_of_record_beats_a_package(tmp_path):
    """Review 2.2. Fail-before: with a flavored canonical ZIP and a package both present and no
    flavor given, the resolver returned the package as "the antiSMASH zip". Pass-after: the
    canonical ZIP wins and is labelled; two different flavors give None with both listed; only a
    package left gives the package, labelled package_embedded."""
    w = tmp_path / "W"
    canon = w / "Store/_ANTISMASH_CANONICAL/loose" / f"{A}.zip"
    canon.parent.mkdir(parents=True)
    with zipfile.ZipFile(canon, "w") as zf:
        zf.writestr(f"{A}.json", "{}")
    pkg = w / "mamey_packages" / f"{A}_SapoteMamey_v9.7.450_engine1.9.170_loose_Complete_Package.zip"
    pkg.parent.mkdir(parents=True)
    with zipfile.ZipFile(pkg, "w") as zf:
        zf.writestr(f"{A}.json", "{}")
    from mamey.strain_data_home import clear_strain_data_cache, resolve_antismash_zip
    clear_strain_data_cache()
    h = strain_data_home(A, root=str(w))
    assert h["antismash_zip"] == str(canon) and h["antismash_source_kind"] == "canonical_loose"
    other = w / "Store/_ANTISMASH_CANONICAL/relaxed" / f"{A}.zip"
    other.parent.mkdir(parents=True)
    with zipfile.ZipFile(other, "w") as zf:
        zf.writestr(f"{A}.json", '{"relaxed": 1}')
    h = strain_data_home(A, root=str(w))
    assert h["antismash_zip"] is None and h["antismash_source_kind"] == "AMBIGUOUS_FLAVOR"
    assert set(h["canonical_antismash"]) == {"loose", "relaxed"}
    assert resolve_antismash_zip(A, root=str(w), flavor="relaxed") == str(other)
    canon.unlink(); other.unlink()
    clear_strain_data_cache()
    h = strain_data_home(A, root=str(w))
    assert h["antismash_zip"] == str(pkg) and h["antismash_source_kind"] == "package_embedded"
    clear_strain_data_cache()


def test_package_homes_come_from_the_master_settings(tmp_path, monkeypatch):
    """Review 2.1. Fail-before: a package in a workspace-named home was found only when the
    undocumented MAMEY_PACKAGE_HOMES was set. Pass-after: the master named by SAPOTE_STRAIN_MASTER
    lists it in package_homes, and the resolver finds it with MAMEY_PACKAGE_HOMES unset."""
    monkeypatch.delenv("MAMEY_PACKAGE_HOMES", raising=False)
    w = tmp_path / "W"
    pkg = w / "PACKAGES OF RECORD" / A / f"{A}_SapoteMamey_v9.7.450_engine1.9.170_loose_Complete_Package.zip"
    pkg.parent.mkdir(parents=True)
    with zipfile.ZipFile(pkg, "w") as zf:
        zf.writestr("package/manifest.json", "{}")
    from mamey.strain_data_home import clear_strain_data_cache
    clear_strain_data_cache()
    assert strain_data_home(A, root=str(w))["mamey_package"] is None
    m = _master(tmp_path)
    cfg = json.loads((m / "strain_master.json").read_text())
    cfg["package_homes"] = ["../W/PACKAGES OF RECORD"]
    (m / "strain_master.json").write_text(json.dumps(cfg))
    monkeypatch.setenv("SAPOTE_STRAIN_MASTER", str(m))
    clear_strain_data_cache()
    h = strain_data_home(A, root=str(w))
    assert h["mamey_package"] == str(pkg)
    clear_strain_data_cache()


def test_list_layout_of_the_first_master_is_read(tmp_path):
    """Pass-after: a LAYOUT.md written as a list of folders (the first master's form) is read:
    listed folders pass, an unlisted folder fails, root files are not layout-checked, and inbox
    subfolders are left to the inbox check."""
    m = tmp_path / "Old"
    for d in ("00 Inbox/Done", "01 Strains/Source tables", "03 Genomes/ANI", "03 Genomes/Extra"):
        (m / d).mkdir(parents=True)
    (m / "notes.md").write_text("x\n")
    (m / "LAYOUT.md").write_text("# Layout\n\n## In use\n\n- `00 Inbox`\n- `01 Strains`\n- `01 Strains/Source tables`\n"
                                 "- `03 Genomes`\n- `03 Genomes/ANI`\n\n## Planned\n\n- `05 Trees/Source tables`\n")
    layout = next(c for c in sm.check(str(m), now=NOW)["checks"] if c["name"].startswith("layout"))
    assert layout["lines"] == ["03 Genomes/Extra/: folder not in the layout"]


def test_shipped_sources_hold_no_private_paths():
    """Pass-after: the new and changed shipped files name no home-directory path and no workspace
    folder; the master root is configurable only."""
    for rel in ("mamey/strain_master.py", "mamey/strain_data_home.py", "docs/DATA_HOME.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "/Users/" not in text and "/home/" not in text, rel
        assert "Strain Master New" not in text and "OFFICIAL_DATA/ASSET" not in text, rel
