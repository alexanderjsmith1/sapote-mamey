"""NC-005: machine-readable signed strict-health waiver — logic + shipped-waiver validity."""
import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _rh():
    spec = importlib.util.spec_from_file_location("repo_health", _ROOT / "tools" / "repo_health.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["repo_health"] = m  # register before exec so the @dataclass annotations resolve
    spec.loader.exec_module(m)
    return m


def test_waiver_requires_full_signature(tmp_path):
    rh = _rh()
    entry = {"metric": "print_calls", "ceiling": 1300, "observed": 1389, "owner": "X", "reason": "Y"}
    p = tmp_path / "w.json"
    p.write_text(json.dumps({"schema_version": rh._WAIVER_SCHEMA, "waivers": [entry]}))
    assert "print_calls" in rh.load_waivers(p)
    # missing owner -> invalid, not loaded
    p.write_text(json.dumps({"schema_version": rh._WAIVER_SCHEMA,
                             "waivers": [{k: v for k, v in entry.items() if k != "owner"}]}))
    assert rh.load_waivers(p) == {}
    # non-int observed -> invalid
    p.write_text(json.dumps({"schema_version": rh._WAIVER_SCHEMA,
                             "waivers": [{**entry, "observed": "139"}]}))
    assert rh.load_waivers(p) == {}
    # wrong schema -> ignored
    p.write_text(json.dumps({"schema_version": "nope", "waivers": [entry]}))
    assert rh.load_waivers(p) == {}


def test_waiver_covers_only_up_to_signed_observed():
    rh = _rh()
    w = {"observed": 139}
    assert rh._waiver_covers(w, 139) and rh._waiver_covers(w, 100)
    assert not rh._waiver_covers(w, 140)   # drift above the signed count is NOT covered
    assert not rh._waiver_covers(w, None)


def test_shipped_waiver_is_valid_and_signed():
    rh = _rh()
    w = rh.load_waivers(_ROOT / "STRICT_HEALTH_WAIVER.json")
    assert {"silent_swallow", "print_calls"} <= set(w)
    for e in w.values():
        assert e["owner"] and e["reason"] and isinstance(e["observed"], int)
