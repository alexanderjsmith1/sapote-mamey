import csv
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools/taxonomy_T06_figures.py'
@pytest.mark.parametrize('layout',['bee','moss'])
def test_printed_layout_stamp_numbers(tmp_path,layout):
    if not shutil.which('Rscript'): pytest.skip('Rscript not installed')
    cohort=tmp_path/'cohort.tsv'; data=tmp_path/'data.tsv'
    cohort.write_text('strain\tgenus\tblock\nSYN-971\tStreptomyces\tisolates\nSYN-972\tNocardia\tisolates\nSYN-973\tNocardia\tisolates\n')
    data.write_text('strain\tsimilarity\td4\td4_ci_low\td4_ci_high\ttype_strain\nSYN-971\t99\t77.6\t76\t79\tStreptomyces example\nSYN-972\t98\t30\t29\t31\tNocardia example\nSYN-973\t\t40\t39\t41\tNocardia example\n')
    command=[sys.executable,str(TOOL),'--cohort',str(cohort),'--data',str(data),'--out',str(tmp_path/'figure'),'--layout',layout,'--dpi','72']
    if layout=='moss': command+=['--palette-set','moss']
    result=subprocess.run(command,capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    for suffix in ['png','pdf']: assert b'Sapote-Mamey taxonomy_T06_figures' in (tmp_path/f'figure.{suffix}').read_bytes()
    with (tmp_path/'figure_numbers.tsv').open() as f: nums={r['metric']:int(r['count']) for r in csv.DictReader(f,delimiter='\t')}
    assert nums['cohort_rows']==3
    assert nums['plotted_rows']==(3 if 'T06'=='T05' else 2)
    if 'T06'!='T01': assert nums['d4_at_least_70']==1
    else: assert nums['similarity_below_98.65']==1
    again=subprocess.run(command,capture_output=True,text=True)
    assert again.returncode!=0 and 'overwrite' in again.stderr

def test_portable_palette_source():
    text=TOOL.read_text()
    import re
    assert not re.search(r'#[0-9A-Fa-f]{6}',text.split('R_SCRIPT =')[0])
    assert '/Users/' not in text


# Exact lines from the sealed release remain tolerated only in their original file
# and occurrence count. The baseline contains digests, never identifier literals.
def _new_isolate_literals(root, baseline):
    import collections
    import hashlib
    import re
    allowed = baseline["line_sha256_counts"]
    pattern = re.compile(r"AS-(\d{3,})(?!\d)")
    found = []
    for directory in ("tests", "tools", "mamey"):
        for path in sorted((root / directory).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            try:
                source = path.read_text(encoding="utf-8")
            except UnicodeError:
                continue
            if "\0" in source:
                continue
            relative = path.relative_to(root).as_posix()
            remaining = collections.Counter(allowed.get(relative, {}))
            for number, line in enumerate(source.splitlines(), 1):
                hits = pattern.findall(line)
                if not hits:
                    continue
                digest = hashlib.sha256(line.encode()).hexdigest()
                if remaining[digest] > 0:
                    remaining[digest] -= 1
                    continue
                if relative.startswith("tests/") and all(970 <= int(n) <= 999 for n in hits):
                    continue
                found.append(f"{relative}:{number}: {line.strip()}")
    return found


def test_bundle_code_names_no_real_isolate():
    import json
    baseline = json.loads((ROOT / "tests/sealed_450_isolate_literal_baseline.json").read_text())
    assert baseline["schema"] == 1
    assert not _new_isolate_literals(ROOT, baseline)


def test_isolate_guard_rejects_new_or_duplicate_literals(tmp_path):
    import hashlib
    bad = "AS-" + str(123)
    path = tmp_path / "tests/example.py"
    path.parent.mkdir()
    original = f'value = "{bad}"'
    digest = hashlib.sha256(original.encode()).hexdigest()
    baseline = {"line_sha256_counts": {"tests/example.py": {digest: 1}}}
    path.write_text(original + "\n")
    assert not _new_isolate_literals(tmp_path, baseline)
    path.write_text(original + "\n" + original + "\n")
    assert len(_new_isolate_literals(tmp_path, baseline)) == 1
    path.write_text(f'changed = "{bad}"\n')
    assert len(_new_isolate_literals(tmp_path, baseline)) == 1


def test_isolate_guard_scans_all_three_trees_and_regex_builders(tmp_path):
    empty = {"line_sha256_counts": {}}
    for directory in ("tests", "tools", "mamey"):
        path = tmp_path / directory / "new.txt"
        path.parent.mkdir()
        # Regex builders and explicit generic-prefix fixtures are not private IDs.
        path.write_text('pattern = r"AS-' + r'\d+' + '"\nfixture = "SYN-971"\n')
    assert not _new_isolate_literals(tmp_path, empty)
    for directory in ("tests", "tools", "mamey"):
        with (tmp_path / directory / "new.txt").open("a") as fh:
            fh.write('literal = "AS-' + str(123) + '"\n')
    assert len(_new_isolate_literals(tmp_path, empty)) == 3


def test_isolate_guard_reserves_test_range_and_rejects_production_ids(tmp_path):
    empty = {"line_sha256_counts": {}}
    for directory in ("tests", "tools", "mamey"):
        (tmp_path / directory).mkdir()
    path = tmp_path / "tests/example.py"
    for number in (970, 999):
        path.write_text("AS-" + str(number) + "\n")
        assert not _new_isolate_literals(tmp_path, empty)
    for number in (969, 1000, 999970):
        path.write_text("AS-" + str(number) + "\n")
        assert len(_new_isolate_literals(tmp_path, empty)) == 1
    path.write_text("SYN-970\n")
    for directory in ("tools", "mamey"):
        (tmp_path / directory / "example.py").write_text("AS-" + str(970) + "\n")
    assert len(_new_isolate_literals(tmp_path, empty)) == 2
