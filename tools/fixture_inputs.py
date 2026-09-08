"""Content-preserving preparation of the one hash-bound synthetic test archive.

This is test-input preparation, never a user-archive admission path. Production
compression limits remain unchanged; the original archive remains a refusal control.
"""
import copy
import hashlib
import io
from pathlib import Path
import re
import zipfile

_SINGLE_CONTIG_SHA256 = "bd6422d403d0b019c14f0d8c13dbfe2898b7e5afb0a4d43bf58fb083fdc9fde8"
SYNTHETIC_FULL_CONTIG_ID = "SYNTHETIC_CONTIG_000001"

_FULL_LOCUS_POLICY = "single_contig_full_locus_runtime_v1"
_FULL_LOCUS_MEMBER_MAPPING = {
    "syn/NODE_1.region001.gbk": "syn/SYNTHETIC_CONTIG_000001.region001.gbk",
    "syn/NODE_1.fasta": "syn/SYNTHETIC_CONTIG_000001.fasta",
    "syn/NODE_1.region002.gbk": "syn/SYNTHETIC_CONTIG_000001.region002.gbk",
    "syn/NODE_1.region003.gbk": "syn/SYNTHETIC_CONTIG_000001.region003.gbk",
    "syn/knownclusterblast/NODE_1_c2.txt": (
        "syn/knownclusterblast/SYNTHETIC_CONTIG_000001_c2.txt"
    ),
    "syn/knownclusterblast/NODE_1_c1.txt": (
        "syn/knownclusterblast/SYNTHETIC_CONTIG_000001_c1.txt"
    ),
    "syn/knownclusterblast/NODE_1_c3.txt": (
        "syn/knownclusterblast/SYNTHETIC_CONTIG_000001_c3.txt"
    ),
}

def prepare_single_contig_fixture(source: Path, target: Path) -> dict:
    """Store repetitive FASTA uncompressed; preserve all members and source bytes."""
    source = Path(source)
    target = Path(target)
    source_bytes = source.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    if source_hash != _SINGLE_CONTIG_SHA256:
        raise ValueError("synthetic fixture source hash is not the governed input")
    member_hashes = {}
    with zipfile.ZipFile(io.BytesIO(source_bytes)) as zin:
        infos = zin.infolist()
        if len({info.filename for info in infos}) != len(infos):
            raise ValueError("synthetic fixture has duplicate member names")
        with zipfile.ZipFile(target, "x") as zout:
            for info in infos:
                content = zin.read(info)
                admitted = copy.copy(info)
                if admitted.filename.lower().endswith((".fa", ".fna", ".fasta", ".fas")):
                    admitted.compress_type = zipfile.ZIP_STORED
                zout.writestr(admitted, content)
                member_hashes[info.filename] = hashlib.sha256(content).hexdigest()
    with zipfile.ZipFile(target) as zout:
        observed = {info.filename: hashlib.sha256(zout.read(info)).hexdigest()
                    for info in zout.infolist()}
        if observed != member_hashes:
            raise ValueError("synthetic fixture member parity failed")
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_hash:
        raise ValueError("synthetic fixture source changed during preparation")
    return {"policy": "single_contig_stored_fasta_v1", "source_sha256": source_hash,
            "prepared_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "member_sha256": member_hashes}


def _replace_anchored_once(text: str, pattern: str, replacement, label: str) -> str:
    transformed, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"full-locus synthetic fixture expected one {label}, found {count}")
    return transformed


def _transform_region_gbk(content: bytes) -> bytes:
    text = content.decode("ascii")

    def locus_line(match: re.Match) -> str:
        length = int(match.group(1))
        return f"LOCUS       {SYNTHETIC_FULL_CONTIG_ID:<24}{length:>11} bp{match.group(2)}"

    text = _replace_anchored_once(
        text,
        r"^LOCUS\s+NODE_1\s+(\d+)\s+bp(.*)$",
        locus_line,
        "NODE_1 LOCUS line",
    )
    text = _replace_anchored_once(
        text,
        r"^ACCESSION\s+NODE_1\s*$",
        f"ACCESSION   {SYNTHETIC_FULL_CONTIG_ID}",
        "NODE_1 ACCESSION line",
    )
    text = _replace_anchored_once(
        text,
        r"^VERSION\s+NODE_1\s*$",
        f"VERSION     {SYNTHETIC_FULL_CONTIG_ID}",
        "NODE_1 VERSION line",
    )
    return text.encode("ascii")


def _transform_fasta(content: bytes) -> tuple[bytes, str]:
    text = content.decode("ascii")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != ">NODE_1":
        raise ValueError("full-locus synthetic fixture expected the exact >NODE_1 FASTA header")
    sequence = "".join(
        line.strip() for line in text.splitlines() if line and not line.startswith(">")
    )
    if len(sequence) != 100000 or set(sequence) != {"A"}:
        raise ValueError("full-locus synthetic fixture expected exactly 100000 A bases")
    ending = "\r\n" if lines[0].endswith("\r\n") else "\n" if lines[0].endswith("\n") else ""
    lines[0] = f">{SYNTHETIC_FULL_CONTIG_ID}{ending}"
    return "".join(lines).encode("ascii"), hashlib.sha256(sequence.encode("ascii")).hexdigest()


def _transform_kcb(content: bytes) -> bytes:
    text = content.decode("ascii")
    text = _replace_anchored_once(
        text,
        r"^ClusterBlast scores for CP073042\.1\s*$",
        f"ClusterBlast scores for {SYNTHETIC_FULL_CONTIG_ID}",
        "CP073042.1 KCB query header",
    )
    return text.encode("ascii")


def prepare_full_locus_single_contig_fixture(source: Path, target: Path) -> dict:
    """Generate one explicit full-locus synthetic archive in temporary test storage.

    Unlike :func:`prepare_single_contig_fixture`, this is an explicit, narrow
    transformation. It rewrites only seven hash-bound members and their anchored
    identity fields; it is not a production admission or identity-repair path.
    """
    source = Path(source)
    target = Path(target)
    if target.exists():
        raise FileExistsError(f"runtime synthetic fixture target already exists: {target}")
    source_bytes = source.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    if source_hash != _SINGLE_CONTIG_SHA256:
        raise ValueError("synthetic fixture source hash is not the governed input")

    source_member_hashes = {}
    prepared_member_hashes = {}
    sequence_sha256 = ""
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(source_bytes)) as zin:
        infos = zin.infolist()
        names = [info.filename for info in infos]
        if len(set(names)) != len(names):
            raise ValueError("synthetic fixture has duplicate member names")
        if names != list(_FULL_LOCUS_MEMBER_MAPPING):
            raise ValueError("full-locus synthetic fixture source member inventory changed")
        with zipfile.ZipFile(output, "w") as zout:
            for info in infos:
                content = zin.read(info)
                source_member_hashes[info.filename] = hashlib.sha256(content).hexdigest()
                if info.filename.endswith(".gbk"):
                    transformed = _transform_region_gbk(content)
                elif info.filename.endswith(".fasta"):
                    transformed, sequence_sha256 = _transform_fasta(content)
                elif "/knownclusterblast/" in info.filename and info.filename.endswith(".txt"):
                    transformed = _transform_kcb(content)
                else:
                    raise ValueError(f"unexpected full-locus synthetic fixture member: {info.filename}")
                prepared_name = _FULL_LOCUS_MEMBER_MAPPING[info.filename]
                prepared = copy.copy(info)
                prepared.filename = prepared_name
                prepared.orig_filename = prepared_name
                if prepared_name.endswith(".fasta"):
                    prepared.compress_type = zipfile.ZIP_STORED
                zout.writestr(prepared, transformed)
                prepared_member_hashes[prepared_name] = hashlib.sha256(transformed).hexdigest()

    prepared_bytes = output.getvalue()
    with zipfile.ZipFile(io.BytesIO(prepared_bytes)) as prepared:
        prepared_names = prepared.namelist()
        if prepared_names != list(_FULL_LOCUS_MEMBER_MAPPING.values()):
            raise ValueError("full-locus synthetic fixture prepared member inventory mismatch")
        observed = {
            info.filename: hashlib.sha256(prepared.read(info)).hexdigest()
            for info in prepared.infolist()
        }
        if observed != prepared_member_hashes:
            raise ValueError("full-locus synthetic fixture prepared member hash mismatch")
    if hashlib.sha256(source.read_bytes()).hexdigest() != source_hash:
        raise ValueError("synthetic fixture source changed during preparation")
    with target.open("xb") as handle:
        handle.write(prepared_bytes)
    return {
        "policy": _FULL_LOCUS_POLICY,
        "source_sha256": source_hash,
        "prepared_sha256": hashlib.sha256(prepared_bytes).hexdigest(),
        "declared_full_contig": SYNTHETIC_FULL_CONTIG_ID,
        "source_sequence_bases": 100000,
        "source_sequence_sha256": sequence_sha256,
        "member_mapping": dict(_FULL_LOCUS_MEMBER_MAPPING),
        "source_member_sha256": source_member_hashes,
        "prepared_member_sha256": prepared_member_hashes,
        "transformation": "seven_known_members_and_anchored_identity_fields_only",
    }
