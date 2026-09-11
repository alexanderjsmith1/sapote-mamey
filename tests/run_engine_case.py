#!/usr/bin/env python3
"""Run one engine (sealed|patched) through the poisoned-scans + corrupt-manifest cases,
dump JSON results for cross-engine comparison. Usage: run_engine_case.py <engine_root> <out.json>"""
import dataclasses
import json
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
root = sys.argv[1]
out = Path(sys.argv[2])
sys.path.insert(0, root)

from mamey.models import BGCRecord               # noqa: E402
from mamey.scoring import triage_bgcs            # noqa: E402
from mamey.packaging import write_manifest       # noqa: E402

try:
    from mamey import degradation
    HAS_DEG = True
    degradation.drain()  # clear any import-time events (registry fallback in partial copies)
except ImportError:
    HAS_DEG = False


class EvilDict:
    """Truthy mapping whose .get always raises — poisons the scan-map extraction guards."""
    def get(self, *a, **k):
        raise RuntimeError("poisoned scan bundle")
    def __bool__(self):
        return True


class PoisonedScans:
    cctt = EvilDict()
    resistance_tiers = EvilDict()
    primary_metabolism = EvilDict()
    misanchor_guards = EvilDict()


bgcs = [
    BGCRecord("BGC001", "NODE_1_length_50000_cov_30", 1, 100, 42000, 50000,
              products=["t1pks"], edge_status="Interior"),
    BGCRecord("BGC002", "NODE_2_length_30000_cov_28", 1, 200, 21000, 30000,
              products=["terpene"], edge_status="Full-contig"),
    BGCRecord("BGC003", "NODE_3_length_9000_cov_25", 1, 50, 8900, 9000,
              products=["nrps"], edge_status="Edge"),
    BGCRecord("BGC004", "NODE_4_length_60000_cov_31", 2, 500, 45000, 60000,
              products=["lanthipeptide"], edge_status="Interior"),
]

triage = triage_bgcs(bgcs, rggmci=None, scans=PoisonedScans())
triage_out = [dataclasses.asdict(t) for t in triage]

# corrupt-manifest case: package dir whose manifest.json is garbage bytes
tmp = Path(tempfile.mkdtemp(prefix="netcase_"))
pkg = tmp / "package"
pkg.mkdir()
(pkg / "manifest.json").write_bytes(b"\x00{not json!!")
(pkg / "SMOKE_2_inventory.csv").write_text("a,b\n1,2\n")
try:
    manifest = write_manifest(pkg)
    # strip volatile fields for comparison (paths/timestamps differ per tmpdir)
    stable = {k: v for k, v in manifest.items()
              if k not in {"package_dir", "generated", "generated_at", "written_at", "files"}}
    files = sorted(f["path"] for f in manifest.get("files", []) if isinstance(f, dict))
    manifest_case = {"stable_keys": sorted(manifest.keys()), "stable": stable, "file_paths": files}
except Exception as exc:  # noqa: BLE001 - comparison harness must capture, not die
    manifest_case = {"error": repr(exc)}

events = degradation.drain() if HAS_DEG else []
out.write_text(json.dumps({
    "engine_root": root.rsplit("/", 2)[-2] + "/" + root.rsplit("/", 1)[-1],
    "has_degradation_module": HAS_DEG,
    "triage": triage_out,
    "manifest_case": manifest_case,
    "breadcrumbs": events,
}, indent=2, sort_keys=True, default=str))
print(f"cases done: triage_records={len(triage_out)} breadcrumbs={len(events)} deg_module={HAS_DEG}")
