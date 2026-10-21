"""strain_master.py — create, fill and check a User Strain Master (docs/DATA_HOME.md).

A User Strain Master is one folder, chosen by the user, that holds a copy of every record and
result a paper or report relies on. It has a fixed layout: numbered areas (01 Strains ...
07 Papers), and in each area only the subfolders its LAYOUT.md allows. Every stored file is a
byte-for-byte copy whose SHA-256 and original path are recorded in its folder's README, and
every import adds one line to the master's CHANGELOG.md. The reader side (finding a master and
looking things up in it) is ``mamey.strain_data_home``; this module is the only writer.

    init_master(root)                 new master: layout, LAYOUT.md, READMEs, CHANGELOG.md, inbox, settings
    adopt_master(root, ...)           write only strain_master.json into an existing master
    submit(items, ...)                the one way in: byte copies into 00 Inbox/<id>/ with MANIFEST.tsv
    verify(id, accept=...)            a second reviewer (never the submitter) accepts or returns it
    apply_submission(id, ...)         an accepted import goes to its folders through store(); an
                                      accepted record edit is applied at its record home
    store(src, folder, what, ...)     the import step: copy, README record, CHANGELOG line
    check(master)                     junk, layout, README coverage, checksums, CHANGELOG, inbox, named paths

Every step is booked in 00 Inbox/INBOX_LEDGER.tsv. ``store`` on its own is refused unless the
master's settings say ``"direct_store": true`` (for a single-person master that opts out).

Write boundary: every write lands inside the configured master root, checked on the resolved
path, so ``..``, an absolute folder or a symlink cannot carry a write outside it. Originals are
never moved or edited. A replaced copy moves to that folder's ``Superseded/``. The source names
no workspace path; the root comes from the caller or ``SAPOTE_STRAIN_MASTER``.
Standard library only.
"""
from __future__ import annotations

import csv
import datetime
import glob
import hashlib
import io
import json
import os
import re
import shutil
import tempfile
import zipfile

from .csv_safety import SafeDictWriter, SafeWriter
from .strain_data_home import (
    RECORD_HEADER, STRAIN_MASTER_CHANGELOG, STRAIN_MASTER_CONFIG, STRAIN_MASTER_ENV, STRAIN_MASTER_INBOX,
    STRAIN_MASTER_KINDS, STRAIN_MASTER_LEDGER,
    STRAIN_MASTER_LAYOUT, STRAIN_MASTER_LAYOUT_FILE, STRAIN_MASTER_SCHEMA, STRAIN_MASTER_TOP_README,
    SUPERSEDED_MARKER, _NUMBERED, layout_allows, read_layout, strain_master_config, strain_master_root,
)

__all__ = ["StrainMasterError", "init_master", "adopt_master", "store", "check", "check_report_lines",
           "layout_markdown", "submit", "verify", "apply_submission", "inbox_status", "LEDGER_COLUMNS",
           "MANIFEST_COLUMNS", "CHANGESET_COLUMNS", "CHECKLIST"]

_HEADER_PREFIX = "| File | SHA-256 |"
_ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})`")
_LOG_ROW = re.compile(r"^- (\S+ \S+) · (new|replaced|registered) · `([^`]+)` · sha256 ([0-9a-f]{64})")
_JUNK = (".DS_Store", "__pycache__")
_RESERVED = ("README.md", STRAIN_MASTER_TOP_README, STRAIN_MASTER_CONFIG, STRAIN_MASTER_LAYOUT_FILE,
             STRAIN_MASTER_CHANGELOG)
_INTROS = {f"{a}/{s}": w for a, _w, subs in STRAIN_MASTER_LAYOUT for s, w in subs if s != "*"}
_INTROS.update({a: w for a, w, _s in STRAIN_MASTER_LAYOUT})


class StrainMasterError(Exception):
    """A refused request. The message starts with a short code (NO_MASTER, OUTSIDE_ROOT, ...)."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inside(root: str, path: str) -> bool:
    """True when *path*, with symlinks resolved, sits strictly below *root*."""
    rr = os.path.realpath(root)
    rp = os.path.realpath(path)
    return rp != rr and rp.startswith(rr + os.sep)


def _atomic_write(path: str, data: bytes) -> None:
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _write_text(path: str, text: str) -> None:
    _atomic_write(path, text.encode("utf-8"))


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _folder_readme(title: str, intro: str) -> str:
    return "\n".join([f"# {title}", "", intro, "",
                      "Each file is a byte-for-byte copy of its original (left in place), entered with "
                      "`strain-master store`; `strain-master check` re-checks every checksum below.", "",
                      RECORD_HEADER, "|---|---|---|---|", ""])


def layout_markdown(name: str) -> str:
    """The LAYOUT.md of a new master: the only entries the self-check allows."""
    rows = [("00 README.md", "file", "What this master is, its house rules and its areas."),
            (STRAIN_MASTER_LAYOUT_FILE, "file", "This file: the only folders allowed here."),
            (STRAIN_MASTER_CHANGELOG, "file", "One line per import, written by `strain-master store`."),
            (STRAIN_MASTER_CONFIG, "file", "Settings: the master's name, raw stores and where each output kind goes.")]
    for area, what, subs in STRAIN_MASTER_LAYOUT:
        rows.append((area, "area", what))
        if area == STRAIN_MASTER_INBOX:
            rows.append((f"{area}/{STRAIN_MASTER_LEDGER}", "file", "One row per submission, every step booked."))
        rows += [(f"{area}/{s}", "folder", w) for s, w in subs]
    return "\n".join([f"# Layout of {name}", "",
                      "These are the only entries allowed. `strain-master check` fails on any other top-level "
                      "entry or area subfolder. Every area may also hold `Superseded/` and its README. "
                      "`*` means one folder per item. Change this file only with the owner's approval.", "",
                      "| Path | Kind | What goes in |", "|---|---|---|"]
                     + [f"| `{p}` | {k} | {w} |" for p, k, w in rows] + [""])


def _config(name: str, raw_stores=(), bundle_version: str | None = None, **extra) -> dict:
    cfg = {"schema": STRAIN_MASTER_SCHEMA, "name": name,
           "created": datetime.date.today().isoformat(), "created_with": bundle_version or "unknown",
           "raw_stores": list(raw_stores), "folders": dict(STRAIN_MASTER_KINDS),
           "checksum_readmes": ["**/README.md"], "coverage_exempt": [], "direct_store": False}
    cfg.update({k: v for k, v in extra.items() if v is not None})
    return cfg


def _top_readme(name: str) -> str:
    lines = [f"# {name}", "",
             "The one home for data that ends up in a paper. If a number is in a paper, its source is in here.", "",
             "## House rules",
             "- **The master holds copies, never edits.** Records are edited at their home; the copy here is re-imported.",
             "- **One way in.** Files enter only through `python mamey_run.py strain-master store`, which writes "
             "the README record and a CHANGELOG line.",
             "- **A fixed layout.** Only the folders in `LAYOUT.md` are allowed.",
             "- **No stray files.** Every file is listed in its folder's README.",
             "- **One current version.** A replaced copy moves to the Superseded folder beside it.",
             "- **Check every round.** Run `python mamey_run.py strain-master check` and report its RESULT line.",
             "", "## Root files",
             f"- `{STRAIN_MASTER_LAYOUT_FILE}`: the allowed layout.",
             f"- `{STRAIN_MASTER_CHANGELOG}`: one line per import.",
             f"- `{STRAIN_MASTER_CONFIG}`: settings.", "", "## Areas"]
    lines += [f"- `{area}/`: {what}" for area, what, _subs in STRAIN_MASTER_LAYOUT]
    return "\n".join(lines + [""])


def init_master(root: str, name: str | None = None, raw_stores=(), bundle_version: str | None = None) -> list[str]:
    """Create a new master at *root* with the standard layout. Refuses an occupied folder.
    Returns the created paths, relative to *root*."""
    root = os.path.abspath(os.path.expanduser(root))
    if os.path.exists(root) and (not os.path.isdir(root) or os.listdir(root)):
        raise StrainMasterError(f"OCCUPIED: {root} exists and is not an empty folder; "
                                "use `adopt` for an existing master")
    name = name or os.path.basename(os.path.normpath(root))
    os.makedirs(root, exist_ok=True)
    made = []
    for area, what, subs in STRAIN_MASTER_LAYOUT:
        os.makedirs(os.path.join(root, area))
        named = [s for s, _w in subs if s != "*"]
        body = [f"# {area}", "", what, ""] + [f"- `{s}/`: {w}" for s, w in subs if s != "*"]
        body += [f"- One folder per item: {w}" for s, w in subs if s == "*"] + [""]
        _write_text(os.path.join(root, area, "README.md"), "\n".join(body))
        made.append(area + "/README.md")
        for sub in named:
            os.makedirs(os.path.join(root, area, sub))
            intro = _INTROS[f"{area}/{sub}"]
            _write_text(os.path.join(root, area, sub, "README.md"), _folder_readme(sub, intro)
                        if area != STRAIN_MASTER_INBOX else f"# {sub}\n\n{intro}\n")
            made.append(f"{area}/{sub}/README.md")
    _write_text(os.path.join(root, STRAIN_MASTER_INBOX, STRAIN_MASTER_LEDGER), "\t".join(LEDGER_COLUMNS) + "\n")
    made.append(f"{STRAIN_MASTER_INBOX}/{STRAIN_MASTER_LEDGER}")
    _write_text(os.path.join(root, STRAIN_MASTER_TOP_README), _top_readme(name))
    _write_text(os.path.join(root, STRAIN_MASTER_LAYOUT_FILE), layout_markdown(name))
    _write_text(os.path.join(root, STRAIN_MASTER_CHANGELOG), f"# Changelog of {name}\n\nOne line per import.\n\n")
    _write_text(os.path.join(root, STRAIN_MASTER_CONFIG),
                json.dumps(_config(name, raw_stores, bundle_version), indent=1) + "\n")
    return [STRAIN_MASTER_TOP_README, STRAIN_MASTER_LAYOUT_FILE, STRAIN_MASTER_CHANGELOG, STRAIN_MASTER_CONFIG] + made


def adopt_master(root: str, name: str | None = None, raw_stores=(), checksum_readmes=None,
                 coverage_exempt=None, bundle_version: str | None = None) -> str:
    """Register an existing master: write only its strain_master.json. Nothing else is touched;
    its LAYOUT.md and CHANGELOG.md are the owner's to write."""
    root = os.path.abspath(os.path.expanduser(root))
    if not os.path.isdir(root):
        raise StrainMasterError(f"NO_SUCH_FOLDER: {root}")
    path = os.path.join(root, STRAIN_MASTER_CONFIG)
    if os.path.exists(path):
        raise StrainMasterError(f"ALREADY_ADOPTED: {path} exists")
    cfg = _config(name or os.path.basename(os.path.normpath(root)), raw_stores, bundle_version,
                  checksum_readmes=list(checksum_readmes) if checksum_readmes else None,
                  coverage_exempt=list(coverage_exempt) if coverage_exempt else None)
    _write_text(path, json.dumps(cfg, indent=1) + "\n")
    return path


def _origin(src: str, root: str, member: str | None) -> str:
    """Original path, relative to the folder holding the master when it lies there, else absolute."""
    path = os.path.abspath(src)
    base = os.path.dirname(os.path.abspath(root))
    shown = os.path.relpath(path, base) if path.startswith(base + os.sep) else path
    return f"`{shown}` → `{member}`" if member else f"`{shown}`"


def _upsert(readme: str, title: str, intro: str, row_name: str, row: str, superseded_row: str | None) -> None:
    text = _read(readme) if os.path.isfile(readme) else _folder_readme(title, intro)
    head, sep, tail = text.partition(SUPERSEDED_MARKER)
    lines = head.rstrip("\n").split("\n")
    at = next((i for i, ln in enumerate(lines) if (m := _ROW.match(ln.strip())) and m.group(1) == row_name), None)
    if at is not None:
        lines[at] = row
    else:
        hdr = next((i for i, ln in enumerate(lines) if ln.startswith(_HEADER_PREFIX)), None)
        if hdr is None:
            lines += ["", RECORD_HEADER, "|---|---|---|---|", row]
        else:
            end = hdr + 1
            while end + 1 < len(lines) and lines[end + 1].startswith("|"):
                end += 1
            lines.insert(end + 1, row)
    head = "\n".join(lines) + "\n"
    if superseded_row:
        if sep:
            tl = tail.rstrip("\n").split("\n")
            last = max((i for i, ln in enumerate(tl) if ln.startswith("|")), default=len(tl) - 1)
            tl.insert(last + 1, superseded_row)
            tail = "\n".join(tl) + "\n"
        else:
            sep = SUPERSEDED_MARKER
            tail = " earlier copies:\n\n| File | SHA-256 | Why |\n|---|---|---|\n" + superseded_row + "\n"
            head += "\n"
    _write_text(readme, head + sep + tail)


def _register_in_parent(root: str, folder: str, intro: str) -> None:
    parent, _, last = folder.rpartition("/")
    readme = os.path.join(root, parent, "README.md")
    text = _read(readme) or f"# {parent.rsplit('/', 1)[-1]}\n"
    if last not in text:
        _write_text(readme, text.rstrip("\n") + f"\n- `{last}/`: {intro}\n")


def _logged(root: str) -> dict:
    """Latest CHANGELOG entry per stored path: {path: (when, action, sha256)}."""
    out = {}
    for line in _read(os.path.join(root, STRAIN_MASTER_CHANGELOG)).splitlines():
        m = _LOG_ROW.match(line)
        if m:
            out[m.group(3)] = (m.group(1), m.group(2), m.group(4))
    return out


def store(src: str, folder: str, what: str, *, master: str | None = None, name: str | None = None,
          member: str | None = None, builder: str | None = None, create: bool = False,
          intro: str | None = None, dry_run: bool = False, now: datetime.datetime | None = None,
          origin: str | None = None, note: str | None = None, _from_inbox: bool = False) -> dict:
    """The one way in. Copy *src* (or one *member* of the ZIP *src*) byte for byte into *folder*,
    record its SHA-256, original path, *what* and *builder* in that folder's README, and add one
    line to the master's CHANGELOG.md.

    *folder* is a path under an area (``03 Genomes/ANI``) or an output kind (``mamey_package``).
    When the master has a LAYOUT.md, the folder's area and area subfolder must be allowed there.
    An unchanged file is left as is (and logged once as ``registered`` if the CHANGELOG lacks
    it); a changed one replaces the copy, and the old copy moves to ``Superseded/<date>_<name>``
    with a README row. Returns ``{"action", "dest", "sha256", "origin", "superseded", "readme",
    "logged", "dry_run"}``.
    """
    now = now or datetime.datetime.now()
    today = now.date().isoformat()
    root = strain_master_root(master)
    if root is None:
        raise StrainMasterError(f"NO_MASTER: give --master or set {STRAIN_MASTER_ENV} to an existing folder")
    try:
        cfg = strain_master_config(root)
    except ValueError as exc:
        raise StrainMasterError(f"CONFIG_INVALID: {exc}") from exc
    if not (_from_inbox or cfg.get("direct_store")):
        raise StrainMasterError("INBOX_REQUIRED: files enter this master through `strain-master submit`, a second "
                                "reviewer's `verify`, then `import`; direct store is off in its settings")
    folder = cfg["folders"].get(folder, folder).strip().strip("/")
    parts = folder.split("/")
    if parts[0] == STRAIN_MASTER_INBOX:
        raise StrainMasterError("BAD_FOLDER: the inbox is not a data folder")
    if (os.path.isabs(folder) or not folder or any(p in ("", ".", "..") or p.startswith(".") for p in parts)
            or "Superseded" in parts):
        raise StrainMasterError(f"BAD_FOLDER: {folder!r} must be a plain path inside the master")
    if not _NUMBERED.match(parts[0]) or len(parts) < 2:
        raise StrainMasterError(f"BAD_FOLDER: {folder!r} must be a folder inside an area (NN Name/Folder)")
    dest_dir = os.path.join(root, *parts)
    if not _inside(root, dest_dir):
        raise StrainMasterError(f"OUTSIDE_ROOT: {folder!r} resolves outside {root}")
    layout = read_layout(os.path.join(root, STRAIN_MASTER_LAYOUT_FILE))
    if layout is not None and not layout_allows(layout, folder):
        raise StrainMasterError(f"NOT_IN_LAYOUT: {folder!r} is not allowed by {STRAIN_MASTER_LAYOUT_FILE}; "
                                "a layout change needs the owner's approval")
    for label, value in (("what", what), ("builder", builder or "x")):
        if any(c in value for c in "|\n`") or not value.strip():
            raise StrainMasterError(f"BAD_TEXT: give a one-line {label} without '|' or backticks")
    name = name or os.path.basename(member or src)
    if os.sep in name or "/" in name or name.startswith(".") or name in _RESERVED:
        raise StrainMasterError(f"BAD_NAME: {name!r}")
    new_folder = not os.path.isdir(dest_dir)
    if new_folder and not create:
        raise StrainMasterError(f"NO_SUCH_FOLDER: {folder!r}; to add a folder the layout allows, pass "
                                "--create-folder with --intro")
    if new_folder and not (intro and intro.strip()):
        raise StrainMasterError("NEED_INTRO: a new folder needs --intro (one line on what it holds)")
    if new_folder and not os.path.isdir(os.path.dirname(dest_dir)):
        raise StrainMasterError(f"NO_SUCH_FOLDER: the parent of {folder!r} does not exist")
    if member:
        with zipfile.ZipFile(src) as zf:
            data = zf.read(member)
    else:
        if not os.path.isfile(src):
            raise StrainMasterError(f"NO_SUCH_FILE: {src}")
        with open(src, "rb") as fh:
            data = fh.read()
    h = _sha(data)
    dest = os.path.join(dest_dir, name)
    if os.path.islink(dest) or not _inside(root, dest):
        raise StrainMasterError(f"OUTSIDE_ROOT: {dest} is a link or resolves outside {root}")
    action, old_sha = "new", None
    if os.path.exists(dest):
        with open(dest, "rb") as fh:
            old_sha = _sha(fh.read())
        action = "unchanged" if old_sha == h else "replaced"

    def rel(p):
        return os.path.relpath(p, root).replace(os.sep, "/")

    sup = os.path.join(dest_dir, "Superseded", f"{today}_{name}") if action == "replaced" else None
    if sup and os.path.exists(sup):
        raise StrainMasterError(f"SUPERSEDED_EXISTS: {rel(sup)}; one replacement per file per day")
    origin = origin or _origin(src, root, member)
    log_action = action if action != "unchanged" else (None if rel(dest) in _logged(root) else "registered")
    result = {"action": action, "dest": rel(dest), "sha256": h, "origin": origin,
              "superseded": rel(sup) if sup else None, "readme": rel(os.path.join(dest_dir, "README.md")),
              "logged": log_action, "dry_run": dry_run}
    if dry_run:
        return result
    os.makedirs(dest_dir, exist_ok=True)
    if new_folder:
        _register_in_parent(root, "/".join(parts), intro.strip())
    if sup:
        os.makedirs(os.path.dirname(sup), exist_ok=True)
        shutil.move(dest, sup)
    if action != "unchanged":
        _atomic_write(dest, data)
        with open(dest, "rb") as fh:
            if _sha(fh.read()) != h:
                raise StrainMasterError(f"COPY_MISMATCH: {rel(dest)} does not match its source after writing")
    text_what = what.strip() + (f"{'' if what.strip().endswith('.') else '.'} Built by {builder.strip()}." if builder else "")
    row = f"| `{name}` | `{h}` | {origin} | {text_what} |"
    srow = f"| `{os.path.basename(sup)}` | `{old_sha}` | replaced on {today}: the source changed |" if sup else None
    title = parts[-1]
    _upsert(os.path.join(dest_dir, "README.md"), title,
            (intro or _INTROS.get("/".join(parts[:2]), title)).strip(), name, row, srow)
    if log_action:
        log = os.path.join(root, STRAIN_MASTER_CHANGELOG)
        text = _read(log) or f"# Changelog of {cfg.get('name')}\n\nOne line per import.\n\n"
        line = (f"- {now.strftime('%Y-%m-%d %H:%M')} · {log_action} · `{rel(dest)}` · sha256 {h} · from {origin}"
                f"{' · built by ' + builder.strip() if builder else ''} · {what.strip()}{' · ' + note if note else ''}")
        _write_text(log, text.rstrip("\n") + "\n" + line + "\n")
    return result


# ------------------------------------------------------------------------------------------ inbox
# Same ledger, statuses, folder names and record-edit rules as the first master's own inbox.py,
# so a master can move between the two without migrating its ledger.
LEDGER_COLUMNS = ("id", "submitted", "submitter", "kind", "topic", "target", "files", "status", "verifier",
                  "verified", "checks", "findings", "applied", "changelog")
MANIFEST_COLUMNS = ("file", "bytes", "sha256", "source", "member", "target", "what", "builder", "intro")
CHANGESET_COLUMNS = ("file", "key_column", "key", "field", "old", "new", "ruling")
CHECKLIST = ("files match their sources by SHA-256", "stated counts reproduce from the sources",
             "identities (strain / contig / region / alias) come from one source record",
             "no value contradicts a record or a ruling", "target folder is in LAYOUT; README line drafted",
             "no claim beyond the evidence; no private path in a shareable file")
REVIEWER_CHECKS = (2, 3, 4, 6)          # 1 and 5 are run by the tool
_STAMP = "%Y-%m-%d %H:%M"


def _clean(value, limit: int | None = None) -> str:
    text = re.sub(r"[\t\r\n]+", " ", str(value or "")).strip()
    return text[:limit] if limit else text


def _ledger_path(root: str) -> str:
    return os.path.join(root, STRAIN_MASTER_INBOX, STRAIN_MASTER_LEDGER)


def _read_tsv(path: str) -> list[dict]:
    if not os.path.isfile(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return [dict(r) for r in csv.DictReader(fh, delimiter="\t")]


def _write_tsv(path: str, columns, rows) -> None:
    buf = io.StringIO()
    w = SafeDictWriter(buf, fieldnames=list(columns), delimiter="\t", lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows({c: _clean(r.get(c)) for c in columns} for r in rows)
    _write_text(path, buf.getvalue())


def _root_cfg(master: str | None) -> tuple[str, dict]:
    root = strain_master_root(master)
    if root is None:
        raise StrainMasterError(f"NO_MASTER: give --master or set {STRAIN_MASTER_ENV} to an existing folder")
    try:
        return root, strain_master_config(root)
    except ValueError as exc:
        raise StrainMasterError(f"CONFIG_INVALID: {exc}") from exc


def _person(value: str | None, label: str) -> str:
    if not value or not re.fullmatch(r"[A-Za-z0-9._-]{2,64}", value):
        raise StrainMasterError(f"BAD_ID: give --{label} as a short id (letters, digits, . _ -), e.g. a chat id")
    return value


def _row(root: str, sub_id: str) -> tuple[list[dict], dict]:
    rows = _read_tsv(_ledger_path(root))
    hit = next((r for r in rows if r.get("id") == sub_id), None)
    if hit is None:
        raise StrainMasterError(f"NO_SUCH_SUBMISSION: {sub_id} has no ledger row")
    return rows, hit


def _record_homes(root: str, cfg: dict) -> list[str]:
    return [os.path.realpath(h if os.path.isabs(h) else os.path.join(root, h)) for h in cfg.get("record_homes") or []]


def _in_record_home(path: str, homes: list[str]) -> bool:
    rp = os.path.realpath(path)
    return any(rp.startswith(h + os.sep) for h in homes)


def _check_folder(cfg: dict, layout, folder: str) -> str:
    folder = cfg["folders"].get(folder, folder).strip().strip("/")
    parts = folder.split("/")
    if (len(parts) < 2 or not _NUMBERED.match(parts[0]) or parts[0] == STRAIN_MASTER_INBOX
            or any(p in ("", ".", "..") or p.startswith(".") for p in parts) or "Superseded" in parts):
        raise StrainMasterError(f"BAD_FOLDER: {folder!r} must be a folder inside an area (NN Name/Folder)")
    if layout is not None and not layout_allows(layout, folder):
        raise StrainMasterError(f"NOT_IN_LAYOUT: {folder!r} is not allowed by {STRAIN_MASTER_LAYOUT_FILE}")
    return folder


def submit(items: list[dict], *, submitter: str, topic: str, summary: str, reproduce=(), kind: str = "import",
           target: str | None = None, changeset: str | None = None, master: str | None = None,
           now: datetime.datetime | None = None) -> dict:
    """Submit to the inbox. Nothing reaches a data folder or a record table here.

    ``kind="import"``: *items* are dicts with ``src`` and ``what``, optionally ``folder`` (default
    *target*), ``name``, ``builder``, ``member`` (a ZIP member of ``src``) and ``intro`` (one line for
    a new folder the layout allows). ``kind="record-edit"``: *changeset* is a TSV with columns
    file, key_column, key, field, old, new, ruling; every file must sit in a record home named in
    the master's settings. Everything is checked before anything is written. Writes
    ``00 Inbox/<date_time>_<submitter>_<topic>/`` with byte copies, MANIFEST.tsv and SUBMISSION.md,
    and books one SUBMITTED ledger row. *reproduce* lists the counts or claims the verifier must reproduce.
    """
    now = now or datetime.datetime.now()
    root, cfg = _root_cfg(master)
    _person(submitter, "submitter")
    if not topic.strip() or not summary.strip():
        raise StrainMasterError("NEED_ARGS: a submission needs --topic and --summary")
    layout = read_layout(os.path.join(root, STRAIN_MASTER_LAYOUT_FILE))
    rows = []
    if kind == "import":
        if not items:
            raise StrainMasterError("NEED_ARGS: an import needs at least one file")
        names = set()
        for it in items:
            src, member = it.get("src") or "", it.get("member") or None
            if not os.path.isfile(src):
                raise StrainMasterError(f"NO_SUCH_FILE: {src}")
            folder = _check_folder(cfg, layout, it.get("folder") or target or "")
            name = it.get("name") or os.path.basename(member or src)
            if ("/" in name or os.sep in name or name.startswith(".") or name in names
                    or name in _RESERVED + ("SUBMISSION.md", "MANIFEST.tsv", "VERIFICATION.md", "APPLIED.md")):
                raise StrainMasterError(f"BAD_NAME: {name!r} (reserved, hidden or repeated)")
            names.add(name)
            what = it.get("what") or summary.split("\n")[0]
            for label, value in (("what", what), ("builder", it.get("builder") or "x"), ("intro", it.get("intro") or "x")):
                if any(c in value for c in "|\n\t`") or not value.strip():
                    raise StrainMasterError(f"BAD_TEXT: give a one-line {label} without '|', tabs or backticks")
            if member:
                with zipfile.ZipFile(src) as zf:
                    data = zf.read(member)
            else:
                with open(src, "rb") as fh:
                    data = fh.read()
            rows.append({"file": name, "bytes": len(data), "sha256": _sha(data), "source": os.path.abspath(src),
                         "member": member or "", "target": folder, "what": what, "builder": it.get("builder") or "",
                         "intro": it.get("intro") or "", "_data": data})
        ledger_target = "; ".join(sorted({r["target"] for r in rows}))
    elif kind == "record-edit":
        if not changeset or not os.path.isfile(changeset):
            raise StrainMasterError("NEED_ARGS: a record edit needs --changeset <tsv>")
        edits = _read_tsv(changeset)
        if not edits or not set(CHANGESET_COLUMNS) <= set(edits[0]):
            raise StrainMasterError(f"BAD_CHANGESET: columns must include {', '.join(CHANGESET_COLUMNS)}")
        homes = _record_homes(root, cfg)
        for e in edits:
            if not _in_record_home(e["file"], homes):
                raise StrainMasterError(f"NOT_A_RECORD_HOME: {e['file']} is not under a record home in the settings")
        with open(changeset, "rb") as fh:
            data = fh.read()
        rows.append({"file": "CHANGESET.tsv", "bytes": len(data), "sha256": _sha(data),
                     "source": os.path.abspath(changeset), "_data": data})
        ledger_target = "record tables"
    else:
        raise StrainMasterError("BAD_KIND: kind is import or record-edit")
    sub_id = f"{now:%Y-%m-%d_%H%M}_{submitter}_{re.sub(r'[^A-Za-z0-9]+', '-', topic).strip('-')[:40]}"
    folder_abs = os.path.join(root, STRAIN_MASTER_INBOX, sub_id)
    ledger = _read_tsv(_ledger_path(root))
    if os.path.exists(folder_abs) or any(r.get("id") == sub_id for r in ledger):
        raise StrainMasterError(f"SUBMISSION_EXISTS: {sub_id}")
    if not _inside(root, folder_abs):
        raise StrainMasterError(f"OUTSIDE_ROOT: {folder_abs}")
    os.makedirs(folder_abs)
    for r in rows:
        _atomic_write(os.path.join(folder_abs, r["file"]), r.pop("_data"))
    _write_tsv(os.path.join(folder_abs, "MANIFEST.tsv"), MANIFEST_COLUMNS, rows)
    lines = [f"# {topic.strip()}", "", f"- id: {sub_id}", f"- kind: {kind}",
             f"- submitted: {now.strftime(_STAMP)} by {submitter}", f"- target: {ledger_target}", "",
             "## What and why", "", summary.strip(), "", "## For the verifier to reproduce", ""]
    lines += [f"- {c}" for c in reproduce] or ["- (none stated)"]
    lines += ["", "## Files", ""] + [f"- {r['file']}: {r['bytes']} bytes, SHA-256 {r['sha256']}, from {r['source']}"
                                     f"{' member ' + r['member'] if r.get('member') else ''}"
                                     f"{' -> ' + r['target'] if r.get('target') else ''}" for r in rows]
    _write_text(os.path.join(folder_abs, "SUBMISSION.md"), "\n".join(lines) + "\n")
    ledger.append({"id": sub_id, "submitted": now.strftime(_STAMP), "submitter": submitter, "kind": kind,
                   "topic": topic, "target": ledger_target, "files": len(rows), "status": "SUBMITTED"})
    os.makedirs(os.path.dirname(_ledger_path(root)), exist_ok=True)
    _write_tsv(_ledger_path(root), LEDGER_COLUMNS, ledger)
    return {"id": sub_id, "status": "SUBMITTED", "files": len(rows)}


def _tool_checks(root: str, cfg: dict, folder_abs: str, kind: str) -> tuple[list[str], list[str]]:
    """(problems, drafted README lines) for checklist items 1 and 5."""
    probs, drafts = [], []
    layout = read_layout(os.path.join(root, STRAIN_MASTER_LAYOUT_FILE))
    for r in _read_tsv(os.path.join(folder_abs, "MANIFEST.tsv")):
        p = os.path.join(folder_abs, r["file"])
        if not os.path.isfile(p) or _file_sha(p) != r["sha256"]:
            probs.append(f"{r['file']}: changed since submission")
        src, member = r.get("source") or "", r.get("member") or ""
        if os.path.isfile(src):
            if member:
                with zipfile.ZipFile(src) as zf:
                    same = _sha(zf.read(member)) == r["sha256"]
            else:
                same = _file_sha(src) == r["sha256"]
            if not same:
                probs.append(f"{r['file']}: source changed since submission")
        if kind != "import":
            continue
        folder = r.get("target") or ""
        if layout is None or not layout_allows(layout, folder):
            probs.append(f"{r['file']}: target {folder!r} is not in {STRAIN_MASTER_LAYOUT_FILE}")
        elif not os.path.isdir(os.path.join(root, *folder.split("/"))) and not r.get("intro"):
            probs.append(f"{r['file']}: target {folder!r} does not exist; submit it with an intro line")
        else:
            built = f" Built by {r['builder']}." if r.get("builder") else ""
            drafts.append(f"| `{r['file']}` | `{r['sha256']}` | {_origin(src, root, member or None)} | {r['what']}{built} |")
    return probs, drafts


def verify(sub_id: str, *, verifier: str, accept: bool, checks: str, notes: str = "",
           master: str | None = None, now: datetime.datetime | None = None) -> dict:
    """Accept or return a submission. The verifier must not be the submitter.

    Items 1 and 5 of the checklist run here. To accept, *checks* must give what was run for items
    2, 3, 4 and 6, numbered (``"2 ok: recount 26; 3 ok: ...; 4 ok: ...; 6 ok: ..."``), and the
    tool's checks must pass; otherwise nothing is written. A return moves the submission to
    ``00 Inbox/Returned/<id>/``. VERIFICATION.md records the checklist, what was run and the findings.
    """
    now = now or datetime.datetime.now()
    root, cfg = _root_cfg(master)
    _person(verifier, "verifier")
    rows, row = _row(root, sub_id)
    if row["status"] != "SUBMITTED":
        raise StrainMasterError(f"BAD_STATE: {sub_id} is {row['status']}, not SUBMITTED")
    if verifier.casefold() == row["submitter"].casefold():
        raise StrainMasterError("SELF_VERIFY: the verifier must be a different chat from the submitter")
    if not _clean(checks):
        raise StrainMasterError("NEED_CHECKS: say what was run (--checks)")
    folder_abs = os.path.join(root, STRAIN_MASTER_INBOX, sub_id)
    probs, drafts = _tool_checks(root, cfg, folder_abs, row["kind"])
    if accept:
        given = {int(n) for n in re.findall(r"(?:^|[;\n])\s*(\d)\b", checks)}
        missing = [n for n in REVIEWER_CHECKS if n not in given]
        if missing:
            raise StrainMasterError(f"NEED_CHECKS: number what was run for item(s) {', '.join(map(str, missing))} "
                                    "of the checklist")
        if probs:
            raise StrainMasterError("CANNOT_ACCEPT: " + "; ".join(probs))
    status = "ACCEPTED" if accept else "RETURNED"
    text = [f"# Verification of {sub_id}", "", f"- verifier: {verifier}, {now.strftime(_STAMP)}",
            f"- result: {status}", "", "## Checklist", ""]
    text += [f"{i}. {c}" for i, c in enumerate(CHECKLIST, 1)]
    text += ["", "## What was run", "", checks.strip(), "", "## Notes", "", notes.strip() or "-"]
    if probs:
        text += ["", "## Tool findings", ""] + [f"- {p}" for p in probs]
    if drafts:
        text += ["", "## README lines drafted", ""] + drafts
    _write_text(os.path.join(folder_abs, "VERIFICATION.md"), "\n".join(text) + "\n")
    row.update(status=status, verifier=verifier, verified=now.strftime(_STAMP), checks=_clean(checks, 300),
               findings=_clean(notes or "; ".join(probs), 300))
    if not accept:
        dest = os.path.join(root, STRAIN_MASTER_INBOX, "Returned", sub_id)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(folder_abs, dest)
    _write_tsv(_ledger_path(root), LEDGER_COLUMNS, rows)
    return {"id": sub_id, "status": status, "verifier": verifier}


def _apply_record_edits(changeset: str, homes: list[str], stamp: str) -> list[str]:
    """Apply cell edits at their record home: each only if the cell still holds ``old`` and its key
    matches exactly one row; every file is checked before any is written; a ``.bak_<time>_inbox``
    copy is kept. Same rules as the first master's inbox.py."""
    by_file: dict = {}
    for e in _read_tsv(changeset):
        if not _in_record_home(e["file"], homes):
            raise StrainMasterError(f"NOT_A_RECORD_HOME: {e['file']}")
        by_file.setdefault(e["file"], []).append(e)
    plans = []
    for path, edits in by_file.items():
        with open(path, newline="", encoding="utf-8") as fh:
            text = fh.read()
        nl = "\r\n" if "\r\n" in text else "\n"
        lines = text.split(nl)
        delim = "," if path.endswith(".csv") else "\t"
        hdr = next(csv.reader([lines[0]], delimiter=delim))
        for e in edits:
            if e["key_column"] not in hdr or e["field"] not in hdr:
                raise StrainMasterError(f"BAD_CHANGESET: {path} has no column {e['key_column']!r} or {e['field']!r}")
            kc, fc = hdr.index(e["key_column"]), hdr.index(e["field"])
            hit = [i for i, ln in enumerate(lines[1:], 1) if ln and next(csv.reader([ln], delimiter=delim))[kc] == e["key"]]
            if len(hit) != 1:
                raise StrainMasterError(f"KEY_NOT_UNIQUE: {path}: key {e['key']} matches {len(hit)} rows; nothing applied")
            cells = next(csv.reader([lines[hit[0]]], delimiter=delim))
            if cells[fc] != e["old"]:
                raise StrainMasterError(f"OLD_VALUE_DIFFERS: {path} {e['key']} {e['field']} holds {cells[fc]!r}, "
                                        f"not {e['old']!r}; nothing applied")
            plans.append((path, hit[0], fc, e))
        by_file[path] = (lines, nl, delim, edits)
    done = []
    for path, (lines, nl, delim, _edits) in by_file.items():
        shutil.copy2(path, f"{path}.bak_{stamp}_inbox")
        for p, i, fc, e in plans:
            if p != path:
                continue
            cells = next(csv.reader([lines[i]], delimiter=delim))
            cells[fc] = e["new"]
            buf = io.StringIO()
            SafeWriter(buf, delimiter=delim, lineterminator="").writerow(cells)   # formula-led cells neutralised; signed numbers and lone signs kept
            lines[i] = buf.getvalue()
            done.append(f"{os.path.basename(path)} {e['key']} {e['field']}: {e['old']} -> {e['new']} ({e['ruling']})")
        _atomic_write(path, nl.join(lines).encode("utf-8"))
    return done


def apply_submission(sub_id: str, *, chat: str, master: str | None = None,
                     now: datetime.datetime | None = None) -> dict:
    """Apply an ACCEPTED submission. An import goes to its folders through ``store`` (README row,
    CHANGELOG line, Superseded/ for a replaced copy); a record edit is applied at its record home.
    The submission's records then move to ``00 Inbox/Done/<id>/`` with APPLIED.md."""
    now = now or datetime.datetime.now()
    root, cfg = _root_cfg(master)
    _person(chat, "chat")
    rows, row = _row(root, sub_id)
    if row["status"] != "ACCEPTED":
        raise StrainMasterError(f"NOT_ACCEPTED: {sub_id} is {row['status']}; only ACCEPTED submissions are applied")
    folder_abs = os.path.join(root, STRAIN_MASTER_INBOX, sub_id)
    manifest = _read_tsv(os.path.join(folder_abs, "MANIFEST.tsv"))
    for r in manifest:
        p = os.path.join(folder_abs, r["file"])
        if not os.path.isfile(p) or _file_sha(p) != r["sha256"]:
            raise StrainMasterError(f"CHANGED_AFTER_VERIFY: {r['file']} no longer matches its manifest")
    note = f"inbox {sub_id}; submitted by {row['submitter']}, verified by {row['verifier']}"
    if row["kind"] == "import":
        done = []
        for r in manifest:
            res = store(os.path.join(folder_abs, r["file"]), r.get("target") or row["target"],
                        r.get("what") or row["topic"], master=root, name=r["file"], builder=r.get("builder") or None,
                        create=bool(r.get("intro")), intro=r.get("intro") or None, now=now, _from_inbox=True,
                        origin=_origin(r.get("source") or r["file"], root, r.get("member") or None), note=note)
            done.append(f"{res['action']} {res['dest']}")
            os.unlink(os.path.join(folder_abs, r["file"]))
        line = f"{now.strftime(_STAMP)} import {row['topic']}: {len(done)} file(s) ({note})"
    else:
        done = _apply_record_edits(os.path.join(folder_abs, "CHANGESET.tsv"), _record_homes(root, cfg),
                                   now.strftime("%Y-%m-%d_%H%M"))
        line = f"{now.strftime(_STAMP)} record edit {row['topic']}: {len(done)} cell(s) ({note})"
        log = os.path.join(root, STRAIN_MASTER_CHANGELOG)
        _write_text(log, (_read(log) or "# Changelog\n\nOne line per import.\n\n").rstrip("\n") + f"\n- {line}\n")
    _write_text(os.path.join(folder_abs, "APPLIED.md"),
                f"# Applied {sub_id}\n\n- by {chat}, {now.strftime(_STAMP)}\n\n" + "".join(f"- {d}\n" for d in done))
    dest = os.path.join(root, STRAIN_MASTER_INBOX, "Done", sub_id)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(folder_abs, dest)
    row.update(status="APPLIED", applied=now.strftime(_STAMP), changelog=_clean(line, 300))
    _write_tsv(_ledger_path(root), LEDGER_COLUMNS, rows)
    return {"id": sub_id, "status": "APPLIED", "applied": done}


def inbox_status(master: str | None = None) -> list[dict]:
    """The ledger rows, oldest first."""
    root, _cfg = _root_cfg(master)
    return _read_tsv(_ledger_path(root))


def _check_inbox(root: str, now: datetime.datetime | None = None) -> dict:
    """Every submission folder has a ledger row; no one verified their own; nothing ACCEPTED waits a
    day or more; each row's folder is where its status says."""
    inbox = os.path.join(root, STRAIN_MASTER_INBOX)
    if not os.path.isdir(inbox):
        return {"name": "inbox bookkeeping", "status": "WARN",
                "lines": [f"no {STRAIN_MASTER_INBOX}/: submissions cannot be checked"]}
    now = now or datetime.datetime.now()
    rows = _read_tsv(_ledger_path(root))
    ids = {r.get("id") for r in rows}
    bad = [] if os.path.isfile(_ledger_path(root)) else [f"{STRAIN_MASTER_INBOX}/{STRAIN_MASTER_LEDGER}: missing"]
    for entry in sorted(os.listdir(inbox)):
        if entry.startswith(".") or entry in ("Done", "Returned", "README.md", STRAIN_MASTER_LEDGER):
            continue
        if not os.path.isdir(os.path.join(inbox, entry)):
            bad.append(f"{STRAIN_MASTER_INBOX}/{entry}: loose file in the inbox")
        elif entry not in ids:
            bad.append(f"{STRAIN_MASTER_INBOX}/{entry}: no ledger row")
    for r in rows:
        sid, status = r.get("id", ""), r.get("status", "")
        if r.get("verifier") and r["verifier"].casefold() == (r.get("submitter") or "").casefold():
            bad.append(f"{sid}: verified by its own submitter")
        place = {"APPLIED": ("Done", sid), "RETURNED": ("Returned", sid)}.get(status, (sid,))
        if status not in ("SUBMITTED", "ACCEPTED", "APPLIED", "RETURNED"):
            bad.append(f"{sid}: unknown status {status!r}")
        elif not os.path.isdir(os.path.join(inbox, *place)):
            bad.append(f"{sid}: {status} in the ledger but {STRAIN_MASTER_INBOX}/{'/'.join(place)}/ is missing")
        if status == "ACCEPTED":
            try:
                late = (now - datetime.datetime.strptime(r.get("verified", ""), _STAMP)).days >= 1
            except ValueError:
                late = True
            if late:
                bad.append(f"{sid}: accepted more than a day ago and not applied")
    return {"name": f"inbox bookkeeping ({len(rows)} submissions)", "status": "FAIL" if bad else "PASS", "lines": bad}


# ------------------------------------------------------------------------------------------ check
def _file_sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _record_files(folder: str) -> set[str]:
    """Files a record table covers: everything below *folder*, except READMEs, hidden files,
    Superseded/ and any subfolder that has its own README (it is checked on its own)."""
    out = set()
    for r, ds, fs in os.walk(folder):
        ds[:] = [d for d in ds if not d.startswith(".") and d != "Superseded"
                 and not os.path.isfile(os.path.join(r, d, "README.md"))]
        for f in fs:
            if f != "README.md" and not f.startswith("."):
                out.add(os.path.relpath(os.path.join(r, f), folder).replace(os.sep, "/"))
    return out


def _check_layout(root: str, layout: dict | None, source: str) -> dict:
    """Top-level entries and area subfolders against the layout. Inside the inbox only the inbox
    check applies. A table layout also checks root files and loose area files, and warns on
    allowed folders missing on disk; a list layout names folders only."""
    name = f"layout matches {source}"
    if layout is None:
        return {"name": name, "status": "FAIL", "lines": [f"no {source}: the layout cannot be checked"]}
    files = layout["files"]
    bad, absent = [], []
    for entry in sorted(os.listdir(root)):
        if entry.startswith("."):
            continue
        path = os.path.join(root, entry)
        if os.path.isdir(path):
            if entry not in layout["areas"]:
                bad.append(f"{entry}/: top-level folder not in the layout")
                continue
            if entry == STRAIN_MASTER_INBOX:
                continue
            area = layout["areas"][entry]
            for sub in sorted(os.listdir(path)):
                if sub.startswith(".") or sub == "README.md":
                    continue
                if os.path.isdir(os.path.join(path, sub)):
                    if sub != "Superseded" and sub not in area["folders"] and "*" not in area["folders"]:
                        bad.append(f"{entry}/{sub}/: folder not in the layout")
                elif files is not None and sub not in area["files"]:
                    bad.append(f"{entry}/{sub}: file loose in an area")
        elif files is not None and entry not in files:
            bad.append(f"{entry}: top-level file not in the layout")
    if files is not None:
        for area, spec in layout["areas"].items():
            if not os.path.isdir(os.path.join(root, area)):
                absent.append(f"{area}/: in the layout, not on disk")
            for sub in spec["folders"]:
                if sub != "*" and not os.path.isdir(os.path.join(root, area, sub)):
                    absent.append(f"{area}/{sub}/: in the layout, not on disk")
    return {"name": name, "status": "FAIL" if bad else ("WARN" if absent else "PASS"), "lines": bad + sorted(absent)}


def check(master: str | None = None, layout_file: str | None = None, config_file: str | None = None,
          now: datetime.datetime | None = None) -> dict:
    """Generic self-check of a master. Returns ``{"root", "name", "checks": [{"name", "status",
    "lines"}], "result": PASS | PASS with warnings | FAIL}``. Reads only.

    1. no junk files (.DS_Store, Office lock files, __pycache__, .pyc)                      FAIL
    2. top-level entries and area subfolders are all in LAYOUT.md (or *layout_file*, to
       preview a proposed layout; *config_file* likewise previews settings); allowed
       folders missing on disk                                                             FAIL / WARN
    3. every file and folder is named in its folder's README, its parent's or the top README  WARN
    4. every README with a ``| File | SHA-256 |`` table (within ``checksum_readmes``) lists
       exactly the files on disk, and each SHA-256 matches                                   FAIL
    5. each CHANGELOG entry's latest SHA-256 matches the file (a copy changed outside
       ``store``); no CHANGELOG.md is a warning                                             FAIL / WARN
    6. inbox bookkeeping: every submission has a ledger row, no submitter verified their own,
       nothing ACCEPTED waits more than a day, each row's folder exists                       FAIL
    7. every path written in backticks in a README exists                                    WARN
    """
    root = strain_master_root(master)
    if root is None:
        raise StrainMasterError(f"NO_MASTER: give --master or set {STRAIN_MASTER_ENV} to an existing folder")
    try:
        cfg = strain_master_config(root, config_file)
    except ValueError as exc:
        raise StrainMasterError(f"CONFIG_INVALID: {exc}") from exc
    exempt = [re.compile(p) for p in cfg.get("coverage_exempt") or []]

    def rel(p):
        return os.path.relpath(p, root).replace(os.sep, "/")

    checks = []
    junk = sorted(rel(os.path.join(r, n)) for r, ds, fs in os.walk(root) for n in fs + ds
                  if n in _JUNK or n.startswith("~$") or n.endswith(".pyc"))
    checks.append({"name": "no junk files", "status": "FAIL" if junk else "PASS", "lines": junk})

    lpath = layout_file or os.path.join(root, STRAIN_MASTER_LAYOUT_FILE)
    checks.append(_check_layout(root, read_layout(lpath),
                                STRAIN_MASTER_LAYOUT_FILE if layout_file is None else os.path.basename(lpath)))

    top_text = _read(os.path.join(root, STRAIN_MASTER_TOP_README)) or _read(os.path.join(root, "README.md"))
    missing = []
    for r, ds, fs in os.walk(root):
        ds[:] = [d for d in ds if not d.startswith(".")]
        rr = rel(r) if r != root else ""
        if "Superseded" in rr.split("/") or rr.split("/")[0] == STRAIN_MASTER_INBOX \
                or any(e.search(rr) for e in exempt if rr):
            continue
        here = _read(os.path.join(r, "README.md"))
        up = _read(os.path.join(os.path.dirname(r), "README.md")) if r != root else ""
        for n in fs + ds:
            if n in _RESERVED or n.startswith("."):
                continue
            child = f"{rr}/{n}" if rr else n
            if any(e.search(child) for e in exempt):
                continue
            if n not in here and n not in up and n not in top_text:
                missing.append(child)
    checks.append({"name": "every file and folder is named in a README",
                   "status": "WARN" if missing else "PASS", "lines": sorted(missing)})

    readmes = set()
    for pattern in cfg.get("checksum_readmes") or []:
        readmes.update(glob.glob(pattern, root_dir=root, recursive=True))
    bad, n_files, n_tables = [], 0, 0
    for rd in sorted(readmes):
        if "Superseded" in rd.split(os.sep) or os.path.basename(rd) != "README.md":
            continue
        text = _read(os.path.join(root, rd))
        if not any(ln.startswith(_HEADER_PREFIX) for ln in text.splitlines()):
            continue
        n_tables += 1
        folder = os.path.dirname(os.path.join(root, rd))
        listed = {}
        for ln in text.split(SUPERSEDED_MARKER)[0].splitlines():
            m = _ROW.match(ln.strip())
            if m:
                listed[m.group(1)] = m.group(2)
        on_disk = _record_files(folder)
        shown = rel(folder)
        for f in sorted(on_disk | set(listed)):
            n_files += 1
            if f not in listed:
                bad.append(f"{shown}/{f}: on disk, not in the README")
            elif f not in on_disk:
                bad.append(f"{shown}/{f}: in the README, not on disk")
            elif _file_sha(os.path.join(folder, f)) != listed[f]:
                bad.append(f"{shown}/{f}: checksum differs")
    checks.append({"name": f"files match their README checksums ({n_files} files in {n_tables} record tables)",
                   "status": "FAIL" if bad else "PASS", "lines": bad})

    if not os.path.isfile(os.path.join(root, STRAIN_MASTER_CHANGELOG)):
        checks.append({"name": "CHANGELOG entries match the files", "status": "WARN",
                       "lines": [f"no {STRAIN_MASTER_CHANGELOG}: imports are not logged"]})
    else:
        logged, drift = _logged(root), []
        for path, (_when, _action, sha) in sorted(logged.items()):
            p = os.path.join(root, *path.split("/"))
            if not os.path.isfile(p):
                drift.append(f"{path}: logged, not on disk")
            elif _file_sha(p) != sha:
                drift.append(f"{path}: changed since its last logged import")
        checks.append({"name": f"CHANGELOG entries match the files ({len(logged)} files logged)",
                       "status": "FAIL" if drift else "PASS", "lines": drift})

    checks.append(_check_inbox(root, now))

    dead = []
    all_readmes = [p for p in glob.glob("**/README.md", root_dir=root, recursive=True)
                   if "Superseded" not in p.split(os.sep)]
    if os.path.isfile(os.path.join(root, STRAIN_MASTER_TOP_README)):
        all_readmes.append(STRAIN_MASTER_TOP_README)
    for rd in sorted(all_readmes):
        base = os.path.dirname(rd)
        for p in re.findall(r"`([^`]+)`", _read(os.path.join(root, rd))):
            if not re.search(r"[/.]", p) or p.startswith(("http", "tools/", "mamey/", "docs/", "<", "python")) \
                    or (" " in p and "/" not in p):
                continue
            if re.search(r"[*<>]|\.\.\.", p) or (re.fullmatch(r"[\w.-]+\.(py|R|sh)", p)
                                               and glob.glob(f"**/{p}", root_dir=root, recursive=True)):
                continue
            cands = [os.path.join(root, base, p), os.path.join(root, p), os.path.join(root, base, "..", p),
                     os.path.join(os.path.dirname(root), p)]
            if not any(os.path.exists(c) for c in cands) and not glob.glob(
                    f"**/{glob.escape(os.path.basename(p.rstrip('/')))}", root_dir=root, recursive=True):
                dead.append(f"{rd}: `{p}`")
    checks.append({"name": "paths named in READMEs exist", "status": "WARN" if dead else "PASS", "lines": dead})

    statuses = {c["status"] for c in checks}
    result = "FAIL" if "FAIL" in statuses else ("PASS with warnings" if "WARN" in statuses else "PASS")
    return {"root": root, "name": cfg.get("name"), "checks": checks, "result": result}


def check_report_lines(report: dict, limit: int = 25) -> list[str]:
    """The check as terminal lines, in the format of the first master's own self-check."""
    out = []
    for c in report["checks"]:
        out.append(f"[{c['status']}] {c['name']}")
        out += ["       " + ln for ln in c["lines"][:limit]]
        if len(c["lines"]) > limit:
            out.append(f"       ... {len(c['lines']) - limit} more")
    return out + ["", f"RESULT: {report['result']}"]
