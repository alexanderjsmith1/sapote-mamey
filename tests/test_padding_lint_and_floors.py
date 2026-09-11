"""v9.7.227: depth floors lowered (stop rewarding padding) + PAD_SIGNAL lint. The char-floor was a
length target that drove ~22-40% padding; floors now catch only skeleton sections, and a WARN-level
lint surfaces residual filler."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import mamey.modeb_structure_gate as G

def test_floors_lowered_and_large_default_flipped():
    fl = G.load_contract() if hasattr(G, "load_contract") else None
    assert G._is_large_bgc({}) is False                       # absent context -> lower floor (was True)
    # the floor constants dropped from the length-target values
    src = pathlib.Path(G.__file__).read_text()
    assert '"card_min_chars_large": 7000' in src              # was 20000
    assert '"heavy_section_min_chars_large": 450' in src      # was 1400

def test_pad_signal_fires_on_padding_not_on_dense():
    padded = ("## §1 Identity\nThis card is for BGC001.\n\n## §11 Product family\n"
              "Read together, the evidence suggests a family. As with BGC012 and BGC034, this is notable. "
              "In practice, the picture is consistent. Taken together, BGC099 adds nothing here.\n")
    assert G._padding_findings(padded)                        # cross-refs + restatement openers -> fires
    dense = ("## §1 Identity\nThis card is for BGC001.\n\n## §11 Product family\n"
             "The KS-AT-DH-KR domain order and a C-starter condensation domain indicate a hybrid "
             "assembly line; BLASTp of ctg1_79 returns an adenylation domain at 61% identity.\n")
    assert not G._padding_findings(dense)                     # evidence prose -> no false positive
