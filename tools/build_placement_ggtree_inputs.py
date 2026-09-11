#!/usr/bin/env python3
"""build_placement_ggtree_inputs.py — the MISSING producer for tools/ggtree_placement.R.

ggtree_placement.R (shipped) renders a paper-ready EPA-ng placement figure from a pruned newick + an
annotation TSV, but its documented producer (an older unpackaged producer script) was never packaged into the bundle
— the R renderer was orphaned (consumer without producer). This restores the contract end-to-end.

From a grafted placement newick (phylo_place.py report → epa_result.newick) it:
  * classifies tips as query (AS/SID id) / outgroup / reference,
  * prunes to each query + its N nearest reference tips (patristic distance; the prune ladder),
  * writes <prefix>_pruned.nwk and <prefix>_ggtree_annotation.tsv with the columns ggtree_placement.R
    expects: tip, kind, as_id, host, region, accession, validation, label_withloc, label_noloc, ref_label.
  * optionally writes renderer-ready tip/label/category/source metadata via --rect-meta-out.
Query host + GenBank 16S accession come from a strain table (default: the paper strain table /
OFFICIAL_DATA/STRAIN_METADATA.tsv); reference labels drop the redundant ingroup genus, keep the accession.

Usage:
  Tools/bin/python3 tools/build_placement_ggtree_inputs.py \
      --graft <epa_result.newick> --group Actinomadura --neighbors 3 \
      --host-table "September 6 2026/HOST_METADATA_CLEANED_2026-09-06.tsv" \
      --out-prefix <dir>/Actinomadura
Then:
  Rscript tools/ggtree_placement.R <prefix>_pruned.nwk <prefix>_ggtree_annotation.tsv <out> noloc

Needs biopython -> run with Tools/bin/python3. 16S = anchor/neighbourhood, not a species call; judgment deferred.
"""
import argparse, csv, os, re, sys, hashlib, json

try:
    import _phylo_metadata as _phylo_meta
except ImportError:  # imported as tools.build_placement_ggtree_inputs
    from tools import _phylo_metadata as _phylo_meta

try:  # spreadsheet formula guard for optional renderer metadata
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level above tools/
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

LABEL_STYLES = ("id", "host", "noloc", "withloc", "full")
NULLISH = {"", "unknown", "n/a", "na", "none", "null", "unspecified", "not collected", "not provided", "not available", "not applicable", "not determined", "missing", "-"}


def _asid(n):
    m = re.search(r"AS[_-]?(\d+)", n or "")
    return f"AS-{m.group(1)}" if m else (n or "")


def _is_query(n):
    return bool(re.match(r"^(AS|SID)[-_]?\d", n or ""))  # anchored: query tip STARTS with the id; not an embedded "AS 4.xxxx" culture code (F4)


def _find_host_table(path):
    return path or ""


def _clean(v):
    v = (v or "").strip()
    return "" if v.lower() in NULLISH else v


def _dedup_region(host, region):
    """Drop the region when the host string already ends with it.

    A `folder_parse` host such as "Kribella, Moss, Ontario" carries the place inside it, so the old
    formatter printed "(Kribella, Moss, Ontario · Ontario)". Fixing the column precedence removes most
    of these, but a curated host may still legitimately repeat the place, so dedup defensively rather
    than trusting the upstream fix. Case-insensitive; only a trailing repeat is removed, so a host
    genuinely named after a place ("Ontario clover") is untouched.
    """
    if not host or not region:
        return region
    h, r = host.strip().lower(), region.strip().lower()
    if h == r or h.endswith(", " + r) or h.endswith(" " + r):
        return ""
    return region


def _display_accession(acc):
    """Display an accession without its version, retaining full keys for data joins."""
    base = re.sub(r"\.\d+$", "", acc or "")
    return f"({base})" if base else ""


def _label_styles(aid, host, region, acc):
    """Every query-label style for one tip, keyed by name. Never emits an empty "()" or a stray
    separator: a tip with no metadata degrades to the bare id rather than "query_missing_metadata ( · )"."""
    host, region, acc = _clean(host), _clean(region), _clean(acc)
    # Case-normalise the host: the curated tables use lowercase common names ("moss", "ant",
    # "other bee") while a deposited GenBank /host is free text ("Moss"). Mixing both in one figure
    # reads as two different values for the same thing. Lowercased only when the string is a single
    # plain word or two, so a proper noun inside a longer deposited phrase is left alone.
    if host and host.replace(" ", "").isalpha() and len(host.split()) <= 2:
        host = host.lower()
    rg = _dedup_region(host, region)
    inner = " · ".join([x for x in (host, rg) if x])
    paren = f"[{inner}]" if inner else ""
    hostonly = f"[{host}]" if host else ""
    acc = _display_accession(acc)
    return {
        "id":      aid,
        "host":    " ".join(x for x in (aid, hostonly) if x),
        "noloc":   " ".join(x for x in (aid, hostonly, acc) if x),
        "withloc": " ".join(x for x in (aid, paren, acc) if x),
        "full":    " ".join(x for x in (aid, paren, acc) if x),
    }


def _load_aux(paths=()):
    """Read explicit generic TSV inputs; conflicting nonempty values are refused."""
    out = {}
    for path in paths:
        with open(path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            if not {"strain", "host", "region", "accession"} <= set(reader.fieldnames or ()):
                raise ValueError("AUX_METADATA_SCHEMA")
            for row in reader:
                sid = (row.get("strain") or "").strip()
                if not sid or None in row or any(v is None for v in row.values()):
                    raise ValueError("AUX_METADATA_IDENTITY_OR_WIDTH")
                rec = out.setdefault(sid, {})
                for key, col in (("host", "host"), ("region", "region"), ("acc", "accession")):
                    value = _clean(row[col])
                    if rec.get(key) and value and rec[key] != value:
                        raise ValueError("AUX_METADATA_CONFLICT")
                    if value:
                        rec[key] = value
    return out


def _load_required_references(path):
    """Load an explicit query-to-reference-species pairing table."""
    if not path:
        return {}
    out = {}
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not {"strain", "reference_species"} <= set(reader.fieldnames or ()):
            raise ValueError("REQUIRED_REFERENCE_TABLE_SCHEMA")
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("REQUIRED_REFERENCE_TABLE_WIDTH")
            strain = (row.get("strain") or "").strip()
            species = re.sub(r"\s+", " ", (row.get("reference_species") or "").strip())
            if not strain or not re.fullmatch(r"[A-Z][a-z-]+ [a-z][a-z-]+", species):
                raise ValueError("REQUIRED_REFERENCE_TABLE_IDENTITY")
            if strain in out and out[strain] != species:
                raise ValueError("REQUIRED_REFERENCE_TABLE_CONFLICT")
            out[strain] = species
    return out


def _load_hosts(path):
    """Return {AS-id: {host, region, acc}} from a strain table. Accepts the paper strain table
    (Host / Location / Strain Number / Genbank Accession) or STRAIN_METADATA.tsv (host_raw / location /
    tip_label / genbank_accession)."""
    hosts = {}
    if not path or not os.path.exists(path):
        return hosts
    with open(path) as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            sid = (row.get("Strain Number") or row.get("tip_label") or row.get("strain") or "").strip()
            if not sid:
                continue
            # v9.7.417 (metadata repair): CLEAN columns before RAW ones. STRAIN_METADATA.tsv carries both
            # `host_common`/`location` (curated) and `host_raw`/`location_raw` (as-found). For the 106
            # rows whose `source` is `folder_parse`, the raw fields hold the FOLDER LABEL, not a host:
            # query_repeated_region reads host_raw="Kribella, Moss, Ontario" (a misspelled genus + substrate + place)
            # while host_common="moss" and location="Ontario" are correct and sit right there. The old
            # precedence put host_raw FIRST, so 93 of 318 rows put a folder string into a publication
            # figure's tip label, and the location then printed twice: "query_repeated_region (Kribella, Moss,
            # Ontario · Ontario)". This is the standing rule that a folder label is not an ecology
            # source. `--allow-raw-host` restores the old order for a table that has only raw columns.
            _raw_first = bool(globals().get("_ALLOW_RAW_HOST"))
            _h = [row.get("Host"), row.get("host_common"), row.get("host"), row.get("host_raw")]
            _r = [row.get("Location"), row.get("location"), row.get("location_raw")]
            if _raw_first:
                _h = [_h[0], _h[3], _h[1], _h[2]]; _r = [_r[0], _r[2], _r[1]]
            host = next((v.strip() for v in _h if v and v.strip()), "")
            region = next((v.strip() for v in _r if v and v.strip()), "")
            acc = (row.get("Genbank Accession") or row.get("genbank_accession") or "").strip()
            experiment = (row.get("Experiment #") or row.get("experiment_id") or "").strip()
            sample = str(row.get("Sample #") or row.get("sample_id") or "").strip()
            hosts[_asid(sid)] = {"host": host, "region": region,
                                 "acc": ("" if acc.upper() in ("", "N/A") else acc),
                                 "experiment": experiment, "sample": sample}
    return hosts


def _load_origins(path):
    """Return {"genus species".lower(): category} from a type-strain isolation-source TSV."""
    import csv as _csv
    out = {}
    if path and os.path.exists(path):
        with open(path) as fh:
            for row in _csv.DictReader(fh, delimiter="\t"):
                ts = (row.get("type_strain") or "").strip().lower()
                cat = (row.get("category") or "").strip()
                if ts and cat:
                    out[ts] = cat
    return out


def _load_bioassay(path):
    """Return {AS-id: {anti_candida, anti_mrsa}} from a strain-level MEASURED bioassay table
    (CSV or TSV; header must carry strain, anti_Candida, anti_MRSA -- matched case-insensitively;
    extra columns such as host/genus are ignored). Delimiter is auto-detected from the first line
    (a literal tab wins over a comma) so the shipped af_dossier_activity_table.csv (comma) and a
    hand-edited TSV both work without a separate flag.

    CLAIM CEILING (v9.7.423): this is MEASURED, CRUDE-EXTRACT, STRAIN-LEVEL activity -- the same
    ceiling as tree_bioassay.py's overlay. It is never attributed to a BGC or a compound, and it is
    NEVER applied to a reference/type-strain tip: those are public comparators, not this project's
    wet-lab isolates. Values are copied verbatim from the source table; a blank/missing cell is a
    real "not tested" or "not recorded", never inferred or filled with a default."""
    out = {}
    if not path:
        return out
    with open(path, newline="", encoding="utf-8-sig") as fh:
        first = fh.readline()
        fh.seek(0)
        delim = "\t" if "\t" in first else ","
        reader = csv.DictReader(fh, delimiter=delim)
        colmap = {(f or "").strip().lower(): f for f in (reader.fieldnames or [])}
        if len(colmap) != len(reader.fieldnames or []) or not {"strain", "anti_candida", "anti_mrsa"} <= set(colmap):
            raise ValueError("BIOASSAY_METADATA_SCHEMA")
        for row in reader:
            if None in row or any(row.get(colmap[k]) is None for k in ("strain", "anti_candida", "anti_mrsa")):
                raise ValueError("BIOASSAY_METADATA_SCHEMA")
            sid = (row.get(colmap["strain"]) or "").strip()
            if not sid:
                raise ValueError("BIOASSAY_METADATA_IDENTITY")
            aid = _asid(sid)
            cand = (row.get(colmap["anti_candida"]) or "").strip().lower()
            mrsa = (row.get(colmap["anti_mrsa"]) or "").strip().lower()
            values = {"anti_candida": cand, "anti_mrsa": mrsa}
            if any(v not in {"", "positive", "negative", "not_tested"} for v in values.values()):
                raise ValueError("BIOASSAY_METADATA_VALUE")
            if aid in out:
                if out[aid] == values:
                    raise ValueError("BIOASSAY_METADATA_DUPLICATE")
                raise ValueError("BIOASSAY_METADATA_CONFLICT")
            out[aid] = values
    return out

def _species_of(name):
    p = (name or "").replace("_", " ")
    p = __import__("re").sub(r"^[A-Z]{2}[ _]?\d+(?:[ _.]?\d+)?\s+", "", p)
    m = __import__("re").match(r"([A-Z][a-z]+\s+[a-z]+)", p)
    return m.group(1).lower() if m else ""

# Budget applies to organism text only; accessions are preserved outside it.
REF_LABEL_CHARS = int(os.environ.get("GG_REF_LABEL_CHARS", "48"))
if not 8 <= REF_LABEL_CHARS <= 240:
    raise ValueError("GG_REF_LABEL_CHARS must be between 8 and 240")
REF_SOURCE_CHARS = int(os.environ.get("GG_REF_SOURCE_CHARS", "40"))
if not 8 <= REF_SOURCE_CHARS <= 240:
    raise ValueError("GG_REF_SOURCE_CHARS must be between 8 and 240")
_ACC = re.compile(r"(?<![A-Za-z0-9])(?:(?:NZ|NC|NG|NR|XR|GCF|GCA)_[A-Z]{0,6}\d{5,}|[A-Z]{1,2}\d{5,})(?:[._]\d+)?(?![A-Za-z0-9])")


def _accessions(name):
    return list(_ACC.finditer(name or ""))


def _ref_accession(name):
    """Resolve one accession; explicit strain designations are not accession fields."""
    matches = _accessions(name)
    normalize = lambda value: re.sub(r"(?<=\d)_(\d+)$", r".\1", value)
    values = {normalize(m.group()) for m in matches}
    NS = r"^(?:NZ|NC|NG|NR|XR|GCF|GCA)_"
    if len(values) > 1:
        # v9.7.421: a reference tip is built as <the record's own accession>_<its definition>, so a
        # candidate at position 0 IS the record's accession and every later candidate came out of the
        # definition text. When those later candidates are BARE tokens -- no namespace prefix -- they
        # are strain designations, and the leading accession resolves the tip.
        #
        # This is the only thing that rescues a non-type record: the branch below can return a survivor
        # only if it matches the namespace prefix, and a non-type record's own accession is a plain
        # GenBank accession, so no non-type conflict could ever resolve. Measured store-wide, conflicts
        # run 449/26,104 (1.72%) across the non-type pool against 11/27,425 (0.040%) for type strains,
        # and two of ten panels produced no figure today because of it -- e.g.
        # 'KU382719_1_Streptomyces_sp_A00969_16S...', where A00969 is a strain designation.
        #
        # DELIBERATELY NARROW. A later candidate that is namespaced OR carries a version suffix is a
        # real accession, not a designation -- 'MW444715.1' is a deposit, 'A00969' is a strain code --
        # so those tips carry two accessions and stay a refusal. If any later candidate is namespaced
        # or versioned the tip carries
        # two real accessions and stays a refusal, which is what
        # tests/test_reference_collection_prefixes.py pins ('NR_123456.1 strain NR_234567.1'). An
        # earlier, broader version of this hunk returned the leading token unconditionally and broke
        # 18 shipped tests; the narrow rule keeps every one of them green.
        leading = [m for m in matches if m.start() == 0]
        later = [m for m in matches if m.start() != 0]
        _versioned = lambda t: bool(re.search(r"[._]\d+$", t))
        if (len(leading) == 1 and later
                and not any(re.match(NS, m.group()) or _versioned(m.group()) for m in later)):
            return normalize(leading[0].group())
        # Only a declared strain field can disambiguate a bare token. Namespace
        # precedence alone would conceal a genuine mixed-namespace conflict.
        candidates = {normalize(m.group()) for m in matches if re.match(r"^(?:NZ|NC|NG|NR|XR|GCF|GCA)_", m.group()) or not re.search(
            r"\bstrain[ _]+(?:(?:YIM|CCTCC|SYSU|LL|NRRL)[ _]+)?$",
            (name or "")[:m.start()].replace("_", " "), re.I)}
        if len(candidates) == 1 and re.match(r"^(?:NZ|NC|NG|NR|XR|GCF|GCA)_", next(iter(candidates))):
            return next(iter(candidates))
        raise ValueError("REFERENCE_ACCESSION_CONFLICT")
    return next(iter(values), "")


def _acckey(acc):
    return re.sub(r"[^A-Za-z0-9]", "", (acc or "").split(".")[0]).upper()


def _load_ref_source_bundle(db_path):
    """Read deposited metadata as both display text and renderer-safe fields.

    ``category`` and ``location`` are direct projections from the explicitly
    supplied record.  The category uses isolation_source when present and host
    only when isolation_source is missing; neither value is parsed back out of
    the combined display string.
    """
    if not db_path:
        return {}, {}
    import sqlite3
    from contextlib import closing
    from pathlib import Path
    db = Path(db_path).resolve(strict=True)
    out = {}
    fields = {}
    with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)) as con:
        columns = {row[1] for row in con.execute("PRAGMA table_info(record)")}
        host_column = "host" if "host" in columns else "NULL"
        skipped_non_reference = 0
        for acc, isolation, host, country in con.execute("SELECT acc_base, isolation_source, " + host_column + ", country FROM record"):
            if isinstance(acc, str) and re.fullmatch(r"AS_LOCAL_(?:AS|AJS|SID|PENDING)-[0-9]+", acc):
                skipped_non_reference += 1
                continue
            if not isinstance(acc, str) or not _ACC.fullmatch(acc):
                raise ValueError("REFERENCE_SOURCE_ACCESSION_INVALID")
            key = _acckey(acc)
            cleaned = {}
            for field, value in (("isolation_source", isolation), ("host", host), ("country", country)):
                if value is None:
                    value = ""
                if not isinstance(value, str) or any(c in value for c in "\t\r\n"):
                    raise ValueError("REFERENCE_SOURCE_FIELD_INVALID")
                cleaned[field] = _clean(value)
            bits = []
            for field in ("isolation_source", "host", "country"):
                if cleaned[field]:
                    bits.append(("host: " if field == "host" else "") + cleaned[field])
            text = " · ".join(bits)
            structured = {
                "category": cleaned["isolation_source"] or cleaned["host"],
                "location": cleaned["country"],
            }
            if key in out and (out[key] != text or fields[key] != structured):
                raise ValueError("REFERENCE_SOURCE_CONFLICT")
            out[key] = text
            fields[key] = structured
    if skipped_non_reference:
        sys.stderr.write(f"[ggtree-inputs] skipped {skipped_non_reference} non-reference row(s) with explicit local-record keys; metadata not admitted for these rows.\n")
    return out, fields


def _load_ref_sources(db_path):
    """Compatibility view of explicitly supplied deposited metadata."""
    return _load_ref_source_bundle(db_path)[0]


def _rect_metadata_row(tip, label, category_raw, source_raw):
    """Renderer fields plus the untouched metadata and transformation states."""
    category = _phylo_meta.normalize_isolation_source(category_raw)
    source = _phylo_meta.normalize_geography(source_raw)
    return [
        tip, label, category["display_category"], source["display_location"],
        category["raw"], category["state"], source["raw"], source["state"],
    ]


def _reference_source(name, sources, requested):
    acc = _ref_accession(name)
    if not requested:
        return "NOT_REQUESTED", ""
    if not acc:
        return "ACCESSION_UNBOUND", ""
    key = _acckey(acc)
    if key not in sources:
        return "ACCESSION_UNMATCHED", ""
    return ("DEPOSITED_METADATA" if sources[key] else "METADATA_ABSENT"), sources[key]


def _reference_source_fields(name, fields, requested):
    """Return typed status plus direct category/location fields for one tip."""
    acc = _ref_accession(name)
    if not requested:
        return "NOT_REQUESTED", "", ""
    if not acc:
        return "ACCESSION_UNBOUND", "", ""
    key = _acckey(acc)
    if key not in fields:
        return "ACCESSION_UNMATCHED", "", ""
    row = fields[key]
    category, location = row["category"], row["location"]
    status = "DEPOSITED_METADATA" if category or location else "METADATA_ABSENT"
    return status, category, location


def _post_16s_strain_designation(text):
    """Keep an explicit strain designation that follows a 16S descriptor."""
    marker = re.search(r"\b16S\b", text or "", flags=re.I)
    if not marker:
        return ""
    match = re.search(
        r"\bstrain[: ]+(.+?)(?=\s+(?:non[ -]?type|type(?:\s+strain)?|outgroup\b|16S\b)|$)",
        text or "",
        flags=re.I,
    )
    if not match or match.start() < marker.start():
        return ""
    return " ".join(match.group(1).split())


def _ref_label(name, modal, src_map=None):
    """Format deposited labels without guessing accessions or truncating their identity."""
    acc = _ref_accession(name)
    rest = _ACC.sub(lambda m: " " if re.sub(r"(?<=\d)_(\d+)$", r".\1", m.group()) == acc else m.group(), name or "").replace("_", " ")
    designation = _post_16s_strain_designation(rest)
    rest = re.sub(r"\s+outgroup\s+for\s+.*$", "", rest, flags=re.I)
    rest = re.sub(r"\s+16S.*$", "", rest)
    rest = re.sub(r"\s+\(?outgroup\)?\s*$", "", rest, flags=re.I)
    rest = re.sub(r"\s+gene\s+for\s*$", "", rest, flags=re.I)
    rest = re.sub(r"\s+strain[: ]+", " ", rest)
    toks = rest.split()
    if len(toks) >= 2 and toks[0].lower() == toks[1].lower():
        toks.pop(0)
    if toks and modal and toks[0].lower() == modal.lower():
        toks[0] = toks[0][0] + "."
    lab = " ".join(toks)
    if designation and designation.lower() not in lab.lower():
        lab = " ".join((lab, designation))
    if len(lab) > REF_LABEL_CHARS:
        lab = lab[:REF_LABEL_CHARS].rsplit(" ", 1)[0]
    src = (src_map or {}).get(_acckey(acc), "") if acc else ""
    if src:
        if len(src) > REF_SOURCE_CHARS:
            src = (src[:REF_SOURCE_CHARS - 1].rsplit(" ", 1)[0] or src[:REF_SOURCE_CHARS - 1]) + "…"
        lab += f" [{src}]"
    return (lab + " " + _display_accession(acc)) if acc else lab


def _refuse(code: str, detail: str) -> "NoReturn":
    import sys as _s
    _s.stderr.write(f"{code}: {detail}\n")
    raise SystemExit(2)


def _require_readable(path: str, what: str) -> None:
    import os as _o
    if not path or not _o.path.isfile(path):
        _refuse("INPUT_NOT_FOUND", f"{what} {path!r} is not a readable file")


def _require_writable_parent(path: str, what: str) -> None:
    import os as _o
    parent = _o.path.dirname(_o.path.abspath(path)) or "."
    if not _o.path.isdir(parent) or not _o.access(parent, _o.W_OK):
        _refuse("OUTPUT_NOT_WRITABLE", f"cannot write {what} under {parent!r}")


def _write_recovery_receipt(path, payload):
    """Durably replace the recovery receipt without exposing a partial JSON document."""
    tmp = path + ".tmp"
    if os.path.exists(tmp):
        raise OSError(f"stale recovery receipt staging file {os.path.basename(tmp)!r}")
    try:
        with open(tmp, "x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _backup_output(path, backup):
    """Copy one prior final byte-for-byte to an exclusive, fsynced recovery file."""
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as source, open(backup, "xb") as target:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            target.write(chunk)
            digest.update(chunk)
            size += len(chunk)
        target.flush()
        os.fsync(target.fileno())
    return digest.hexdigest(), size


def _require_publication_clear(staged_to_final, recovery_path):
    """Fail closed before staging when an earlier publication needs recovery."""
    recovery_tmp = recovery_path + ".tmp"
    if os.path.exists(recovery_path) or os.path.exists(recovery_tmp):
        _refuse(
            "OUTPUT_PUBLICATION_RECOVERY_PENDING",
            f"recovery evidence {os.path.basename(recovery_path)!r} already exists; "
            "inspect and resolve it before another publication attempt",
        )
    for _staged, final in staged_to_final:
        backup = final + ".prepublish.bak"
        if os.path.exists(backup):
            _refuse(
                "OUTPUT_PUBLICATION_RECOVERY_PENDING",
                f"backup {os.path.basename(backup)!r} already exists; "
                "inspect and resolve it before another publication attempt",
            )


def _publish_output_set(staged_to_final, recovery_path):
    """Publish a related output set with bounded rollback and explicit recovery evidence.

    Individual os.replace calls are atomic; the related-file set is not. Before the first final
    is replaced, existing finals are copied to exclusive, fsynced backups and a recovery receipt
    is committed. A publication error restores every prior final (or removes newly created ones).
    If restoration itself fails, remaining backups and the receipt are deliberately preserved.
    """
    records = []
    backups = []
    _require_publication_clear(staged_to_final, recovery_path)

    try:
        for staged, final in staged_to_final:
            existed = os.path.exists(final)
            backup = final + ".prepublish.bak"
            original_sha256 = ""
            original_bytes = 0
            if existed:
                original_sha256, original_bytes = _backup_output(final, backup)
                backups.append(backup)
            records.append({
                "final": os.path.basename(final),
                "staged": os.path.basename(staged),
                "existed_before": existed,
                "backup": os.path.basename(backup) if existed else "",
                "original_sha256": original_sha256,
                "original_bytes": original_bytes,
            })
        recovery = {
            "schema": "placement-output-publication-recovery-v1",
            "status": "PREPARED",
            "outputs": records,
            "publication_error": "",
            "rollback_errors": [],
        }
        _write_recovery_receipt(recovery_path, recovery)
    except (OSError, UnicodeError, TypeError, ValueError) as exc:
        cleanup_errors = []
        for _staged, final in staged_to_final:
            backup = final + ".prepublish.bak"
            if os.path.exists(backup):
                try:
                    os.unlink(backup)
                except OSError as cleanup_exc:
                    cleanup_errors.append(
                        f"{os.path.basename(backup)}: "
                        f"{type(cleanup_exc).__name__}: {cleanup_exc}"
                    )
        cleanup_detail = (
            "; backup cleanup also failed: " + "; ".join(cleanup_errors)
            if cleanup_errors else ""
        )
        _refuse(
            "OUTPUT_PUBLICATION_PREPARE_FAILED",
            f"final outputs were not modified; recovery preparation failed "
            f"({type(exc).__name__}: {exc}){cleanup_detail}",
        )

    try:
        for staged, final in staged_to_final:
            os.replace(staged, final)
    except OSError as publication_error:
        recovery["status"] = "ROLLBACK_IN_PROGRESS"
        recovery["publication_error"] = (
            f"{type(publication_error).__name__}: {publication_error}"
        )
        receipt_warnings = []
        try:
            _write_recovery_receipt(recovery_path, recovery)
        except OSError as exc:
            receipt_warnings.append(
                f"rollback-start receipt update: {type(exc).__name__}: {exc}"
            )

        rollback_errors = []
        for record, (_staged, final) in zip(records, staged_to_final):
            backup = final + ".prepublish.bak"
            try:
                if record["existed_before"]:
                    if not os.path.exists(backup):
                        raise OSError(f"required backup {os.path.basename(backup)!r} is missing")
                    os.replace(backup, final)
                elif os.path.exists(final):
                    os.unlink(final)
            except OSError as exc:
                rollback_errors.append({
                    "final": os.path.basename(final),
                    "error": f"{type(exc).__name__}: {exc}",
                })
        for staged, _final in staged_to_final:
            if os.path.exists(staged):
                try:
                    os.unlink(staged)
                except OSError as exc:
                    rollback_errors.append({
                        "staged": os.path.basename(staged),
                        "error": f"{type(exc).__name__}: {exc}",
                    })

        if rollback_errors:
            recovery["status"] = "RECOVERY_REQUIRED"
            recovery["rollback_errors"] = rollback_errors
            try:
                _write_recovery_receipt(recovery_path, recovery)
            except OSError as exc:
                rollback_errors.append({
                    "recovery_receipt": os.path.basename(recovery_path),
                    "error": f"{type(exc).__name__}: {exc}",
                })
            _refuse(
                "OUTPUT_PUBLICATION_RECOVERY_REQUIRED",
                f"publication failed and rollback was incomplete; inspect "
                f"{os.path.basename(recovery_path)!r} and preserved .prepublish.bak files; "
                f"errors: {json.dumps(rollback_errors, sort_keys=True)}",
            )

        cleanup_warnings = list(receipt_warnings)
        if os.path.exists(recovery_path):
            try:
                os.unlink(recovery_path)
            except OSError as exc:
                cleanup_warnings.append(
                    f"recovery receipt cleanup: {type(exc).__name__}: {exc}"
                )
        warning_detail = (
            "; recovery bookkeeping warning: " + "; ".join(cleanup_warnings)
            if cleanup_warnings else ""
        )
        _refuse(
            "OUTPUT_PUBLICATION_FAILED_ROLLED_BACK",
            f"publication failed ({type(publication_error).__name__}: {publication_error}); "
            "all prior final outputs were restored and newly created finals were removed"
            + warning_detail,
        )

    cleanup_errors = []
    recovery["status"] = "COMMITTED"
    for backup in backups:
        if os.path.exists(backup):
            try:
                os.unlink(backup)
            except OSError as exc:
                cleanup_errors.append(
                    f"{os.path.basename(backup)}: {type(exc).__name__}: {exc}"
                )
    if os.path.exists(recovery_path):
        try:
            os.unlink(recovery_path)
        except OSError as exc:
            cleanup_errors.append(f"receipt cleanup: {type(exc).__name__}: {exc}")
    if cleanup_errors:
        recovery["status"] = "COMMITTED_CLEANUP_REQUIRED"
        recovery["cleanup_errors"] = cleanup_errors
        receipt_error = ""
        try:
            _write_recovery_receipt(recovery_path, recovery)
        except OSError as exc:
            receipt_error = f"; recovery receipt update failed: {type(exc).__name__}: {exc}"
        _refuse(
            "OUTPUT_PUBLICATION_COMMITTED_CLEANUP_REQUIRED",
            "all final outputs were committed, but recovery-artifact cleanup failed: "
            + "; ".join(cleanup_errors) + receipt_error,
        )


def _read_tree_or_refuse(path: str, what: str = "--graft"):
    try:
        from Bio import Phylo
    except ImportError:
        _refuse("DEPENDENCY_MISSING", "biopython is required for tree I/O (pip install biopython)")
    try:
        t = Phylo.read(path, "newick")
    except Exception as exc:
        _refuse("INPUT_NOT_A_TREE", f"{what} {path!r} did not parse as Newick ({type(exc).__name__}: {exc})")
    tips = t.get_terminals()
    if len(tips) < 2:
        _refuse("INPUT_NOT_A_TREE", f"{what} {path!r} parsed as {len(tips)} tip(s); a placement graft carries queries and references")
    return t, tips


def _ref_label_or_refuse(name, modal, src_map=None):
    """Report conflicting reference accessions with the input tip and a repair hint."""
    try:
        return _ref_label(name, modal, src_map)
    except ValueError as exc:
        if str(exc) != "REFERENCE_ACCESSION_CONFLICT":
            raise
        found = sorted({m.group() for m in _accessions(name)})
        _refuse(
            "REFERENCE_ACCESSION_CONFLICT",
            f"reference tip {name!r} carries {len(found)} accession candidates ({', '.join(found)}); "
            "this is usually two complete records fused into one tip name upstream. "
            "Repair the tip, or drop it from the panel; the label is not guessed.",
        )

def main():
    ap = argparse.ArgumentParser(allow_abbrev=False)  # v9.7.412: no silent prefix matching
    ap.add_argument("--graft", required=True, help="grafted placement newick (epa_result.newick)")
    ap.add_argument("--group", default="cohort")
    ap.add_argument("--neighbors", type=int, default=3, help="N nearest reference tips kept per query")
    ap.add_argument("--host-table", default="",
                    help="strain table (generic TSV: strain/tip_label + host + location + accession). "
                         "Supply this or --aux-table for metadata labels; otherwise tips may be bare. No auto-location.")
    ap.add_argument("--outgroup-substr", default="outgroup",
                    help="substring identifying the outgroup tip (also matched: a genus != the modal ingroup genus)")
    ap.add_argument("--keep-all-refs", action="store_true")
    ap.add_argument("--aux-table", action="append", default=[],
                    help="Explicit TSV with strain, host, region, accession; repeatable; conflicts refused")
    ap.add_argument("--no-aux", action="store_true", help="Disable auxiliary metadata")
    ap.add_argument("--allow-raw-host", action="store_true",
                    help="prefer host_raw/location_raw over the curated host_common/location "
                         "(v9.7.417: the curated columns now win by default, because for "
                         "`folder_parse` rows the raw ones hold a FOLDER LABEL, not a host). Use "
                         "only for a strain table that carries the raw columns alone.")
    ap.add_argument("--family-level", action="store_true",
                    help="multi-genus (family) tree: prune/label every genus normally; only the "
                         "registry outgroup tip is treated as outgroup (keeps full genus names).")
    ap.add_argument("--origin-table", default="", help="TSV: type_strain\tcategory — colors reference tips by isolation origin")
    ap.add_argument("--ref-source-db", default="", help="Explicit SQLite file with record(acc_base, isolation_source, country); no automatic discovery")
    ap.add_argument("--required-reference-table", default="",
                    help="TSV: strain, reference_species. The named species must exist in the "
                         "backbone and is counted first within each query's neighbor quota.")
    ap.add_argument("--bioassay-table", default="",
                    help="Strain-level MEASURED bioassay table (CSV/TSV: strain, anti_Candida, anti_MRSA). "
                         "Query tips only; never applied to reference tips. Not a BGC or compound claim.")
    ap.add_argument(
        "--rect-meta-out",
        default="",
        help="optional renderer-ready TSV with tip, label, category and source columns",
    )
    ap.add_argument("--out-prefix", required=True)
    a = ap.parse_args()
    globals()["_ALLOW_RAW_HOST"] = bool(getattr(a, "allow_raw_host", False))
    _require_readable(a.graft, "--graft")
    metadata_sources = [p for p in [a.host_table, a.origin_table, a.ref_source_db, a.bioassay_table,
                                     a.required_reference_table,
                                     *(a.aux_table if not a.no_aux else [])] if p]
    source_hashes = {}
    for path in [a.graft, *metadata_sources]:
        _require_readable(path, "metadata source")
        with open(path, "rb") as handle:
            source_hashes[path] = hashlib.sha256(handle.read()).hexdigest()
    _require_writable_parent(a.out_prefix + "_pruned.nwk", "--out-prefix")
    if a.rect_meta_out:
        _require_writable_parent(a.rect_meta_out, "--rect-meta-out")

    t, tips = _read_tree_or_refuse(a.graft)
    from Bio import Phylo  # reader helper has already verified this dependency; writer also needs it

    def genus(x):
        pp = re.sub(r"^\s*[A-Z]{2}[ _]?\d+(?:[ _.]?\d+)?\s+", "", (x.name or "").replace("_", " "))
        m = re.match(r"([A-Za-z]+)", pp)
        return m.group(1) if m else ""

    q = [x for x in tips if _is_query(x.name)]
    non_q = [x for x in tips if not _is_query(x.name)]
    import collections
    genera = collections.Counter(genus(x) for x in non_q if genus(x))
    modal = genera.most_common(1)[0][0] if genera else ""
    # on a family tree keep full genus names (many genera → an initial like "A." is ambiguous);
    # on a single-genus tree drop the redundant modal genus to its initial.
    lab_modal = "" if a.family_level else modal

    def is_og(x):
        n = (x.name or "").lower()
        if a.family_level:
            # family-level (multi-genus) tree: ONLY the true registry outgroup is an outgroup;
            # every other genus is a legitimate reference to be pruned/labelled normally.
            return a.outgroup_substr.lower() in n
        return (a.outgroup_substr.lower() in n) or (genus(x) and genus(x) != modal)

    og = [x for x in non_q if is_og(x)]
    refs = [x for x in non_q if x not in og]

    def species_name(x):
        plain = (x.name or "").replace("_", " ")
        match = re.match(r"^([A-Z][a-z-]+)\s+([a-z][a-z-]+)(?:\s|$)", plain)
        return f"{match.group(1)} {match.group(2)}" if match else ""

    required_references = _load_required_references(a.required_reference_table)
    query_ids_in_tree = {_asid(x.name) for x in q}
    if required_references and not query_ids_in_tree.intersection(required_references):
        _refuse("REQUIRED_REFERENCE_TABLE_NO_QUERY_MATCH",
                "none of the declared strains is a query tip in this tree")

    selection_rows = []
    if a.keep_all_refs:
        for r in sorted(refs, key=lambda tip: tip.name or ""):
            selection_rows.append(("", r.name or "", "", "", "keep_all_references"))
    elif q:
        keep = set(id(x) for x in q) | set(id(x) for x in og)
        for qq in q:
            ranked = sorted(refs, key=lambda r: (t.distance(qq, r), r.name or ""))
            selected = []
            required_species = required_references.get(_asid(qq.name))
            if required_species:
                required_candidates = [r for r in ranked if species_name(r) == required_species]
                if not required_candidates:
                    _refuse("REQUIRED_REFERENCE_NOT_IN_BACKBONE",
                            f"{_asid(qq.name)} requires {required_species}, which is absent")
                selected.append((required_candidates[0], "workbook_required_species"))
            for candidate in ranked:
                if any(candidate is chosen for chosen, _mode in selected):
                    continue
                if len(selected) >= max(1, a.neighbors):
                    break
                selected.append((candidate, "nearest_per_query"))
            for rank, (r, mode) in enumerate(selected, 1):
                keep.add(id(r))
                selection_rows.append((qq.name or "", r.name or "", rank,
                                       f"{t.distance(qq, r):.12g}", mode))
        for x in list(refs):
            if id(x) not in keep:
                try:
                    t.prune(x)
                except Exception as exc:
                    raise ValueError(f"REFERENCE_PRUNE_FAILED:{x.name}:{exc}") from exc

    hosts = _load_hosts(_find_host_table(a.host_table))
    # v9.7.418: fold in whatever `--aux-table` supplies (repeatable). Values fill only EMPTY fields
    # from --host-table; a conflicting non-empty value is refused, not silently preferred. --no-aux
    # disables the fold for a strictly reproducible re-run of an older figure.
    # (The .417 text here referred to an `AUX_TABLES` constant and to auto-discovered deposited/
    # tree-metadata tables. Both were removed when this tool was genericised in the same cut -- the
    # tool no longer knows any workspace filename -- so the comment described behaviour that had
    # already been deleted. Corrected rather than deleted, because the precedence rule it states is
    # still the one callers need to know.)
    if not getattr(a, "no_aux", False):
        _aux = _load_aux(a.aux_table)
        _added = 0
        # Count only fields that enrich query tips in this tree.
        _tip_ids = {_asid(x.name) for x in q}
        _offtree_strains = set()      # STRAINS, not fields — see the message below
        for _sid, _rec in _aux.items():
            _cur = hosts.setdefault(_sid, {"host": "", "region": "", "acc": ""})
            for _k in ("host", "region", "acc"):
                # `_clean` here, not truthiness: a curated cell holding the literal "unknown" is a
                # PLACEHOLDER, not a value, and treating it as present blocked the deposited record
                # from filling it (query_unknown_region location="unknown" while its GenBank geo_loc_name is
                # "Canada: Ontario").
                if _rec.get(_k) and _clean(_cur.get(_k)) and _rec[_k] != _clean(_cur[_k]):
                    raise ValueError("HOST_METADATA_CONFLICT")
                if _rec.get(_k) and not _clean(_cur.get(_k)):
                    _cur[_k] = _rec[_k]
                    if _sid in _tip_ids:
                        _added += 1
                    else:
                        _offtree_strains.add(_sid)
        if _added or _offtree_strains:
            _msg = (f"[ggtree-inputs] aux metadata: filled {_added} empty field(s) on tips in this "
                    f"tree, from explicit auxiliary tables")
            if _offtree_strains:
                # Shared tables may legitimately include other cohorts.
                _msg += (f" ({len(_offtree_strains)} more matched strain(s) not in this tree"
                         + ("; NO tip was enriched — is this the right table?" if not _added else "")
                         + ")")
            sys.stdout.write(_msg + "\n")
    # v9.7.418: the failure mode this tool has is SILENT — with no --host-table and no --aux-table it
    # exits 0 and writes a perfectly well-formed annotation whose every query label is a bare id.
    # That is indistinguishable, downstream, from a cohort that genuinely has no metadata, and it is
    # what a bare invocation now does by default. Say so once, on stderr, without failing: a caller
    # rendering an exploratory tree with no metadata is doing nothing wrong.
    query_ids = {_asid(x.name) for x in t.get_terminals() if _is_query(x.name)}
    if query_ids and not any(any((hosts.get(aid) or {}).get(k) for k in ("host", "acc", "region")) for aid in query_ids):
        sys.stderr.write("[ggtree-inputs] NOTE: no query carries host/accession metadata or location — every "
                         "query tip will render as a bare id. Pass --host-table (and --aux-table) "
                         "if that is not intended; there is no auto-location.\n")
    # v9.7.423: bioassay is strain-level MEASURED activity, requested explicitly and applied to
    # query tips only -- never to a reference/type-strain tip.
    bioassay = _load_bioassay(a.bioassay_table)
    if a.bioassay_table and query_ids and not any(aid in bioassay for aid in query_ids):
        sys.stderr.write("[ggtree-inputs] NOTE: --bioassay-table given but no query strain in this "
                         "tree matched it -- every query's bioassay_status will read NOT_RECORDED. "
                         "Is this the right table for this cohort?\n")
    origins = _load_origins(a.origin_table)
    ref_src, ref_fields = _load_ref_source_bundle(a.ref_source_db)
    reference_labels = {x.name: _ref_label_or_refuse(x.name, lab_modal, ref_src)
                        for x in t.get_terminals() if not _is_query(x.name)}
    reference_states = {x.name: _reference_source(x.name, ref_src, bool(a.ref_source_db))
                        for x in t.get_terminals() if not _is_query(x.name)}
    reference_field_states = {
        x.name: _reference_source_fields(x.name, ref_fields, bool(a.ref_source_db))
        for x in t.get_terminals() if not _is_query(x.name)
    }
    # The optional reference metadata source is explicit; make an omitted request visible.
    if reference_states and not a.ref_source_db:
        sys.stderr.write(f"[ggtree-inputs] NOTE: no --ref-source-db, so all {len(reference_states)} "
                         "reference tips are NOT_REQUESTED and will render without their deposited "
                         "isolation source / host / country. Pass --ref-source-db if that is not "
                         "intended; there is no automatic discovery.\n")
    nwk_out = a.out_prefix + "_pruned.nwk"
    ann_out = a.out_prefix + "_ggtree_annotation.tsv"
    selection_out = a.out_prefix + "_reference_selection.tsv"
    receipt_out = a.out_prefix + "_metadata_receipt.json"
    rect_out = a.rect_meta_out
    nwk_tmp = nwk_out + ".tmp"
    ann_tmp = ann_out + ".tmp"
    selection_tmp = selection_out + ".tmp"
    receipt_tmp = receipt_out + ".tmp"
    staged_outputs = [(nwk_tmp, nwk_out), (ann_tmp, ann_out),
                      (selection_tmp, selection_out), (receipt_tmp, receipt_out)]
    rect_tmp = ""
    if rect_out:
        rect_tmp = rect_out + ".tmp"
        staged_outputs.insert(2, (rect_tmp, rect_out))
    final_paths = [os.path.abspath(final) for _staged, final in staged_outputs]
    if len(set(final_paths)) != len(final_paths):
        _refuse("OUTPUT_PATH_CONFLICT", "output paths must be distinct")
    publication_recovery = a.out_prefix + "_publication_recovery.json"
    _require_publication_clear(staged_outputs, publication_recovery)
    Phylo.write(t, nwk_tmp, "newick")
    # v9.7.417: label_id / label_host / label_full are ADDITIVE. label_withloc and label_noloc keep
    # their exact names and meaning so tools/ggtree_placement.R and any existing call site still work.
    hdr = ["tip", "kind", "as_id", "host", "region", "accession", "validation",
           "label_withloc", "label_noloc", "ref_label", "origin",
           "label_id", "label_host", "label_full", "group", "reference_source_status",
           "reference_source", "reference_habitat_status", "reference_habitat",
           "reference_country_status", "reference_country",
           "bioassay_status", "anti_candida", "anti_mrsa", "experiment_id", "sample_id"]
    rect_rows = []
    with open(ann_tmp, "w", encoding="utf-8", newline="") as out:
        out.write("\t".join(hdr) + "\n")
        for x in t.get_terminals():
            n = x.name
            if _is_query(n):
                aid = _asid(n); h = hosts.get(aid, {})
                ho, rg, ac = h.get("host", ""), h.get("region", ""), h.get("acc", "")
                experiment, sample = h.get("experiment", ""), h.get("sample", "")
                # never emit empty "()" when the query is absent from the host table (#5 supplies data)
                st = _label_styles(aid, ho, rg, ac)
                lw, ln = st["withloc"], st["noloc"]
                _ba = bioassay.get(aid)
                if _ba is not None:
                    _cand, _mrsa = _ba["anti_candida"], _ba["anti_mrsa"]
                    _ba_status = "MEASURED" if any(v in {"positive", "negative"} for v in (_cand, _mrsa)) else ("NOT_TESTED" if _cand == _mrsa == "not_tested" else "NOT_RECORDED")
                elif a.bioassay_table:
                    _ba_status, _cand, _mrsa = "NOT_RECORDED", "", ""
                else:
                    _ba_status, _cand, _mrsa = "NOT_REQUESTED", "", ""
                out.write("\t".join([n, "query", aid, ho, rg, ac, "NEIGHBORHOOD", lw, ln, "", "",
                                     st["id"], st["host"], st["full"], a.group, "", "", "", "", "", "",
                                     _ba_status, _cand, _mrsa, experiment, sample]) + "\n")
                rect_rows.append(_rect_metadata_row(n, lw, _clean(ho), _clean(rg)))
            elif x in og or (a.outgroup_substr.lower() in (n or "").lower()):
                _ol = reference_labels[n]
                _fs, _cat, _loc = reference_field_states[n]
                _cat_status = _fs if _fs != "DEPOSITED_METADATA" or _cat else "METADATA_ABSENT"
                _loc_status = _fs if _fs != "DEPOSITED_METADATA" or _loc else "METADATA_ABSENT"
                # bioassay is strain-level MEASURED activity on this project's own isolates only --
                # a reference/outgroup tip is a public comparator and never carries these columns.
                out.write("\t".join([n, "reference", "", "", "", "", "", "", "", _ol, "",
                                     _ol, _ol, _ol, a.group, *reference_states[n],
                                     _cat_status, _cat, _loc_status, _loc, "", "", "", "", ""]) + "\n")
                rect_rows.append(_rect_metadata_row(n, _ol, _cat, _loc))
            else:
                _org = origins.get(_species_of(n), "")
                _rl = reference_labels[n]
                _fs, _cat, _loc = reference_field_states[n]
                _cat_status = _fs if _fs != "DEPOSITED_METADATA" or _cat else "METADATA_ABSENT"
                _loc_status = _fs if _fs != "DEPOSITED_METADATA" or _loc else "METADATA_ABSENT"
                out.write("\t".join([n, "reference", "", "", "", "", "", "", "", _rl, _org,
                                     _rl, _rl, _rl, a.group, *reference_states[n],
                                     _cat_status, _cat, _loc_status, _loc, "", "", "", "", ""]) + "\n")
                rect_rows.append(_rect_metadata_row(n, _rl, _cat, _loc))
    if rect_tmp:
        with open(rect_tmp, "w", encoding="utf-8", newline="") as out:
            writer = _SafeWriter(out, delimiter="\t", lineterminator="\n")
            writer.writerow(["tip", "label", "category", "source", "category_raw",
                             "category_state", "source_raw", "source_state"])
            writer.writerows(rect_rows)
    with open(selection_tmp, "w", encoding="utf-8", newline="") as out:
        writer = _SafeWriter(out, delimiter="\t", lineterminator="\n")
        writer.writerow(["query_tip", "reference_tip", "neighbor_rank",
                         "patristic_distance", "selection_mode"])
        writer.writerows(selection_rows)
    # Bind exact admitted input bytes and outputs without packaging machine-specific absolute paths.
    for path, expected in source_hashes.items():
        with open(path, "rb") as handle:
            if hashlib.sha256(handle.read()).hexdigest() != expected:
                for staged, _final in staged_outputs:
                    if os.path.exists(staged):
                        os.unlink(staged)
                raise ValueError("METADATA_SOURCE_CHANGED_DURING_RUN")
    receipt = {"schema": "placement-metadata-inputs-v1", "sources": [
        {"name": os.path.basename(path), "sha256": digest} for path, digest in source_hashes.items()],
        "outputs": {}, "reference_source_states": {k: v[0] for k, v in reference_states.items()}}
    output_pairs = [(nwk_out, nwk_tmp), (ann_out, ann_tmp),
                    (selection_out, selection_tmp)]
    if rect_out:
        output_pairs.append((rect_out, rect_tmp))
    for final_path, staged_path in output_pairs:
        with open(staged_path, "rb") as handle:
            receipt["outputs"][os.path.basename(final_path)] = hashlib.sha256(handle.read()).hexdigest()
    with open(receipt_tmp, "w", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2)
        handle.write("\n")
    _publish_output_set(
        staged_outputs,
        publication_recovery,
    )
    sys.stdout.write(f"[ggtree-inputs] {a.group}: {len(t.get_terminals())} tips "
                     f"({len(q)} queries) -> {nwk_out} + {ann_out}"
                     + (f" + {rect_out}" if rect_out else "") + "\n")


_TYPED_CODES = frozenset({
    "AUX_METADATA_SCHEMA",
    "AUX_METADATA_IDENTITY_OR_WIDTH",
    "AUX_METADATA_CONFLICT",
    "REFERENCE_ACCESSION_CONFLICT",
    "REFERENCE_SOURCE_ACCESSION_INVALID",
    "REFERENCE_SOURCE_FIELD_INVALID",
    "REFERENCE_SOURCE_CONFLICT",
    "HOST_METADATA_CONFLICT",
    "METADATA_SOURCE_CHANGED_DURING_RUN",
    "BIOASSAY_METADATA_SCHEMA",
    "BIOASSAY_METADATA_IDENTITY",
    "BIOASSAY_METADATA_VALUE",
    "BIOASSAY_METADATA_DUPLICATE",
    "BIOASSAY_METADATA_CONFLICT",
    "REQUIRED_REFERENCE_TABLE_SCHEMA",
    "REQUIRED_REFERENCE_TABLE_WIDTH",
    "REQUIRED_REFERENCE_TABLE_IDENTITY",
    "REQUIRED_REFERENCE_TABLE_CONFLICT",
})


def _run_or_refuse():
    """Run `main()`, converting a typed contract violation into this tool's own refusal.

    Nine call sites in this module raise `ValueError("SOME_TYPED_CODE")` when an input breaks a
    contract -- aux-table schema, reference-source fields, host metadata, a mid-run metadata
    change, an unresolvable accession. Every other malformed-input path here exits through
    `_refuse(code, detail)` with that code on stderr and exit 2. The typed raises did not: they
    escaped as bare tracebacks, so an operator saw a Python stack instead of the contract that
    failed and the exit code was 1, not the tool's refusal code.

    Only the explicit contract-code registry above is converted. Any other `ValueError`, including
    an ALL-CAPS message, is unexpected and keeps its traceback.
    """
    try:
        return main()
    except ValueError as exc:
        code = str(exc)
        if code not in _TYPED_CODES:
            raise
        _refuse(code, "input contract violated; no final outputs were committed. "
                      "The code above names which contract failed; the offending input is the one "
                      "named by the corresponding --option.")


if __name__ == "__main__":
    sys.exit(_run_or_refuse())
