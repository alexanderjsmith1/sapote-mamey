"""Card 458_bioassay_caption_from_plotted_platforms: the bioassay caption's platform sentence comes from the
platforms behind the plotted values (the read_on column of the best-value table), not a fixed 384-well sentence.

The defect: every caption said "384-well data use only the bound 120 µg/mL selection", also for P. larvae, which was
screened on 96-well plates only. Synthetic tables; --prepare-only, so R is not needed.
"""
import json
from pathlib import Path

from mamey.bioassay_paper import cli, sha, write

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ["strain", "organism", "material", "best_pct", "best_96", "best_384_120", "read_on"]


def run(tmp_path, kind, rows, fields=FIELDS):
    table, roster, aliases, lock = (tmp_path / n for n in ("assay.tsv", "roster.tsv", "aliases.json", "lock.json"))
    aliases.write_text("{}"); lock.write_text("{}")
    write(roster, [dict(strain=f"SYN-{970 + i}", genus="Streptomyces", group="Bryophytes") for i in range(3)])
    write(table, [dict(zip(fields, r)) for r in rows], fields)
    out = tmp_path / f"out_{kind}"
    cli(kind, ROOT / f"tools/bioassay_{kind.lower()}.R",
        ["--table", str(table), "--roster", str(roster), "--aliases", str(aliases), "--lock", str(lock),
         "--table-sha256", sha(table), "--lock-sha256", sha(lock), "--layout", "moss", "--out", str(out),
         "--prepare-only"])
    return (out / "CAPTION.md").read_text(), json.loads((out / "RUN_INFO.json").read_text())


def larvae(strain, v):
    return [(strain, o, "Crude extract", v, v, "", "96-well") for o in ("Foulbrood 19118-1", "Foulbrood 818")]


def test_96_well_only_targets_get_no_384_wording(tmp_path):
    rows = larvae("SYN-970", "85") + larvae("SYN-971", "10")
    rows += [("SYN-970", "MRSA", "Crude extract", "90", "90", "", "96-well"),
             ("SYN-971", "MRSA", "Crude extract", "5", "5", "", "96-well")]
    cap, info = run(tmp_path, "A03", rows)
    assert "384" not in cap
    assert "All plotted values are from 96-well plates." in cap
    assert info["plotted_platforms"] == {"MRSA": ["96-well"], "P. larvae": ["96-well"]}


def test_a_mixed_target_says_which_value_is_used(tmp_path):
    rows = larvae("SYN-970", "85") + larvae("SYN-971", "10")
    rows += [("SYN-970", "MRSA", "Crude extract", "90", "40", "90", "both"),      # read on both: the higher is used
             ("SYN-971", "MRSA", "Crude extract", "5", "5", "", "96-well")]
    cap, info = run(tmp_path, "A03", rows)
    assert "384-well data use only" not in cap
    assert "P. larvae was screened on 96-well plates only." in cap
    assert ("MRSA values are from 96-well plates and 384-well plates at the bound 120 µg/mL selection; "
            "where an isolate was read on both, the higher value is used.") in cap
    assert info["plotted_platforms"] == {"MRSA": ["384-well", "96-well"], "P. larvae": ["96-well"]}


def test_only_plotted_values_count(tmp_path):
    """A 384-well MRSA reading for an isolate with no P. larvae reading is not on the A03 plot, so it adds nothing."""
    rows = larvae("SYN-970", "85")
    rows += [("SYN-970", "MRSA", "Crude extract", "90", "90", "", "96-well"),
             ("SYN-972", "MRSA", "Crude extract", "70", "", "70", "384-well")]
    cap, _ = run(tmp_path, "A03", rows)
    assert "384" not in cap


def test_a_table_without_platforms_makes_no_platform_claim(tmp_path):
    fields = ["strain", "organism", "material", "best_pct"]
    rows = [r[:4] for r in larvae("SYN-970", "85")] + [("SYN-970", "MRSA", "Crude extract", "90")]
    cap, info = run(tmp_path, "A03", rows, fields)
    assert "384" not in cap and "96-well" not in cap
    assert "The input table does not record the plate platform." in cap
    assert info["plotted_platforms"] == {"MRSA": ["not recorded"], "P. larvae": ["not recorded"]}
