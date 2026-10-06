"""docs/ANTISMASH_WEB_SUBMISSION_SOP.md: the antiSMASH web procedure, with the light-touch queue rule.

2026-10-02: "a very light approach on the antiSMASH web server, with a strict 'no submission if a queue' approach",
noting that a 20-30 s "queued" with about 20 jobs running is transient, and that a real queue starts above about 65 running.
Text-contract tests; no network.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOP = ROOT / "docs" / "ANTISMASH_WEB_SUBMISSION_SOP.md"


def text():
    return SOP.read_text(encoding="utf-8")


def test_the_sop_exists_and_is_indexed():
    assert SOP.exists()
    assert "docs/ANTISMASH_WEB_SUBMISSION_SOP.md" in (ROOT / "CURRENT_DOCS_INDEX.md").read_text(encoding="utf-8")


def test_no_submission_while_a_queue_exists_or_the_server_is_busy():
    t = text()
    assert "queue_length" in t and "is 0" in t
    assert re.search(r"`running` is below 60", t)
    assert "Never submit while `queue_length` is above 0 or `running` is 60 or more." in t


def test_a_transient_queued_state_is_not_treated_as_a_queue():
    t = text()
    assert "20–30 seconds" in t and "not a queue" in t
    assert "more than 2 minutes" in t


def test_settings_are_loose_with_all_eleven_features_and_no_email():
    t = text()
    assert "hmmdetection_strictness=loose" in t
    for f in ("knownclusterblast", "clusterblast", "subclusterblast", "cc_mibig", "asf", "rre", "clusterhmmer",
              "pfam2go", "tigrfam", "tfbs", "ncbi_context"):
        assert f"{f}=true" in t, f
    assert "Never put an email address" in t


def test_spacing_retry_and_download_rules():
    t = text()
    assert "at least 45 seconds apart" in t
    assert "Never retry automatically." in t
    assert "Download every finished job." in t


def test_the_page_carries_no_machine_paths_or_personal_identifiers():
    t = text()
    assert "/Users/" not in t and "@gmail" not in t and "Claude_Alex" not in t


def test_the_bundle_ships_no_code_that_submits_to_the_public_server():
    for d in ("tools", "mamey", "deliverable_tools"):
        for p in (ROOT / d).rglob("*.py"):
            assert "api/v1.0/submit" not in p.read_text(encoding="utf-8", errors="ignore"), p


def test_at_most_five_of_your_jobs_at_once():
    """The owner, 2 Oct: the antiSMASH submission page asks users to limit themselves to 5 concurrent submissions; the public
    SOP encodes it."""
    text = SOP.read_text(encoding="utf-8")
    assert "at most 5 of your jobs on the server at once" in text
    assert "Never have more than 5 of your jobs queued or running at once." in text
