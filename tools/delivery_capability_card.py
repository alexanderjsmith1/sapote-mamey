#!/usr/bin/env python3
"""Summarize declared browser requirements and hash-bound check receipts.

Read-only inputs; no browser/network execution, biological analysis or compatibility
inference. A card reports producer assertions and binding states, never ship approval.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import html
import json
import os
from pathlib import Path
import re
import tempfile

KINDS = ("static_dependencies", "data_syntax", "program_behavior", "browser_compatibility", "visual_review")
ADAPTERS = {"delivery_check_v1", "tb03_static", "locus_data_syntax", "protein_data_syntax", "unbound_legacy", "report_visual"}
HASH = re.compile(r"^[a-f0-9]{64}$")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def path_at(root, value):
    return (root / value).resolve()


def pinned_json(root, declaration):
    p = path_at(root, declaration["path"])
    row = {"path": str(p), "expected_sha256": declaration.get("sha256")}
    if not p.is_file():
        return None, {**row, "state": "RECEIPT_MISSING"}
    receipt_bytes = p.read_bytes()
    actual = hashlib.sha256(receipt_bytes).hexdigest()
    row["actual_sha256"] = actual
    if not HASH.fullmatch(str(declaration.get("sha256", ""))):
        return None, {**row, "state": "RECEIPT_REVISION_NOT_PINNED"}
    if actual != declaration["sha256"]:
        return None, {**row, "state": "RECEIPT_HASH_MISMATCH"}
    try:
        data = json.loads(receipt_bytes.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("receipt is not an object")
    except (ValueError, UnicodeError) as exc:
        return None, {**row, "state": "RECEIPT_INVALID", "detail": str(exc)}
    return data, row


def check_receipt(root, spec, artifact):
    data, row = pinned_json(root, spec)
    row.update(kind=spec["kind"], adapter=spec["adapter"])
    if data is None:
        return row
    row["producer_claim_only"] = True
    row["recorded_at"] = data.get("checked_at", data.get("when_UTC", "NOT_RECORDED"))
    row["scope"] = data.get("scope", data.get("limits", "NOT_RECORDED"))
    adapter, kind = spec["adapter"], spec["kind"]
    bound_hash, bound_bytes, result = None, None, None
    if adapter == "unbound_legacy":
        row["state"] = "RECEIPT_UNBOUND"
        row["detail"] = "Retained producer receipt has no admitted exact-deliverable binding adapter. Its existence is not a check of these bytes."
        return row
    if adapter == "delivery_check_v1":
        if data.get("schema") != "sapote.delivery_check.v1" or data.get("kind") != kind or not data.get("method") or not data.get("scope"):
            return {**row, "state": "RECEIPT_INVALID", "detail": "schema, kind, method and scope are required"}
        target = data.get("artifact", {})
        if not isinstance(target, dict) or type(target.get("bytes")) is not int or target["bytes"] < 0:
            return {**row, "state": "RECEIPT_INVALID", "detail": "native receipt artifact needs a nonnegative integer byte count"}
        bound_hash, bound_bytes = target.get("sha256"), target.get("bytes")
        result = data.get("result")
        if result not in {"PASS", "FAIL", "NOT_PERFORMED", "HELD"}:
            return {**row, "state": "RECEIPT_INVALID", "detail": "unknown result"}
        row["method"] = data["method"]
        row["environment"] = data.get("environment", {})
        if kind == "browser_compatibility" and result == "PASS":
            env = data.get("environment", {})
            if not all(isinstance(env.get(k), str) and env[k].strip() for k in ("browser", "browser_version", "os")) or not data.get("checked_at"):
                return {**row, "state": "BROWSER_RECEIPT_ENVIRONMENT_UNSPECIFIED", "detail": "A browser pass needs dated browser/version/OS scope."}
            try:
                recorded = datetime.fromisoformat(data["checked_at"].replace("Z", "+00:00"))
                if recorded.tzinfo is None:
                    raise ValueError("timezone is missing")
            except (ValueError, AttributeError):
                return {**row, "state": "BROWSER_RECEIPT_ENVIRONMENT_UNSPECIFIED", "detail": "checked_at must be an ISO timestamp with timezone."}
    elif adapter == "tb03_static":
        if kind != "static_dependencies" or data.get("schema") != "sapote.standalone_delivery.receipt.v1":
            return {**row, "state": "RECEIPT_SCOPE_MISMATCH"}
        rows = [r for r in data.get("files_checked", []) if r.get("path") == spec.get("member")]
        if len(rows) != 1:
            return {**row, "state": "RECEIPT_UNBOUND", "detail": "Exactly one configured member must be bound."}
        bound_hash, bound_bytes = rows[0].get("sha256"), rows[0].get("bytes")
        row["scope"] = data.get("limits", [])
        result = "PASS" if data.get("status") == "PASS_STATIC_CONTRACT" and rows[0].get("state") == "MATCH" and not data.get("errors") else "FAIL"
    elif adapter == "locus_data_syntax":
        if kind != "data_syntax" or data.get("status") != "PASS_DATA_BINDINGS_AND_JS_SYNTAX":
            return {**row, "state": "RECEIPT_SCOPE_MISMATCH"}
        bound_hash, bound_bytes = data.get("HTML_sha256"), data.get("standalone_HTML_bytes")
        result = "PASS" if not data.get("errors") else "FAIL"
    elif adapter == "protein_data_syntax":
        if kind != "data_syntax" or data.get("status") != "PASS_DATA_PRESERVATION_AND_JS_SYNTAX":
            return {**row, "state": "RECEIPT_SCOPE_MISMATCH"}
        bound_hash = data.get("output_viewer_sha256")
        result = "PASS" if data.get("point_arrays_unchanged") is True else "FAIL"
    elif adapter == "report_visual":
        if kind != "visual_review" or data.get("status") != "RENDERED_PAGES_INSPECTED":
            return {**row, "state": "RECEIPT_SCOPE_MISMATCH"}
        matches = [r for r in data.get("reviewed_PDFs", []) if r.get("sha256") == artifact.get("actual_sha256")]
        if len(matches) != 1:
            return {**row, "state": "RECEIPT_SCOPE_MISMATCH", "detail": "Visual receipt binds other PDF bytes, not this target."}
        bound_hash = matches[0]["sha256"]
        row["scope"] = data.get("review", "NOT_RECORDED")
        result = "PASS"
    if adapter in {"tb03_static", "locus_data_syntax"} and (type(bound_bytes) is not int or bound_bytes < 0):
        return {**row, "state": "RECEIPT_INVALID", "detail": "This adapter requires a nonnegative integer artifact byte count."}
    if not HASH.fullmatch(str(bound_hash or "")):
        return {**row, "state": "RECEIPT_UNBOUND"}
    row.update(receipt_artifact_sha256=bound_hash, receipt_artifact_bytes=bound_bytes)
    if artifact["state"] != "EXACT_CONFIGURED_ARTIFACT":
        return {**row, "state": "ARTIFACT_BINDING_HOLD"}
    if bound_hash != artifact["actual_sha256"] or (bound_bytes is not None and bound_bytes != artifact["actual_bytes"]):
        return {**row, "state": "RECEIPT_STALE_FOR_TARGET"}
    return {**row, "state": "BOUND_REPORTED_" + result, "reported_result": result}


def build(config, root):
    if config.get("schema") != "sapote.delivery_capability_card.v1":
        raise ValueError("unsupported config schema")
    source = config["artifact"]
    if not HASH.fullmatch(str(source.get("sha256", ""))) or type(source.get("bytes")) is not int or source["bytes"] < 0:
        raise ValueError("artifact needs exact SHA-256 and nonnegative byte count")
    p = path_at(root, source["path"])
    artifact = {"path": str(p), "expected_sha256": source["sha256"], "expected_bytes": source["bytes"]}
    if not p.is_file():
        artifact["state"] = "ARTIFACT_MISSING"
    else:
        artifact.update(actual_sha256=sha(p), actual_bytes=p.stat().st_size)
        artifact["state"] = "EXACT_CONFIGURED_ARTIFACT" if artifact["actual_sha256"] == source["sha256"] and artifact["actual_bytes"] == source["bytes"] else "ARTIFACT_CHANGED"
    capabilities, names = [], set()
    for declaration in config.get("declared_capabilities", []):
        name, requirement = declaration["name"], declaration["requirement"]
        if not isinstance(name, str) or not name.strip() or name in names or requirement not in {"REQUIRED", "OPTIONAL", "NOT_DECLARED"}:
            raise ValueError("invalid or duplicate capability declaration")
        names.add(name)
        row = {"name": name, "requirement": requirement, "measured_compatibility": "NOT_MEASURED_BY_THIS_CARD"}
        if requirement == "NOT_DECLARED":
            row.update(state="NOT_DECLARED", reason=declaration.get("reason", "No producer declaration supplied."))
        else:
            evidence = declaration.get("evidence", {})
            if not evidence.get("path") or not HASH.fullmatch(str(evidence.get("sha256", ""))) or not evidence.get("excerpt"):
                raise ValueError("declared requirement needs source path, SHA-256 and exact excerpt")
            q = path_at(root, evidence["path"])
            row["source"] = {**evidence, "path": str(q)}
            if not q.is_file():
                row["state"] = "DECLARATION_SOURCE_MISSING"
            else:
                raw = q.read_bytes()
                if hashlib.sha256(raw).hexdigest() != evidence["sha256"]:
                    row["state"] = "DECLARATION_SOURCE_CHANGED"
                elif evidence["excerpt"] not in raw.decode("utf-8"):
                    row["state"] = "DECLARATION_EXCERPT_NOT_FOUND"
                else:
                    row["state"] = "SOURCE_BOUND_DECLARATION_UNMEASURED"
        capabilities.append(row)
    checks, seen = [], set()
    for spec in config.get("checks", []):
        if spec.get("kind") not in KINDS or spec.get("adapter") not in ADAPTERS or spec["kind"] in seen:
            raise ValueError("unsupported/duplicate check kind or adapter")
        seen.add(spec["kind"])
        checks.append(check_receipt(root, spec, artifact))
    checks += [{"kind": kind, "state": "NOT_PERFORMED", "detail": "No receipt selected in this config."} for kind in KINDS if kind not in seen]
    holds = [r["kind"] + ": " + r["state"] for r in checks if r["state"] != "BOUND_REPORTED_PASS"]
    holds += [r["name"] + ": " + r["state"] for r in capabilities if r["state"] not in {"SOURCE_BOUND_DECLARATION_UNMEASURED", "NOT_DECLARED"}]
    if artifact["state"] != "EXACT_CONFIGURED_ARTIFACT":
        holds.insert(0, artifact["state"])
    return {"schema": "sapote.delivery_capability_card.result.v1", "status": "EVIDENCE_CARD_WITH_HOLDS" if holds else "EVIDENCE_CARD_BOUND_PRODUCER_REPORTS",
            "artifact": artifact, "declared_capabilities": capabilities, "checks": checks, "holds": holds,
            "compatibility_claim": "No compatibility measurement is performed by this card. A dated bound producer browser receipt applies only to its stated environment.",
            "freshness_scope": "Exact-byte content binding, not a time-to-live or proof of compatibility in a changed browser/environment.",
            "authority": "Receipt hashes bind assertions to bytes; they do not authenticate a reviewer or grant scientific, thesis, merge or release acceptance."}


def render(card):
    esc = lambda x: html.escape(str(x), quote=True)
    artifact = card["artifact"]
    capabilities = "".join("<tr><td>" + esc(r["name"]) + "</td><td>" + esc(r["requirement"]) + "</td><td>" + esc(r["state"]) + "</td></tr>" for r in card["declared_capabilities"])
    checks = "".join("<tr><td>" + esc(r["kind"]) + "</td><td>" + esc(r["state"]) + "</td><td>" + esc(r.get("scope", r.get("detail", ""))) + "</td></tr>" for r in card["checks"])
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Delivery capability card</title><style>body{font:16px system-ui,sans-serif;margin:2rem auto;padding:0 1rem;max-width:1000px;line-height:1.5}table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{border:1px solid #777;padding:.5rem;text-align:left;vertical-align:top;overflow-wrap:anywhere}code,pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><body><h1>Delivery capability card</h1><p>'+esc(card["status"])+'</p><p>Artifact: <code>'+esc(artifact["path"])+'</code><br>Current SHA-256: <code>'+esc(artifact.get("actual_sha256", "UNAVAILABLE"))+'</code><br>Binding: '+esc(artifact["state"])+'</p><h2>Producer declarations</h2><p>These are requirements, not measured browser compatibility.</p><table><tr><th>Capability</th><th>Requirement</th><th>Declaration evidence</th></tr>'+capabilities+'</table><h2>Separate check states</h2><table><tr><th>Check</th><th>Binding and reported result</th><th>Scope or hold</th></tr>'+checks+'</table><p>'+esc(card["compatibility_claim"])+'</p><p>'+esc(card["freshness_scope"])+'</p><p>'+esc(card["authority"])+'</p></body></html>\n'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--json-out", type=Path, required=True)
    p.add_argument("--html-out", type=Path)
    p.add_argument("--replace-candidate", action="store_true")
    a = p.parse_args(argv)
    config_bytes = a.config.read_bytes()
    config = json.loads(config_bytes)
    root = a.config.resolve().parent
    inputs = {a.config.resolve(), path_at(root, config["artifact"]["path"])}
    inputs |= {path_at(root, row["path"]) for row in config.get("checks", [])}
    inputs |= {path_at(root, row["evidence"]["path"]) for row in config.get("declared_capabilities", []) if row.get("evidence", {}).get("path")}
    outputs = [a.json_out] + ([a.html_out] if a.html_out else [])
    if len({q.resolve() for q in outputs}) != len(outputs) or any(q.is_symlink() or q.resolve() in inputs for q in outputs):
        p.error("outputs must be distinct, non-symlink, derived files, separate from every input")
    card = build(config, root)
    card["config_file_sha256"] = hashlib.sha256(config_bytes).hexdigest()
    texts = [json.dumps(card, ensure_ascii=False, indent=2) + "\n"] + ([render(card)] if a.html_out else [])
    for q, text in zip(outputs, texts):
        if q.exists() and q.read_text(encoding="utf-8") != text and not a.replace_candidate:
            p.error("changed candidate output exists; preserve it or select --replace-candidate: " + str(q))
    # Preflight both outputs before any write. Each replacement is atomic;
    # the two outputs are not a transactional pair after interruption.
    for q, text in zip(outputs, texts):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=q.parent, delete=False) as f:
            f.write(text)
            temp = Path(f.name)
        os.replace(temp, q)
    print(json.dumps({"status": card["status"], "holds": len(card["holds"]), "artifact": card["artifact"]["state"]}))
    return 1 if card["artifact"]["state"] != "EXACT_CONFIGURED_ARTIFACT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
