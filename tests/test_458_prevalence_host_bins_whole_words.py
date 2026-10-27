"""Prevalence host bins match whole words, not substrings.

classify() in domain_prevalence and scan_prevalence binned "plant", "Antarctic", "halotolerant"
and "Tibetan antelope" as ant, and "beetle" as bee. Checked over the 748 distinct isolation-source
and host strings in OFFICIAL_DATA: 52 bins change (50 ant -> other, 2 bee -> other), none gain a bin.
"""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(f"{name}_458", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TOOLS = [_load("domain_prevalence"), _load("scan_prevalence")]

CASES = [
    ("plant root (Samanea saman)", "other"),
    ("Antarctic soil, Fildes Peninsula, King George Island", "other"),
    ("soil (halotolerant isolate)", "other"),
    ("faeces of Tibetan antelope (Pantholops hodgsonii), Qinghai-Tibet Plateau", "other"),
    ("frass of Protaetia brevitarsis (beetle) larvae, China", "other"),
    ("leaf-cutting ant Atta cephalotes fungus garden", "ant"),
    ("worker ants", "ant"),
    ("Bombus impatiens gut", "bee"),
    ("honeybee hive", "bee"),
    ("Wax beehive", "bee"),
    ("Native beee covered in pollen", "bee"),
    ("solitary wasp nest", "wasp"),
    ("bee or wasp nest", "bee_or_wasp"),
    ("Sphagnum moss", "moss"),
    ("fungal fruiting body", "fungus_assoc"),
    ("", "unknown"),
]


@pytest.mark.parametrize("mod", TOOLS, ids=["domain_prevalence", "scan_prevalence"])
@pytest.mark.parametrize("src,want", CASES)
def test_classify(mod, src, want):
    assert mod.classify(src) == want
