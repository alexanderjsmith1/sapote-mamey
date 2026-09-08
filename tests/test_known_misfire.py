import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent

def test_esmeraldin_flagged_known_misfire():
    d = json.load(open(ROOT / "mamey" / "data" / "reference_bgc_library.json"))
    items = d if isinstance(d, list) else d.get("entries", d.get("references"))
    e = [x for x in items if (x.get("compound") or x.get("name")) == "esmeraldin"][0]
    assert e.get("architecture_capacity") == "KNOWN_MISFIRE"
