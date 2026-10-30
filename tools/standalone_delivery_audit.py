#!/usr/bin/env python3
"""Read-only, manifest-bound static HTML/SVG/CSS delivery audit (candidate).

Does not execute JavaScript, fetch URLs, extract archives, render pages or infer
scientific validity. Existing handoff_gate and producer behavior checks retain
their ownership. Exit 0 means only PASS_STATIC_CONTRACT, never ship approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import stat
import sys
import zipfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

SCHEMA = "sapote.standalone_delivery.v1"
LIMITS = [
    "Only manifest-listed bytes and syntactically exposed HTML/SVG/CSS references are checked.",
    "JavaScript, embedded payloads, service workers and generated URLs require producer program checks.",
    "No network, browser rendering, visual inspection, scientific acceptance or release approval.",
    "Directory mode audits the declared subset, not unlisted neighboring files.",
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def member_path(value):
    """Require an unambiguous portable manifest/archive name, without I/O."""
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("invalid portable member name")
    p = PurePosixPath(value)
    if p.is_absolute() or any(v in ("", ".", "..") for v in value.split("/")) or re.match(r"^[A-Za-z]:", value):
        raise ValueError("member name must be canonical and relative: " + value)
    return value


class Folder:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("root is not a directory")

    def read(self, name):
        p = self.root
        for part in PurePosixPath(name).parts:
            p = p / part
            if p.is_symlink():
                raise ValueError("symlink is not admitted: " + name)
        p = p.resolve(strict=True)
        if not p.is_relative_to(self.root) or not p.is_file():
            raise ValueError("not a regular file inside root: " + name)
        return p.read_bytes()


class Archive:
    def __init__(self, path):
        self.z = zipfile.ZipFile(path)
        seen = set()
        for info in self.z.infolist():
            name = info.filename.rstrip("/") if info.is_dir() else info.filename
            member_path(name)
            if name in seen:
                raise ValueError("duplicate archive member: " + name)
            seen.add(name)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("archive symlink is not admitted: " + name)

    def read(self, name):
        info = self.z.getinfo(name)
        if info.is_dir():
            raise ValueError("archive member is a directory: " + name)
        return self.z.read(info)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs, self.ids, self.styles, self.scripts = [], set(), [], []
        self.active = None
        self.unsupported = []

    def handle_starttag(self, tag, attrs):
        if len({key for key, _value in attrs}) != len(attrs):
            self.unsupported.append("DUPLICATE_HTML_ATTRIBUTE_REQUIRES_REVIEW")
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and a.get("name"):
            self.ids.add(a["name"])
        if tag == "base":
            self.unsupported.append("HTML_BASE_REQUIRES_REVIEW")
        if a.get("srcset"):
            self.unsupported.append("SRCSET_REQUIRES_REVIEW")
        if a.get("srcdoc"):
            self.unsupported.append("SRCDOC_REQUIRES_REVIEW")
        if tag == "meta" and a.get("http-equiv", "").lower() == "refresh":
            self.unsupported.append("META_REFRESH_REQUIRES_REVIEW")
        for attr in ("src", "href", "xlink:href", "poster", "data"):
            if not a.get(attr):
                continue
            if attr == "data" and tag != "object":
                continue
            role = "navigation" if tag == "a" and attr == "href" else "runtime"
            self.refs.append((a[attr], role, tag + "[" + attr + "]"))
        if a.get("style"):
            self.styles.append(a["style"])
        if tag in ("style", "script"):
            self.active = tag

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        if self.active == "style":
            self.styles.append(data)
        elif self.active == "script":
            self.scripts.append(data)

    def handle_endtag(self, tag):
        if tag == self.active:
            self.active = None


def css_refs(text):
    # CSS escapes are not silently interpreted by this intentionally small parser.
    for m in re.finditer(r"url\(\s*(['\"]?)(.*?)\1\s*\)|@import\s+(['\"])(.*?)\3", re.sub(r"/\*.*?\*/", "", text, flags=re.S), re.I | re.S):
        yield m.group(2) if m.group(2) is not None else m.group(4)


def audit(manifest, store):
    errors, refs, checked = [], [], []
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")
    if manifest.get("schema") != SCHEMA:
        raise ValueError("unsupported manifest schema")
    files = {}
    for row in manifest.get("files", []):
        name = member_path(row["path"])
        if name in files:
            raise ValueError("duplicate manifest member: " + name)
        if not re.fullmatch(r"[a-f0-9]{64}", row.get("sha256", "")) or type(row.get("bytes")) is not int or row["bytes"] < 0:
            raise ValueError("invalid expected hash/byte count: " + name)
        files[name] = row
    if not files or not manifest.get("entrypoints"):
        raise ValueError("nonempty files and entrypoints are required")
    for name in manifest["entrypoints"]:
        member_path(name)
        if name not in files or not name.lower().endswith((".html", ".htm")):
            raise ValueError("entrypoint must name a manifest HTML file: " + name)
    optional = {}
    for row in manifest.get("optional_provenance", []):
        if not isinstance(row, dict) or not isinstance(row.get("url"), str):
            raise ValueError("optional provenance URL must be a string")
        key = (member_path(row["from"]), row["url"])
        if key[0] not in files or not isinstance(row.get("reason"), str) or not row["reason"].strip() or key in optional or urlsplit(key[1]).scheme not in ("", "https", "http", "file"):
            raise ValueError("invalid/duplicate optional provenance declaration")
        optional[key] = row["reason"]
    used_optional = set()
    payload, pages = {}, {}
    for name, row in files.items():
        try:
            b = store.read(name)
        except (OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
            errors.append({"code": "DECLARED_FILE_UNAVAILABLE", "path": name, "detail": str(exc)})
            continue
        payload[name] = b
        ok = len(b) == row["bytes"] and digest(b) == row["sha256"]
        checked.append({"path": name, "bytes": len(b), "sha256": digest(b), "state": "MATCH" if ok else "MISMATCH"})
        if not ok:
            errors.append({"code": "EXACT_BYTES_MISMATCH", "path": name})
        if name.lower().endswith((".html", ".htm", ".svg", ".xhtml")):
            try:
                text = b.decode("utf-8-sig", errors="strict")
                page = Page()
                page.feed(text)
                pages[name] = page
            except (UnicodeError, ValueError) as exc:
                errors.append({"code": "HTML_PARSE_ERROR", "path": name, "detail": str(exc)})

    def reference(name, url, role, context):
        url = url.strip()
        row = {"from": name, "url": url, "role": role, "context": context}
        key = (name, url)
        parts = urlsplit(url)
        if role == "navigation" and key in optional:
            used_optional.add(key)
            row.update(state="OPTIONAL_PROVENANCE_NOT_CHECKED", reason=optional[key])
        elif parts.scheme in ("data", "blob"):
            row["state"] = "INLINE_DATA" if parts.scheme == "data" else "PROGRAM_GENERATED_BLOB_REQUIRES_REVIEW"
        elif parts.scheme or parts.netloc:
            if role == "navigation" and parts.scheme in ("https", "http", "mailto", "tel"):
                row["state"] = "OPTIONAL_EXTERNAL_NAVIGATION_NOT_FETCHED"
            else:
                row["state"] = "EXTERNAL_RUNTIME_OR_NONPORTABLE_REFERENCE"
                errors.append({"code": row["state"], **row})
        else:
            p = unquote(parts.path)
            if "\\" in p or "\x00" in p or p.startswith("/") or re.match(r"^[A-Za-z]:", p):
                target = None
            else:
                target = posixpath.normpath(posixpath.join(posixpath.dirname(name), p)) if p else name
                if target == ".." or target.startswith("../"):
                    target = None
            row["resolved_member"] = target
            if target is None:
                row["state"] = "REFERENCE_ESCAPES_DELIVERY_ROOT"
            elif target not in files:
                row["state"] = "REFERENCE_NOT_IN_MANIFEST"
            elif target not in payload:
                row["state"] = "REFERENCE_FILE_UNAVAILABLE"
            elif parts.fragment and target in pages and unquote(parts.fragment) not in pages[target].ids:
                row["state"] = "MISSING_HTML_FRAGMENT"
            else:
                row["state"] = "RESOLVES_TO_BOUND_MEMBER"
            if row["state"] != "RESOLVES_TO_BOUND_MEMBER":
                errors.append({"code": row["state"], **row})
        refs.append(row)

    inline_count = 0
    hints = []
    for name, page in pages.items():
        for code in page.unsupported:
            errors.append({"code": code, "path": name})
        for url, role, context in page.refs:
            reference(name, url, role, context)
        for css in page.styles:
            for url in css_refs(css):
                if "\\" in url:
                    errors.append({"code": "CSS_ESCAPE_REQUIRES_REVIEW", "path": name})
                else:
                    reference(name, url, "runtime", "inline CSS")
        inline_count += len(page.scripts)
        text = "\n".join(page.scripts)
        found = sorted(set(re.findall(r"\b(?:fetch|XMLHttpRequest|WebSocket|Worker|importScripts|serviceWorker)\b", text)))
        if found:
            hints.append({"path": name, "lexical_hints_only": found})
    for name, b in payload.items():
        if name.lower().endswith(".css"):
            try:
                for url in css_refs(b.decode("utf-8-sig")):
                    if "\\" in url:
                        errors.append({"code": "CSS_ESCAPE_REQUIRES_REVIEW", "path": name})
                    else:
                        reference(name, url, "runtime", "CSS")
            except UnicodeError as exc:
                errors.append({"code": "CSS_DECODE_ERROR", "path": name, "detail": str(exc)})
    for key in optional.keys() - used_optional:
        errors.append({"code": "UNUSED_OPTIONAL_PROVENANCE_DECLARATION", "from": key[0], "url": key[1]})
    return {"schema": "sapote.standalone_delivery.receipt.v1", "status": "FAIL_STATIC_CONTRACT" if errors else "PASS_STATIC_CONTRACT",
            "manifest_sha256": digest(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()),
            "manifest_hash_scope": "canonical parsed JSON; CLI also records exact manifest file bytes",
            "files_checked": checked, "reference_counts": dict(Counter(r["state"] for r in refs)), "references": refs,
            "errors": errors, "inline_script_blocks": inline_count, "program_lexical_hints": hints,
            "javascript_execution": "NOT_PERFORMED", "browser_visual_inspection": "NOT_PERFORMED",
            "scientific_validation": "NOT_PERFORMED", "release_authority": "NOT_GRANTED", "limits": LIMITS}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--root", type=Path)
    source.add_argument("--zip", type=Path)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    a = p.parse_args(argv)
    destination = a.receipt.resolve()
    if a.receipt.exists() or a.receipt.is_symlink() or destination == a.manifest.resolve() or (a.zip and destination == a.zip.resolve()) or (a.root and destination.is_relative_to(a.root.resolve())):
        p.error("receipt must be a new path outside the audited root and distinct from inputs; existing paths are refused")
    manifest_bytes = b""
    try:
        manifest_bytes = a.manifest.read_bytes()
        store = Archive(a.zip) if a.zip else Folder(a.root)
        result = audit(json.loads(manifest_bytes), store)
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        result = {"status": "FAIL_INPUT_CONTRACT", "errors": [{"code": "INPUT_CONTRACT_ERROR", "detail": str(exc)}], "limits": LIMITS}
    if "store" in locals() and isinstance(store, Archive):
        store.z.close()
    result["manifest_file_sha256"] = digest(manifest_bytes)
    result["source"] = str((a.zip or a.root).resolve())
    # The receipt destination is explicit; never default to writing into inputs.
    try:
        with a.receipt.open("x", encoding="utf-8") as receipt:
            receipt.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    except FileExistsError:
        sys.stderr.write("RECEIPT_REFUSED: receipt already exists; refusing to replace evidence\n")
        return 2
    print(json.dumps({"status": result["status"], "errors": len(result["errors"]), "receipt": str(a.receipt)}, sort_keys=True))
    return 0 if result["status"] == "PASS_STATIC_CONTRACT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
