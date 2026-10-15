"""Card attine_452_b02_italic_row_notes: B02 (bgc_classes_per_genome) sets row notes that are genus names in italics.

Attine Fig. S5 notes each row with the host ant genus (Atta, Acromyrmex, Myrmicocrypta), which must be italic. The
names come from an explicit --italic-row-notes list, never from guessing; without it the labels are as before.
Synthetic IDs only.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("b02_italic", ROOT / "tools/bgc_classes_per_genome.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
GENOMES = [dict(strain="AS-971", genus="Synthetica", row_note="Atta"),
           dict(strain="AS-972", genus="Synthetica", row_note="Lower attine"),
           dict(strain="AS-973", genus="Exemplaria", row_note="")]


def test_listed_notes_are_italic_and_others_are_not():
    lab = mod.row_labels(GENOMES, {"Atta", "Acromyrmex"})
    assert lab["AS-971"] == "<i>Synthetica</i> (<i>Atta</i>)"
    assert lab["AS-972"] == "<i>Synthetica</i> (Lower attine)"
    assert lab["AS-973"] == "<i>Exemplaria</i>"


def test_default_labels_are_unchanged():
    lab = mod.row_labels(GENOMES)
    assert lab["AS-971"] == "<i>Synthetica</i> (Atta)" and lab["AS-972"] == "<i>Synthetica</i> (Lower attine)"


def test_option_is_recorded():
    src = (ROOT / "tools/bgc_classes_per_genome.py").read_text()
    assert '"--italic-row-notes"' in src and '"italic_row_notes":sorted(set(args.italic_row_notes))' in src
