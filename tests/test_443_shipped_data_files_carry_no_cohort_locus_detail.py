"""Shipped data files must not carry per-locus cohort BGC detail.

Ruling, 2026-09-24: no detailed strain BGC data inside Sapote-Mamey code; IDs and class-level
statements are fine. `tools/reclass_discriminating_domains.json` had carried one AS strain's full locus
(assembly contig, region, BGC alias, gene), the domain hit's E-value and bitscore, and four reference
channels' reads, inside a rationale string that `reclass_check` loads. The cohort-level measurement
beside it (55 CDS, 31 paired, 18 N-only, 6 C-only) is class-level and stays.

The lock below is a SHAPE rule, not a roster check: the bundle cannot ship the cohort contig roster,
because that roster is the private material. A SPAdes contig name with a coverage of four or more
decimal places is how a real assembly names a contig. Synthetic examples in shipped data use short
coverages (`cov_30.1`, `cov_50`), so they pass.
"""
import json
import re
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[1]
DATA_FILES = sorted([*(BUNDLE / "tools").glob("*.json"), *(BUNDLE / "mamey" / "data").glob("*.json")])
REAL_CONTIG_SHAPE = re.compile(r"NODE_\d+_length_\d+_cov_\d+\.\d{4,}")
RECLASS = BUNDLE / "tools" / "reclass_discriminating_domains.json"


def test_there_are_data_files_to_check():
    assert len(DATA_FILES) >= 2, "the glob found nothing; this lock would pass vacuously"


def test_no_shipped_data_file_names_a_real_assembly_contig():
    offenders = []
    for path in DATA_FILES:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in REAL_CONTIG_SHAPE.finditer(line):
                offenders.append(f"{path.relative_to(BUNDLE)}:{lineno}: {match.group(0)}")
    assert not offenders, "real-assembly contig names in shipped data:\n" + "\n".join(offenders)


def test_reclass_rationale_keeps_its_class_level_measurement():
    """The fix removes one locus, not the evidence for the rule."""
    rules = json.loads(RECLASS.read_text(encoding="utf-8"))
    text = json.dumps(rules)
    assert "31 paired, 18 N-only, 6 C-only" in text
    assert "HMG-CoA synthase" in text


def test_reclass_rationale_carries_no_hit_level_detail():
    text = RECLASS.read_text(encoding="utf-8")
    for token in ("bitscore", "E=2e-11", "ctg48_4", "BGC028"):  # a masked "AS-XXX" alone is allowed
        assert token not in text, f"hit-level or locus detail still present: {token}"
