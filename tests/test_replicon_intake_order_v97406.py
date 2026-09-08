from types import SimpleNamespace

from mamey.parsers import _replicon_intake_key


def _record(identifier, description="", **annotations):
    return SimpleNamespace(
        id=identifier,
        name=identifier,
        description=description,
        annotations=annotations,
    )


def test_chromosome_precedes_plasmid_and_unknown_without_reread():
    records = [
        ("z.region001.gbk", _record("NODE_9")),
        ("p.region001.gbk", _record("repB", "plasmid p2")),
        ("c.region001.gbk", _record("chr", "complete chromosome")),
    ]
    records.sort(key=_replicon_intake_key)
    assert [name for name, _ in records] == [
        "c.region001.gbk", "p.region001.gbk", "z.region001.gbk"
    ]


def test_conflicting_label_is_not_guessed_as_chromosome():
    item = ("ambiguous.region001.gbk", _record("x", "chromosome plasmid assembly"))
    assert _replicon_intake_key(item)[0] == 2


def test_unknowns_are_deterministic_by_source_member():
    records = [
        ("B.region001.gbk", _record("n2")),
        ("a.region001.gbk", _record("n1")),
    ]
    assert [x[0] for x in sorted(records, key=_replicon_intake_key)] == [
        "a.region001.gbk", "B.region001.gbk"
    ]
