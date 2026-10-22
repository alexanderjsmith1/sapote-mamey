"""v9.7.456 card 018c0f08_456_strain_master_parity: the bundle's Strain Master catches up with
the first master's inbox (import-tree, record-replace, duplicate-id rules) and self-check
(byte-copied README sections, copies match their sources), and says "Strain Master".

Every fixture is a scratch master built in tmp_path with ``init_master``. Strain IDs are synthetic.
Fail-before: on the sealed .455 source, ``submit`` has no import-tree or record-replace kind (TypeError
or BAD_KIND), ``_row`` returns the first ledger row for a duplicated id, and the top README and
``strain-master --help`` do not say "Strain Master" alone. Pass-after: each docstring says what it proves.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path

import pytest

from mamey import strain_master as sm

A, B = ("AS-" + str(970 + i) for i in range(2))   # synthetic
NOW = datetime.datetime(2026, 10, 21, 12, 0)
CHECKS = "2 ok: recounted the files; 3 ok: names copied from the tree; 4 ok: no ruling touches these; 6 ok: no claim"
GAP = "04 Gene clusters/Gap rescue"
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _no_env(monkeypatch):
    monkeypatch.delenv("SAPOTE_STRAIN_MASTER", raising=False)


def _master(tmp_path):
    m = tmp_path / "M"
    sm.init_master(str(m), name="Test master")
    return m


def _tree(tmp_path, name="tree"):
    """Two levels: a loose file, a plain subfolder, and a subfolder with its own README and a
    deeper folder; plus names an import-tree must skip."""
    t = tmp_path / "work" / name
    (t / "run7" / "deep").mkdir(parents=True)
    (t / "plain").mkdir()
    (t / "cache").mkdir()
    (t / "a.tsv").write_text(f"strain\tregions\n{A}\t31\n")
    (t / "run7" / "README.md").write_text("# run 7\n\nWritten by the tool; see `nowhere/at/all.txt`.\n")
    (t / "run7" / "table.tsv").write_text("region\tscore\n1\t0.5\n")
    (t / "run7" / "deep" / "x.tsv").write_text("x\n1\n")
    (t / "plain" / "b.tsv").write_text("b\n2\n")
    (t / "cache" / "big.bin").write_bytes(b"\0" * 10)
    (t / ".hidden.tsv").write_text("h\n")
    (t / "~$lock.docx").write_text("l\n")
    (t / "a.tsv.bak_2026").write_text("old\n")
    os.symlink(t / "a.tsv", t / "link.tsv")
    return t


def _through(m, tmp_path, *, topic, now=NOW, **kw):
    """submit, verify by a different chat, apply; returns the submission id."""
    s = sm.submit(kw.pop("items", []), submitter="chat-a", topic=topic, summary="gap-rescue outputs",
                  master=str(m), now=now, **kw)
    sm.verify(s["id"], verifier="chat-b", accept=True, checks=CHECKS, master=str(m), now=now)
    sm.apply_submission(s["id"], chat="chat-b", master=str(m), now=now)
    return s["id"]


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _snapshot(folder):
    return {str(p.relative_to(folder)): p.read_bytes() for p in Path(folder).rglob("*") if p.is_file()}


def test_import_tree_places_files_and_lists_a_byte_copied_readme_in_the_parent(tmp_path):
    """Pass-after: an import-tree stages every file under tree/ with a manifest row, skipping hidden,
    lock, .bak, symlinked and excluded names. Apply places each file through store(): a loose file in
    the target README, a plain subfolder with its own new README, and a subfolder that carries its own
    README.md listed under a `### run7/` section of the target README; the copied README is byte-equal
    to its source and never appended to. check() passes."""
    m = _master(tmp_path)
    t = _tree(tmp_path)
    s = sm.submit([], kind="import-tree", tree_src=str(t), target=GAP, exclude=("cache",), submitter="chat-a",
                  topic="gap rescue tree", summary="gap-rescue outputs", master=str(m), now=NOW)
    staged = m / "00 Inbox" / s["id"]
    manifest = (staged / "MANIFEST.tsv").read_text().splitlines()
    files = sorted(ln.split("\t")[0] for ln in manifest[1:])
    assert files == ["tree/a.tsv", "tree/plain/b.tsv", "tree/run7/README.md", "tree/run7/deep/x.tsv",
                     "tree/run7/table.tsv"]
    assert s["files"] == 5
    sm.verify(s["id"], verifier="chat-b", accept=True, checks=CHECKS, master=str(m), now=NOW)
    sm.apply_submission(s["id"], chat="chat-b", master=str(m), now=NOW)

    g = m / GAP
    for rel in ("a.tsv", "plain/b.tsv", "run7/README.md", "run7/table.tsv", "run7/deep/x.tsv"):
        assert (g / rel).read_bytes() == (t / rel).read_bytes(), rel
    assert not (g / "cache").exists() and not (g / "link.tsv").exists() and not (g / ".hidden.tsv").exists()
    assert (g / "run7" / "README.md").read_bytes() == (t / "run7" / "README.md").read_bytes()
    top = (g / "README.md").read_text()
    sec = top.index("### `run7/` (its own README.md is a byte copy")
    assert top.index(f"| `a.tsv` | `{_sha(t / 'a.tsv')}` |") < sec
    assert top.index("- `plain/`: Copied through the inbox") < sec
    assert top.index(f"| `table.tsv` | `{_sha(t / 'run7/table.tsv')}` |") > sec
    assert top.index("- `deep/`") > sec
    assert f"| `x.tsv` | `{_sha(t / 'run7/deep/x.tsv')}` |" in (g / "run7/deep/README.md").read_text()
    assert f"| `b.tsv` | `{_sha(t / 'plain/b.tsv')}` |" in (g / "plain/README.md").read_text()
    log = (m / "CHANGELOG.md").read_text()
    assert f"· new · `{GAP}/run7/table.tsv`" in log
    report = sm.check(str(m), now=NOW)
    assert report["result"] == "PASS", sm.check_report_lines(report)
    names = [c["name"] for c in report["checks"]]
    assert any(n.startswith("copies match their sources") for n in names)


def test_import_tree_refuses_an_empty_tree_and_a_top_level_readme(tmp_path):
    """Pass-after: an empty tree (after skips) is refused; a README.md at the tree's top level, which
    would replace the target folder's own README, is refused unless --tree-dest names a subfolder.
    A refused submission leaves no inbox folder."""
    m = _master(tmp_path)
    empty = tmp_path / "work" / "empty"
    (empty / "sub").mkdir(parents=True)
    (empty / ".DS_Store").write_text("x")
    with pytest.raises(sm.StrainMasterError, match="EMPTY_TREE"):
        sm.submit([], kind="import-tree", tree_src=str(empty), target=GAP, submitter="chat-a", topic="e",
                  summary="s", master=str(m), now=NOW)
    t = _tree(tmp_path)
    (t / "README.md").write_text("# tree\n")
    with pytest.raises(sm.StrainMasterError, match="BAD_TREE"):
        sm.submit([], kind="import-tree", tree_src=str(t), target=GAP, exclude=("cache",), submitter="chat-a",
                  topic="t", summary="s", master=str(m), now=NOW)
    assert sorted(os.listdir(m / "00 Inbox")) == ["Done", "INBOX_LEDGER.tsv", "README.md", "Returned"]
    sid = _through(m, tmp_path, topic="t2", kind="import-tree", tree_src=str(t), target=GAP, tree_dest=f"{A} run 1",
                   exclude=("cache",))
    g = m / GAP
    assert (g / f"{A} run 1" / "README.md").read_text() == "# tree\n"
    assert f"### `{A} run 1/` (its own README.md is a byte copy; listing added by inbox {sid})" in (g / "README.md").read_text()
    report = sm.check(str(m), now=NOW)
    assert report["result"] == "PASS", sm.check_report_lines(report)


def test_second_import_lands_above_an_existing_byte_copy_section(tmp_path):
    """Pass-after: when the target README already carries a `### name/`
    section, a second import-tree's own rows and new-folder lines, and an ordinary import's row, all
    land above that section, so check() still reads them as the folder's own. check() passes."""
    m = _master(tmp_path)
    _through(m, tmp_path, topic="first", kind="import-tree", tree_src=str(_tree(tmp_path)), target=GAP,
             exclude=("cache",))
    t2 = tmp_path / "work" / "tree2"
    (t2 / "newdir").mkdir(parents=True)
    (t2 / "c.tsv").write_text("c\n3\n")
    (t2 / "newdir" / "d.tsv").write_text("d\n4\n")
    _through(m, tmp_path, topic="second", kind="import-tree", tree_src=str(t2), target=GAP)
    e = tmp_path / "work" / "e.tsv"
    e.write_text("e\n5\n")
    _through(m, tmp_path, topic="third", items=[{"src": str(e), "folder": GAP, "what": "E table"}])
    top = (m / GAP / "README.md").read_text()
    sec = top.index("### `run7/`")
    for needle in (f"| `c.tsv` | `{_sha(t2 / 'c.tsv')}` |", "- `newdir/`: Copied through the inbox",
                   f"| `e.tsv` | `{_sha(e)}` |"):
        assert top.index(needle) < sec, needle
    assert top.count("### `run7/`") == 1
    report = sm.check(str(m), now=NOW)
    assert report["result"] == "PASS", sm.check_report_lines(report)


def test_replace_supersedes_and_without_it_apply_refuses(tmp_path):
    """Pass-after: a second import-tree over existing files is refused at apply without --replace,
    and nothing in the target changes. With --replace the changed copies move to Superseded/ beside
    them, with README rows (a byte-copy folder's row goes in its section), and check() passes. Before
    the re-import, check() warns that a copy no longer matches its changed source."""
    m = _master(tmp_path)
    t = _tree(tmp_path)
    _through(m, tmp_path, topic="first", kind="import-tree", tree_src=str(t), target=GAP, exclude=("cache",))
    (t / "a.tsv").write_text(f"strain\tregions\n{A}\t32\n")
    (t / "run7" / "table.tsv").write_text("region\tscore\n1\t0.6\n")
    report = sm.check(str(m), now=NOW)
    copies = next(c for c in report["checks"] if c["name"].startswith("copies match"))
    assert copies["status"] == "WARN" and report["result"] == "PASS with warnings"
    assert any(ln.startswith(f"{GAP}/a.tsv: its source changed") for ln in copies["lines"])
    assert any(ln.startswith(f"{GAP}/run7/table.tsv: its source changed") for ln in copies["lines"])

    g = m / GAP
    before = _snapshot(g)
    later = NOW + datetime.timedelta(minutes=1)
    s = sm.submit([], kind="import-tree", tree_src=str(t), target=GAP, exclude=("cache",), submitter="chat-a",
                  topic="again", summary="s", master=str(m), now=later)
    sm.verify(s["id"], verifier="chat-b", accept=True, checks=CHECKS, master=str(m), now=later)
    with pytest.raises(sm.StrainMasterError, match="TREE_CLASH"):
        sm.apply_submission(s["id"], chat="chat-b", master=str(m), now=later)
    assert _snapshot(g) == before
    assert sm._row(str(m), s["id"])[1]["status"] == "ACCEPTED"       # refused, still waiting

    later2 = NOW + datetime.timedelta(minutes=2)
    _through(m, tmp_path, topic="again replace", now=later2, kind="import-tree", tree_src=str(t), target=GAP,
             exclude=("cache",), replace=True)
    day = NOW.date().isoformat()
    assert (g / "Superseded" / f"{day}_a.tsv").read_text().endswith("\t31\n")
    assert (g / "run7" / "Superseded" / f"{day}_table.tsv").is_file()
    assert (g / "a.tsv").read_bytes() == (t / "a.tsv").read_bytes()
    top = (g / "README.md").read_text()
    sec = top.index("### `run7/`")
    assert top.index(f"| `{day}_a.tsv` |") < sec < top.index(f"| `{day}_table.tsv` |")
    assert not (g / "plain" / "Superseded").exists()                    # unchanged files stay
    report = sm.check(str(m), now=later2)                               # the refused one is under a day old
    assert report["result"] == "PASS", sm.check_report_lines(report)


def test_link_keeps_the_hard_link(tmp_path, monkeypatch):
    """Pass-after: with --link the staged and the stored file share the source's inode, the
    submission carries a LINKED marker, and the README still records the SHA-256 and origin. A tree on
    another volume is refused with LINK_ACROSS_VOLUMES before anything is written."""
    m = _master(tmp_path)
    t = _tree(tmp_path)
    sid = _through(m, tmp_path, topic="linked", kind="import-tree", tree_src=str(t), target=GAP, exclude=("cache",),
                   link=True)
    g = m / GAP
    for rel in ("a.tsv", "run7/table.tsv", "run7/README.md", "run7/deep/x.tsv"):
        assert os.stat(g / rel).st_ino == os.stat(t / rel).st_ino, rel
    assert (m / "00 Inbox" / "Done" / sid / "LINKED").is_file()
    assert f"| `a.tsv` | `{_sha(t / 'a.tsv')}` | `work/tree/a.tsv` |" in (g / "README.md").read_text()
    assert sm.check(str(m), now=NOW)["result"] == "PASS"
    monkeypatch.setattr(sm, "_same_volume", lambda a, b: False)
    with pytest.raises(sm.StrainMasterError, match="LINK_ACROSS_VOLUMES"):
        sm.submit([], kind="import-tree", tree_src=str(t), target=GAP, link=True, submitter="chat-a", topic="x",
                  summary="s", master=str(m), now=NOW + datetime.timedelta(minutes=5))
    assert not any(n.endswith("_chat-a_x") for n in os.listdir(m / "00 Inbox"))


def test_record_replace_applies_only_when_the_table_is_unchanged(tmp_path):
    """Pass-after: a record-replace books the table's SHA-256 and size at submission (TARGET.tsv). A
    path outside the record homes is refused. Apply writes the new bytes into the same file (same
    inode), keeps a .bak copy and writes one CHANGELOG line; when the table moved since submission,
    apply refuses with RECORD_CHANGED and changes nothing."""
    m = _master(tmp_path)
    cfg = json.loads((m / "strain_master.json").read_text())
    cfg["record_homes"] = ["../Records"]
    (m / "strain_master.json").write_text(json.dumps(cfg))
    rec = tmp_path / "Records" / "HOSTS.tsv"
    rec.parent.mkdir()
    rec.write_text(f"strain\thost\n{A}\th1\n")
    new = tmp_path / "work" / "HOSTS_new.tsv"
    new.parent.mkdir()
    new.write_text(f"strain\thost\n{A}\th1\n{B}\th2\n")
    outside = tmp_path / "work" / "other.tsv"
    outside.write_text("x\n")
    with pytest.raises(sm.StrainMasterError, match="NOT_A_RECORD_HOME"):
        sm.submit([{"src": str(new)}], kind="record-replace", replaces=str(outside), submitter="chat-a",
                  topic="hosts", summary="s", master=str(m), now=NOW)
    ino = os.stat(rec).st_ino
    s = sm.submit([{"src": str(new)}], kind="record-replace", replaces=str(rec), submitter="chat-a",
                  topic="hosts", summary="add a row", master=str(m), now=NOW)
    target = (m / "00 Inbox" / s["id"] / "TARGET.tsv").read_text().splitlines()
    assert target[0] == "target\tsha256_at_submission\tbytes_at_submission"
    assert target[1].split("\t")[1:] == [_sha(rec), str(rec.stat().st_size)]
    sm.verify(s["id"], verifier="chat-b", accept=True, checks=CHECKS, master=str(m), now=NOW)
    sm.apply_submission(s["id"], chat="chat-b", master=str(m), now=NOW)
    assert rec.read_bytes() == new.read_bytes() and os.stat(rec).st_ino == ino
    baks = sorted(p.name for p in rec.parent.iterdir() if ".bak_" in p.name)
    assert baks == ["HOSTS.tsv.bak_2026-10-21_1200_inbox"]
    log = (m / "CHANGELOG.md").read_text()
    assert log.count("record replace hosts") == 1

    later = NOW + datetime.timedelta(minutes=1)
    newer = tmp_path / "work" / "HOSTS_newer.tsv"
    newer.write_text(f"strain\thost\n{A}\th3\n")
    s2 = sm.submit([{"src": str(newer)}], kind="record-replace", replaces=str(rec), submitter="chat-a",
                   topic="hosts again", summary="s", master=str(m), now=later)
    sm.verify(s2["id"], verifier="chat-b", accept=True, checks=CHECKS, master=str(m), now=later)
    rec.write_text(f"strain\thost\n{A}\th4\n")                        # the table moved on
    with pytest.raises(sm.StrainMasterError, match="RECORD_CHANGED"):
        sm.apply_submission(s2["id"], chat="chat-b", master=str(m), now=later)
    assert rec.read_text() == f"strain\thost\n{A}\th4\n"
    assert sorted(p.name for p in rec.parent.iterdir() if ".bak_" in p.name) == baks


def test_duplicate_submit_refused_and_row_resolves_the_live_row(tmp_path):
    """Pass-after: a second submission with the same id is refused (SUBMISSION_EXISTS). A ledger that
    already holds a duplicated id (a WITHDRAWN row, then a live one) resolves to the live row, so verify
    acts on it; check() reads WITHDRAWN as a known status kept in Returned/."""
    m = _master(tmp_path)
    src = tmp_path / "work" / "ani.tsv"
    src.parent.mkdir()
    src.write_text("a\n1\n")
    item = [{"src": str(src), "folder": "03 Genomes/ANI", "what": "ANI"}]
    s = sm.submit(item, submitter="chat-a", topic="ani", summary="s", master=str(m), now=NOW)
    with pytest.raises(sm.StrainMasterError, match="SUBMISSION_EXISTS"):
        sm.submit(item, submitter="chat-a", topic="ani", summary="s", master=str(m), now=NOW)
    ledger = m / "00 Inbox" / "INBOX_LEDGER.tsv"
    lines = ledger.read_text().splitlines()
    dead = lines[1].split("\t")
    dead[sm.LEDGER_COLUMNS.index("status")] = "WITHDRAWN"
    ledger.write_text("\n".join([lines[0], "\t".join(dead), lines[1]]) + "\n")
    (m / "00 Inbox" / "Returned" / s["id"]).mkdir()
    _rows, row = sm._row(str(m), s["id"])
    assert row["status"] == "SUBMITTED"
    sm.verify(s["id"], verifier="chat-b", accept=True, checks=CHECKS, master=str(m), now=NOW)
    statuses = [r["status"] for r in sm.inbox_status(str(m))]
    assert statuses == ["WITHDRAWN", "ACCEPTED"]
    inbox = next(c for c in sm.check(str(m), now=NOW)["checks"] if c["name"].startswith("inbox"))
    assert inbox["status"] == "PASS", inbox["lines"]


def test_name_is_strain_master(tmp_path, capsys):
    """Pass-after: the top README written by init_master, `strain-master --help`, docs/DATA_HOME.md and
    the module docstrings say "Strain Master", never "User Strain Master"."""
    from mamey import cli
    m = _master(tmp_path)
    top = (m / "00 README.md").read_text()
    assert "Strain Master" in top and "User Strain Master" not in top
    with pytest.raises(SystemExit):
        cli.main(["strain-master", "--help"])
    out = capsys.readouterr().out
    assert "Strain Master" in out and "User Strain Master" not in out
    for rel in ("docs/DATA_HOME.md", "mamey/strain_master.py", "mamey/strain_data_home.py", "mamey/cli.py"):
        assert "User Strain Master" not in (ROOT / rel).read_text(encoding="utf-8"), rel


def test_cli_import_tree_and_record_replace_flags(tmp_path, capsys):
    """Pass-after: the CLI takes --kind import-tree with --tree-src, --tree-dest, --exclude, --link and
    --replace, and --kind record-replace with --replaces and one file."""
    from mamey import cli
    m = _master(tmp_path)
    t = _tree(tmp_path)
    assert cli.main(["strain-master", "submit", "--master", str(m), "--chat", "chat-a", "--kind", "import-tree",
                     "--topic", "tree", "--summary", "s", "--target", GAP, "--tree-src", str(t),
                     "--tree-dest", "run 1", "--exclude", "cache", "--link", "--replace"]) == 0
    sub = json.loads(capsys.readouterr().out)
    assert sub["files"] == 5
    staged = m / "00 Inbox" / sub["id"]
    assert (staged / "LINKED").is_file() and (staged / "REPLACE").is_file()
    assert (staged / "tree" / "run 1" / "a.tsv").is_file()
    assert cli.main(["strain-master", "submit", "--master", str(m), "--chat", "chat-a", "--kind", "record-replace",
                     "--topic", "r", "--summary", "s", "--replaces", str(t / "a.tsv"), str(t / "plain/b.tsv")]) == 2
    assert "NOT_A_RECORD_HOME" in capsys.readouterr().out


# ------------------------------------------------------------------ v2: audit findings F04, F05, F08, F16
def _accepted(m, *, topic, now=NOW, **kw):
    """submit and verify by a different chat; returns the submission id (not applied)."""
    s = sm.submit(kw.pop("items", []), submitter="chat-a", topic=topic, summary="gap-rescue outputs",
                  master=str(m), now=now, **kw)
    sm.verify(s["id"], verifier="chat-b", accept=True, checks=CHECKS, master=str(m), now=now)
    return s["id"]


def _status(m, sid):
    return sm._row(str(m), sid)[1]["status"]


def test_tree_refuses_a_symlinked_destination_folder_before_any_write(tmp_path):
    """Pass-after (audit F04): a destination folder that is a symlink out of the master is refused
    with OUTSIDE_ROOT at apply, for a copied README and for an ordinary file. Nothing is written
    outside the master or inside it, and the submission stays ACCEPTED with its staged files."""
    m = _master(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    os.symlink(outside, m / GAP / "linked")
    t = tmp_path / "work" / "only_readme"
    t.mkdir(parents=True)
    (t / "README.md").write_text("# copied\n")
    before = _snapshot(m / GAP)
    sid = _accepted(m, topic="escape", kind="import-tree", tree_src=str(t), target=GAP, tree_dest="linked")
    with pytest.raises(sm.StrainMasterError, match="OUTSIDE_ROOT"):
        sm.apply_submission(sid, chat="chat-b", master=str(m), now=NOW)
    assert list(outside.iterdir()) == []
    assert _snapshot(m / GAP) == before
    assert _status(m, sid) == "ACCEPTED"
    assert (m / "00 Inbox" / sid / "tree" / "linked" / "README.md").is_file()

    t2 = tmp_path / "work" / "files"
    (t2 / "linked").mkdir(parents=True)
    (t2 / "a.tsv").write_text("a\n1\n")
    (t2 / "linked" / "b.tsv").write_text("b\n2\n")
    sid2 = _accepted(m, topic="escape two", kind="import-tree", tree_src=str(t2), target=GAP)
    with pytest.raises(sm.StrainMasterError, match="OUTSIDE_ROOT"):
        sm.apply_submission(sid2, chat="chat-b", master=str(m), now=NOW)
    assert list(outside.iterdir()) == [] and not (m / GAP / "a.tsv").exists()


def test_refused_tree_import_installs_nothing_and_can_be_retried(tmp_path):
    """Pass-after (audit F08): when a later file is refused, no earlier file is installed and no
    staged file is consumed. Once the cause is removed, the same accepted submission applies."""
    m = _master(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    t = tmp_path / "work" / "tree"
    (t / "z").mkdir(parents=True)
    (t / "a.tsv").write_text("a\n1\n")
    (t / "z" / "b.tsv").write_text("b\n2\n")
    os.symlink(outside, m / GAP / "z")
    sid = _accepted(m, topic="partial", kind="import-tree", tree_src=str(t), target=GAP)
    with pytest.raises(sm.StrainMasterError, match="OUTSIDE_ROOT"):
        sm.apply_submission(sid, chat="chat-b", master=str(m), now=NOW)
    assert not (m / GAP / "a.tsv").exists() and list(outside.iterdir()) == []
    assert sorted(p.name for p in (m / "00 Inbox" / sid / "tree").rglob("*.tsv")) == ["a.tsv", "b.tsv"]
    os.unlink(m / GAP / "z")
    sm.apply_submission(sid, chat="chat-b", master=str(m), now=NOW)
    assert (m / GAP / "z" / "b.tsv").read_bytes() == (t / "z" / "b.tsv").read_bytes()
    assert sm.check(str(m), now=NOW)["result"] == "PASS"


def test_retry_after_a_partial_install_treats_identical_files_as_unchanged(tmp_path):
    """Pass-after (audit F08): a file already in place with the same bytes is not a clash, so a
    resubmission after an interrupted apply does not need --replace."""
    m = _master(tmp_path)
    t = _tree(tmp_path)
    _through(m, tmp_path, topic="first", kind="import-tree", tree_src=str(t), target=GAP, exclude=("cache",))
    later = NOW + datetime.timedelta(minutes=1)
    _through(m, tmp_path, topic="same again", now=later, kind="import-tree", tree_src=str(t), target=GAP,
             exclude=("cache",))
    assert sm.check(str(m), now=later)["result"] == "PASS"


def test_replace_refuses_a_symlinked_superseded_folder(tmp_path):
    """Pass-after (audit F16): with --replace, a Superseded/ folder that is a symlink out of the master
    is refused before any current copy moves, for a copied README and for an ordinary file. An
    ordinary import through store() is refused the same way."""
    m = _master(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    t = tmp_path / "work" / "tree"
    (t / "copied").mkdir(parents=True)
    (t / "copied" / "README.md").write_text("original evidence\n")
    (t / "copied" / "data.tsv").write_text("d\n1\n")
    _through(m, tmp_path, topic="first", kind="import-tree", tree_src=str(t), target=GAP)
    os.symlink(outside, m / GAP / "copied" / "Superseded")
    (t / "copied" / "README.md").write_text("replacement evidence\n")
    (t / "copied" / "data.tsv").write_text("d\n2\n")
    before = _snapshot(m / GAP)
    later = NOW + datetime.timedelta(minutes=1)
    sid = _accepted(m, topic="again", now=later, kind="import-tree", tree_src=str(t), target=GAP, replace=True)
    with pytest.raises(sm.StrainMasterError, match="OUTSIDE_ROOT"):
        sm.apply_submission(sid, chat="chat-b", master=str(m), now=later)
    assert list(outside.iterdir()) == [] and _snapshot(m / GAP) == before

    ani = m / "03 Genomes" / "ANI"
    src = tmp_path / "work" / "ani.tsv"
    src.write_text("a\n1\n")
    _through(m, tmp_path, topic="ani", items=[{"src": str(src), "folder": "03 Genomes/ANI", "what": "ANI"}])
    os.symlink(outside, ani / "Superseded")
    src.write_text("a\n2\n")
    sid2 = _accepted(m, topic="ani again", now=later, items=[{"src": str(src), "folder": "03 Genomes/ANI", "what": "ANI"}])
    with pytest.raises(sm.StrainMasterError, match="OUTSIDE_ROOT"):
        sm.apply_submission(sid2, chat="chat-b", master=str(m), now=later)
    assert list(outside.iterdir()) == [] and (ani / "ani.tsv").read_text() == "a\n1\n"


def test_record_backups_are_unique_and_never_follow_a_link(tmp_path):
    """Pass-after (audit F05): two record replacements in the same minute keep two backups, so the
    oldest bytes survive. A symlink already sitting at the backup name is left alone, the file it
    points to is not written, and the backup goes to the next free name."""
    m = _master(tmp_path)
    cfg = json.loads((m / "strain_master.json").read_text())
    cfg["record_homes"] = ["../Records"]
    (m / "strain_master.json").write_text(json.dumps(cfg))
    rec = tmp_path / "Records" / "T.tsv"
    rec.parent.mkdir()
    rec.write_text("v\n0\n")
    (tmp_path / "work").mkdir()
    for n in (1, 2):
        new = tmp_path / "work" / f"T{n}.tsv"
        new.write_text(f"v\n{n}\n")
        _through(m, tmp_path, topic=f"replace {n}", kind="record-replace", replaces=str(rec), items=[{"src": str(new)}])
    base = f"T.tsv.bak_{NOW:%Y-%m-%d_%H%M}_inbox"
    assert rec.read_text() == "v\n2\n"
    assert (rec.parent / base).read_text() == "v\n0\n"
    assert (rec.parent / f"{base}_2").read_text() == "v\n1\n"

    unrelated = tmp_path / "unrelated.txt"
    unrelated.write_text("preserve these bytes\n")
    later = NOW + datetime.timedelta(minutes=1)
    trap = rec.parent / f"T.tsv.bak_{later:%Y-%m-%d_%H%M}_inbox"
    os.symlink(unrelated, trap)
    new = tmp_path / "work" / "T3.tsv"
    new.write_text("v\n3\n")
    _through(m, tmp_path, topic="replace 3", now=later, kind="record-replace", replaces=str(rec), items=[{"src": str(new)}])
    assert unrelated.read_text() == "preserve these bytes\n" and trap.is_symlink()
    assert (rec.parent / f"{trap.name}_2").read_text() == "v\n2\n" and rec.read_text() == "v\n3\n"
