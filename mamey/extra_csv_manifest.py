"""Explicit, checked source-file lists for offline result replay."""

from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path
import csv
import glob
import hashlib
import io


def file_sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def csv_inputs(root, patterns=(), manifest=None):
    root = Path(root).resolve()
    if manifest and patterns:
        raise ValueError("use --extra-csv-list or --extra-csv, not both")
    expected = {}
    input_sha = ""
    if manifest:
        data = Path(manifest).read_bytes()
        input_sha = hashlib.sha256(data).hexdigest()
        reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")), delimiter="\t")
        if not {"path", "sha256", "bytes"} <= set(reader.fieldnames or []):
            raise ValueError(f"{manifest}: needs path, sha256, bytes columns")
        for row in reader:
            name = row["path"]
            if not name or Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError(f"{manifest}: expected root-relative path: {name!r}")
            if name in expected:
                raise ValueError(f"{manifest}: duplicate path: {name}")
            expected[name] = row
        names = sorted(expected)
    else:
        names = sorted({str(Path(p).relative_to(root)) for pattern in patterns
                        for p in glob.glob(str(root / pattern))})
    records, errors = [], []
    for name in names:
        path = root / name
        if not path.resolve().is_relative_to(root):
            errors.append(f"{name}: outside --root"); continue
        if not path.is_file():
            errors.append(f"{name}: missing file"); continue
        digest = file_sha256(path)
        size = path.stat().st_size
        if manifest:
            row = expected[name]
            if digest != row["sha256"].lower():
                errors.append(f"{name}: sha256 differs")
            if str(size) != row["bytes"]:
                errors.append(f"{name}: bytes differs")
        records.append({"path": name, "sha256": digest, "bytes": size})
    if errors:
        raise ValueError("extra CSV validation failed: " + "; ".join(errors))
    return records, input_sha


def write_csv_manifest(path, records):
    with Path(path).open("x", newline="", encoding="utf-8") as stream:
        writer = _SafeDictWriter(stream, fieldnames=["path", "sha256", "bytes"], delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(records)
    return file_sha256(path)
