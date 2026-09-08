#!/usr/bin/env python3
"""Prove that registry-backed source scans match the literal fallback.

This is a candidate-only B2 receipt tool.  It imports the scanner twice for
each supplied antiSMASH ZIP: once with the normal registry overlay and once
with ``MAMEY_DISABLE_REGISTRY_DETECTOR=1``.  It hashes the canonical JSON
serialization of ``SourceScanBundle`` and writes only a report if requested;
it never alters an input archive or package.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import contextlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _serialize(value: Any) -> Any:
    if hasattr(value, "__dict__"):
        return {key: _serialize(item) for key, item in vars(value).items()}
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value


def _fresh_scanner(disable_registry: bool):
    """Reimport just the modules whose import-time state affects this proof."""
    package = sys.modules.get("mamey")
    for module_name in ("mamey.source_scans", "mamey.registry_detector", "mamey.registry_schema"):
        sys.modules.pop(module_name, None)
        if package is not None:
            # v9.7.407 ratchet paydown: an explicit suppress states the intent (the submodule
            # attribute may simply not be bound yet) instead of an opaque try/except/pass.
            with contextlib.suppress(AttributeError):
                delattr(package, module_name.rsplit(".", 1)[1])
    if disable_registry:
        os.environ["MAMEY_DISABLE_REGISTRY_DETECTOR"] = "1"
    else:
        os.environ.pop("MAMEY_DISABLE_REGISTRY_DETECTOR", None)
    from mamey import source_scans

    return source_scans


def _run_once(input_zip: pathlib.Path, *, disable_registry: bool) -> tuple[bool, bytes]:
    scanner = _fresh_scanner(disable_registry)
    from mamey import parsers

    bgcs = parsers.parse_bgcs_from_zip(str(input_zip))
    cds = parsers.extract_cds_features(str(input_zip))
    contigs = parsers.extract_contig_sequences(str(input_zip))
    domains = parsers.extract_domain_features(str(input_zip))
    bundle = scanner.run_source_scans(bgcs, cds, contigs, domains)
    rendered = json.dumps(_serialize(bundle), sort_keys=True, separators=(",", ":"), default=str)
    return bool(scanner.REGISTRY_DETECTOR_ACTIVE), rendered.encode("utf-8")


def discover_inputs() -> list[pathlib.Path]:
    roots = (ROOT / "examples", ROOT / "tests" / "fixtures")
    return sorted({path for base in roots if base.exists() for path in base.rglob("*.zip")})


def probe(input_zip: pathlib.Path) -> dict[str, Any]:
    old_disable = os.environ.get("MAMEY_DISABLE_REGISTRY_DETECTOR")
    try:
        active, active_bytes = _run_once(input_zip, disable_registry=False)
        fallback, fallback_bytes = _run_once(input_zip, disable_registry=True)
        return {
            "input": str(input_zip.relative_to(ROOT)),
            "status": "PASS" if active and not fallback and active_bytes == fallback_bytes else "DIVERGED",
            "registry_active": active,
            "fallback_active": fallback,
            "registry_sha256": hashlib.sha256(active_bytes).hexdigest(),
            "fallback_sha256": hashlib.sha256(fallback_bytes).hexdigest(),
            "registry_bytes": len(active_bytes),
            "fallback_bytes": len(fallback_bytes),
        }
    except Exception as exc:  # input discovery includes test-only malformed ZIPs
        return {"input": str(input_zip.relative_to(ROOT)), "status": "INPUT_UNSUPPORTED", "error": f"{type(exc).__name__}: {exc}"}
    finally:
        if old_disable is None:
            os.environ.pop("MAMEY_DISABLE_REGISTRY_DETECTOR", None)
        else:
            os.environ["MAMEY_DISABLE_REGISTRY_DETECTOR"] = old_disable
        _fresh_scanner(disable_registry=old_disable == "1")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=pathlib.Path, help="antiSMASH ZIP to test; repeatable")
    parser.add_argument("--output", type=pathlib.Path, help="write the JSON receipt to this path")
    args = parser.parse_args(argv)
    inputs = args.input or discover_inputs()
    results = [probe(path.resolve()) for path in inputs]
    report = {"tool": "scan_registry_parity", "schema_version": 1, "results": results}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for result in results:
        print("{status}\t{input}".format(**result))
    return 0 if results and all(row["status"] == "PASS" for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
