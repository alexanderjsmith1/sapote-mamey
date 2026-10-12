"""Own-identity exemptions require independently supplied exact public authority."""

from tests._synthetic_identity_fixture import synthetic_namespace_id
from mamey.dedup_and_guard import leak_audit

OWN = "AS-" + "987654"
FOREIGN = "AS-" + "987655"
HARD_PRIVATE = "AJS-" + "987654"


def test_explicit_public_own_identity_is_exempt():
    rows = [{"strain": OWN, "BGC_ID": "BGC001", "release": "PUBLIC", "notes": "clean"}]
    assert leak_audit(rows, public_strains={OWN}) == []


def test_public_row_tag_alone_never_grants_exemption():
    rows = [{"strain": OWN, "BGC_ID": "BGC001", "release": "PUBLIC"}]
    assert len(leak_audit(rows)) == 1


def test_foreign_private_reference_still_caught_in_authorized_row():
    rows = [{"strain": OWN, "BGC_ID": "BGC001", "release": "PUBLIC", "notes": FOREIGN}]
    leaks = leak_audit(rows, public_strains={OWN})
    assert len(leaks) == 1 and FOREIGN in leaks[0]


def test_hard_private_identity_cannot_be_allowlisted():
    rows = [{"strain": HARD_PRIVATE, "BGC_ID": "BGC001", "release": "PUBLIC"}]
    assert len(leak_audit(rows, public_strains={HARD_PRIVATE})) == 1


def test_pending_in_public_notes_remains_caught():
    assert len(leak_audit([{"strain": "public_reference", "release": "PUBLIC", "notes": (synthetic_namespace_id('PENDING', width=None, case_index=917, separator=True))}])) == 1


def test_private_row_not_subject_to_public_cell_audit():
    assert leak_audit([{"strain": OWN, "release": "PRIVATE", "notes": FOREIGN}]) == []
