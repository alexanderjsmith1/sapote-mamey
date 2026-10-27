#!/usr/bin/env python3
"""Read-only table cross-reference accounting across explicitly scoped chapter parts.

No source edits, field refresh, caption renumbering, biology, or figure validation.
The manifest supplies sources, chapter scopes, optional DOCX mirrors and a named
native paper_reference_audit.py reader. Exact label keys retain type and scope.
"""
import argparse
import collections
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # run as tools/<name>.py from the bundle root
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

TOKEN = r"S?\d+(?:\.(?:[A-Za-z]?\d+[a-z]?))*"
BOUNDARY = r"(?![A-Za-z0-9]|\.[A-Za-z0-9])"
TABLE = re.compile(r"\bTables?\s+(" + TOKEN + r")" + BOUNDARY)
RAW_TABLE = re.compile(r"\bTables?\s+(S?\d[0-9A-Za-z]*(?:\.[0-9A-Za-z]+)*)")
CONTINUE = re.compile(r"\s*(,\s*(?:and\s+)?|and\s+|[–-]\s*)(" + TOKEN + r")" + BOUNDARY)
CAPTION = re.compile(r"^\s*(?:#{1,6}\s+)?Table\s+(" + TOKEN + r")[.:](?:\s|$)")
DATA = re.compile(r"\bData\s+(S?\d+\.[A-Za-z]+)\b")
SHEET = re.compile(r"\bsheets?\s+(S?\d+\.[A-Za-z]\d+)\b", re.I)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""): h.update(b)
    return h.hexdigest()


def visible_md(text):
    # Keep original source line numbers while removing non-reader evidence notes.
    text = re.sub(r"<!--[\s\S]*?-->", lambda m: re.sub(r"[^\n]", " ", m[0]), text)
    rows, fence = [], None
    for number, line in enumerate(text.splitlines(), 1):
        f = re.match(r"^\s*(`{3,}|~{3,})", line)
        if f:
            if fence is None: fence = f[1][0]
            elif fence == f[1][0]: fence = None
            continue
        if fence: continue
        line = re.sub(r"`[^`]*`", "", line)
        line = re.sub(r"\]\([^)]*\)", "]", line)
        line = line.replace("**", "").replace("__", "")
        if line.strip(): rows.append({"location": f"line:{number}", "text": line})
    return rows


def range_labels(first, last):
    a, b = re.fullmatch(r"(.*?)(\d+)", first), re.fullmatch(r"(.*?)(\d+)", last)
    if not a or not b or a[1] != b[1]: raise ValueError("mixed or nonnumeric range")
    start, stop = int(a[2]), int(b[2])
    if stop < start or stop - start > 199: raise ValueError("descending or oversized range")
    width = len(a[2]) if a[2].startswith("0") and len(a[2]) > 1 else 0
    if ((width and len(b[2]) != width)
            or (not width and b[2].startswith("0") and len(b[2]) > 1)):
        raise ValueError("inconsistent zero-padded range")
    return [a[1] + str(i).zfill(width) for i in range(start, stop + 1)]


def scan_rows(rows, document_id, scope):
    events, holds = [], []
    for row in rows:
        text, location = row["text"], row["location"]
        cap = CAPTION.match(text)
        for raw in RAW_TABLE.finditer(text):
            if not re.fullmatch(TOKEN, raw[1]):
                holds.append({"document_id": document_id, "location": location, "code": "TABLE_LABEL_PARSE_HOLD", "detail": raw[1]})
        for hit in TABLE.finditer(text):
            labels, pos = [hit[1]], hit.end()
            while True:
                nxt = CONTINUE.match(text, pos)
                if not nxt: break
                if nxt[1].strip().startswith(("-", "–")):
                    try: labels[-1:] = range_labels(labels[-1], nxt[2])
                    except ValueError as e:
                        holds.append({"document_id": document_id, "location": location, "code": "RANGE_PARSE_HOLD", "detail": str(e)})
                else: labels.append(nxt[2])
                pos = nxt.end()
            for i, label in enumerate(labels):
                events.append({"document_id": document_id, "scope": scope, "location": location,
                               "kind": "Table", "label": label,
                               "role": "definition" if cap and cap.start() <= hit.start() < cap.end() and i == 0 else "citation"})
        for hit in DATA.finditer(text):
            events.append({"document_id": document_id, "scope": scope, "location": location, "kind": "Data", "label": hit[1], "role": "resource_citation"})
        for hit in SHEET.finditer(text):
            data_ids = sorted(set(DATA.findall(text)))
            events.append({"document_id": document_id, "scope": scope, "location": location, "kind": "Sheet", "label": hit[1], "role": "sheet_citation", "data_ids": data_ids})
    return events, holds


def resolve(events, resources=None):
    resources = resources or {}
    defs = collections.defaultdict(list)
    for e in events:
        if e["role"] == "definition": defs[(e["scope"], e["kind"], e["label"])].append(e)
    results = []
    for e in events:
        row = dict(e)
        if e["kind"] == "Table":
            targets = defs[(e["scope"], "Table", e["label"])]
            if len(targets) > 1: status = "DUPLICATE_DEFINITION_HOLD"
            elif targets: status = "DEFINED" if e["role"] == "definition" else "RESOLVED"
            elif "." not in e["label"]: status = "UNSCOPED_LABEL_HOLD"
            else: status = "UNRESOLVED_IN_SUPPLIED_SCOPE"
            row["targets"] = [{k: t[k] for k in ("document_id", "location")} for t in targets]
        elif e["kind"] == "Data":
            status = "RESOURCE_BOUND" if (e["scope"], e["label"]) in resources else "RESOURCE_NOT_SUPPLIED_HOLD"
        else:
            data_ids = e.get("data_ids", [])
            if len(data_ids) != 1: status = "SHEET_RESOURCE_SCOPE_HOLD"
            elif (e["scope"], data_ids[0]) not in resources: status = "RESOURCE_NOT_SUPPLIED_HOLD"
            elif e["label"] not in resources[(e["scope"], data_ids[0])]: status = "SHEET_NOT_FOUND_HOLD"
            else: status = "SHEET_NAME_BOUND"
        row["status"] = status
        results.append(row)
    return results


def workbook_sheets(path):
    with zipfile.ZipFile(path) as z:
        if z.namelist().count("xl/workbook.xml") != 1: raise ValueError("ambiguous/missing workbook XML")
        info = z.getinfo("xl/workbook.xml")
        if info.file_size > 2 * 1024 * 1024: raise ValueError("workbook metadata too large")
        raw = z.read(info)
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper(): raise ValueError("DTD/entity unsupported")
    root = ET.fromstring(raw)
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    names = [x.get("name", "") for x in root.findall(ns + "sheets/" + ns + "sheet")]
    if not names or len(names) != len(set(names)): raise ValueError("empty/duplicate workbook sheet names")
    return names, hashlib.sha256(raw).hexdigest()


def audit_manifest(manifest):
    bindings, events, holds, mirrors = [], [], [], []
    owner = None
    if manifest.get("docx_reader"):
        path = Path(manifest["docx_reader"])
        spec = importlib.util.spec_from_file_location("native_paper_reference_reader", path)
        owner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(owner)
        bindings.append({"role": "native_DOCX_reader", "path": str(path.resolve()), "sha256": sha(path), "bytes": path.stat().st_size})
    for doc in manifest["documents"]:
        path = Path(doc["path"])
        source_bytes = path.read_bytes()
        source_hash = hashlib.sha256(source_bytes).hexdigest()
        rows = visible_md(source_bytes.decode("utf-8"))
        current, found = scan_rows(rows, doc["id"], doc["scope"])
        events.extend(current); holds.extend(found)
        bindings.append({"role": "primary_markdown", "document_id": doc["id"], "path": str(path.resolve()), "sha256": source_hash, "bytes": len(source_bytes)})
        for mirror in doc.get("docx_mirrors", []):
            if owner is None: raise ValueError("DOCX mirror needs explicit native reader")
            paras, native_holds, receipt = owner.read_docx(Path(mirror), doc["scope"])
            seen, parsed_holds = scan_rows(paras, doc["id"], doc["scope"])
            # Full token multisets and definition roles must survive compilation;
            # normal typography and line wrapping do not affect this comparison.
            key = lambda e: (e["kind"], e["label"], e["role"])
            expected, actual = collections.Counter(map(key, current)), collections.Counter(map(key, seen))
            mirrors.append({"document_id": doc["id"], "path": str(Path(mirror).resolve()), "sha256": receipt["sha256"],
                            "xml_parts_sha256": receipt["xml_parts_sha256"], "status": "TABLE_TOKEN_MULTISET_MATCH" if expected == actual else "TABLE_TOKEN_MIRROR_HOLD",
                            "missing_tokens": [list(x) + [n] for x, n in (expected - actual).items()],
                            "extra_tokens": [list(x) + [n] for x, n in (actual - expected).items()],
                            "native_read_holds": native_holds, "parser_holds": parsed_holds,
                            "selected_table_locations": [{k: e[k] for k in ("location", "kind", "label", "role")} for e in seen if e["label"] == "S5.7"]})
            bindings.append({"role": "DOCX_mirror", "document_id": doc["id"], "path": str(Path(mirror).resolve()), "sha256": receipt["sha256"], "bytes": Path(mirror).stat().st_size})
        if sha(path) != source_hash: raise ValueError("primary source changed during read")
    resources, metadata = {}, []
    for resource in manifest.get("workbooks", []):
        path = Path(resource["path"])
        before = sha(path)
        names, xml_hash = workbook_sheets(path)
        if sha(path) != before: raise ValueError("workbook changed during read")
        resources[(resource["scope"], resource["data_id"])] = names
        metadata.append({**resource, "sha256": before, "metadata_sha256": xml_hash, "sheet_names": names})
        bindings.append({"role": "workbook_metadata_source", "path": str(path.resolve()), "sha256": before, "bytes": path.stat().st_size})
    results = resolve(events, resources)
    counts = collections.Counter(x["status"] for x in results)
    return {"schema": "chapter-table-crossrefs-v1", "status": "ACCOUNTED_WITH_HOLDS" if holds or any("HOLD" in x or "UNRESOLVED" in x for x in counts) or any(x["status"].endswith("HOLD") or x["native_read_holds"] or x["parser_holds"] for x in mirrors) else "ACCOUNTED",
            "documents": len(manifest["documents"]), "events": results, "event_status_counts": counts, "parser_holds": holds,
            "DOCX_mirrors": mirrors, "workbooks": metadata, "source_bindings": bindings,
            "limits": "Literal table labels/data resource/sheet names only in explicit corpus. Caption definitions do not prove a populated table. DOCX cached text is not refreshed/rendered. Native reader and mirror-parser holds retain ACCOUNTED_WITH_HOLDS even when token multisets match. Figures, sections, references, biology and workbook cell content not validated."}


def safe(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    out = Path(a.out)
    if out.exists(): p.error("fresh output directory required; existing receipts preserved")
    manifest = json.loads(Path(a.manifest).read_text())
    result = audit_manifest(manifest)
    result["manifest_sha256"] = sha(a.manifest)
    out.mkdir(parents=True)
    (out / "CROSSREF_AUDIT.json").write_text(json.dumps(result, indent=2) + "\n")
    fields = ["document_id", "scope", "location", "kind", "label", "role", "status", "targets"]
    with (out / "CROSSREF_EVENTS.tsv").open("w", newline="") as f:
        w = _SafeDictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n"); w.writeheader()
        for row in result["events"]: w.writerow({k: safe(json.dumps(row[k]) if isinstance(row.get(k), list) else row.get(k, "")) for k in fields})
    print(json.dumps({k: result[k] for k in ("status", "documents", "event_status_counts")}))


if __name__ == "__main__": main()
