import importlib.util,sys
from pathlib import Path
import pytest
SOURCE=Path(__file__).resolve().parents[1]
path=SOURCE/"tools/zip_hygiene_allowlist.py"
spec=importlib.util.spec_from_file_location("zip_policy_admission",path);tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)

@pytest.mark.parametrize("first,second",[("docs/item.pdf","docs/item.pdf"),("docs/item.pdf","./docs/item.pdf"),("./docs/item.pdf","docs/item.pdf"),(" docs/item.pdf ","docs/item.pdf")])
def test_conflicting_duplicate_is_rejected(tmp_path,first,second):
 p=tmp_path/"policy.tsv";p.write_text(f"{first}\t10\tfirst\n{second}\t20\tsecond\n");before=p.read_bytes()
 with pytest.raises(ValueError,match="ZIP_ALLOWLIST_DUPLICATE") as e:tool.load_allowlist(p)
 assert ":2:" in str(e.value) and "line 1" in str(e.value) and p.read_bytes()==before

def test_distinct_entries_and_optional_absence_keep_behavior(tmp_path):
 p=tmp_path/"policy.tsv";p.write_text("./docs/a.pdf\t10\tone\ndocs/b.pdf\t20\ttwo\n")
 assert tool.load_allowlist(p)=={"./docs/a.pdf":(10,"one"),"docs/b.pdf":(20,"two")}
 assert tool.load_allowlist(tmp_path/"absent.tsv")=={}

def test_shipped_policy_still_parses():
 p=SOURCE/"tools/zip_hygiene_allowlist.tsv"
 assert len(tool.load_allowlist(p))==1


def test_dangling_policy_link_is_not_optional_absence(tmp_path):
 p=tmp_path/"policy.tsv";p.symlink_to(tmp_path/"missing.tsv")
 with pytest.raises(ValueError,match="ZIP_ALLOWLIST_UNREADABLE"):tool.load_allowlist(p)
 assert p.is_symlink()

def test_valid_policy_link_still_reads(tmp_path):
 p=tmp_path/"policy.tsv";p.write_text("docs/a.pdf\t10\treason\n");link=tmp_path/"link.tsv";link.symlink_to(p)
 assert tool.load_allowlist(link)=={"docs/a.pdf":(10,"reason")}


def test_broken_parent_policy_link_is_not_optional_absence(tmp_path):
 link=tmp_path/"broken";link.symlink_to(tmp_path/"missing",target_is_directory=True)
 with pytest.raises(ValueError,match="ZIP_ALLOWLIST_UNREADABLE"):tool.load_allowlist(link/"policy.tsv")
 assert link.is_symlink()

def test_valid_parent_link_with_missing_optional_file_stays_optional(tmp_path):
 target=tmp_path/"directory";target.mkdir();link=tmp_path/"valid";link.symlink_to(target,target_is_directory=True)
 assert tool.load_allowlist(link/"absent.tsv")=={}

def test_valid_parent_link_reads_policy(tmp_path):
 target=tmp_path/"directory";target.mkdir();(target/"policy.tsv").write_text("docs/a.pdf\t10\treason\n");link=tmp_path/"valid";link.symlink_to(target,target_is_directory=True)
 assert tool.load_allowlist(link/"policy.tsv")=={"docs/a.pdf":(10,"reason")}
