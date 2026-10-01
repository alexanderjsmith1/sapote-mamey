"""Under `set -o pipefail`, `producer | grep -q` misreports when the producer outlives grep.

grep -q exits at the first match and closes the pipe; a producer that is still writing dies of SIGPIPE (status 141),
and pipefail makes the whole pipeline fail. Two gates were hit:
- tools/release_cut.sh: the CHANGELOG bullet check aborted the cut on a long entry, saying it had no bold bullets;
- tools/make_public_tier.sh: the denylist leak check reported no leak when the term was in many files (fails open).
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
# a producer that writes a bounded amount in one go cannot outlive grep -q
BOUNDED = re.compile(r"^\s*(head|tail|printf|echo)\b")


def _pipefail_scripts():
    for p in sorted(ROOT.rglob("*.sh")):
        if "/tests/" in str(p) or "/.git/" in str(p):
            continue
        text = p.read_text(errors="replace")
        if "pipefail" in text:
            yield p, text


def test_no_grep_q_after_an_unbounded_producer_under_pipefail():
    bad = []
    for p, text in _pipefail_scripts():
        for i, line in enumerate(text.splitlines(), 1):
            code = re.sub(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", "''", line)   # quoted text blanked, so a quoted # is not a comment
            code = re.sub(r"(^|\s)#.*$", "", code)
            m = re.search(r"\|\s*grep\s+-[A-Za-z]*q", code)
            if not m:
                continue
            producer = code[:m.start()].split("|")[-1]
            producer = re.sub(r"^\s*((if|then|elif|while|until|!)\s+)+", "", producer)
            if not BOUNDED.match(producer):
                bad.append(f"{p.relative_to(ROOT)}:{i}: {line.strip()[:120]}")
    assert not bad, "grep -q after an unbounded producer under pipefail:\n" + "\n".join(bad)


@pytest.mark.skipif(BASH is None, reason="needs bash")
def test_release_cut_changelog_check_accepts_a_long_entry(tmp_path):
    script = (ROOT / "tools/release_cut.sh").read_text().splitlines()
    line = next(l for l in script if l.lstrip().startswith("awk 'NR>1 && /^# v9/{exit} {print}' CHANGELOG.md |"))
    pipeline = line.rstrip().rstrip("\\").strip()
    entry = ["# v9.9.999 (test)", "- **a bold bullet** first"]
    entry += [f"- plain bullet {i} with enough words to make the entry long" for i in range(2000)]
    (tmp_path / "CHANGELOG.md").write_text("\n".join(entry + ["# v9.9.998 (older)", "- **old**"]) + "\n")
    r = subprocess.run([BASH, "-c", "set -euo pipefail; " + pipeline], cwd=tmp_path)
    assert r.returncode == 0, "a long CHANGELOG entry with a bold bullet failed the check"


@pytest.mark.skipif(BASH is None, reason="needs bash")
def test_public_tier_leak_check_reports_a_term_in_many_files(tmp_path):
    script = (ROOT / "tools/make_public_tier.sh").read_text()
    cond = re.search(r'^\s*if (grep [^\n]*"\$term" "\$STAGE"[^\n]*?); then', script, re.M).group(1)
    stage = tmp_path / "stage"
    stage.mkdir()
    for i in range(600):
        (stage / f"file_with_a_fairly_long_name_number_{i}.txt").write_text("text with DENYTERM inside\n")
    r = subprocess.run([BASH, "-c", f'set -euo pipefail; if {cond}; then echo LEAK; fi'], cwd=tmp_path,
                       env={"term": "DENYTERM", "STAGE": str(stage), "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True)
    assert "LEAK" in r.stdout, "a denylisted term in 600 files was not reported"
