#!/usr/bin/env python3
"""Resolve reference-genome isolation metadata from the deposited NCBI record (strain-level, cited).

Proven method (peer-lane, 2026-09-14): for a genome/nuccore accession, fetch ONLY the record
header + SOURCE feature via NCBI E-utilities efetch with seq_stop=1 (tiny payload, no sequence), then
read the source qualifiers /isolation_source, /host, /country|/geo_loc_name, /strain. This is the
genome's OWN deposited metadata — NOT a species-level guess. It repeatedly differs from the species
type strain (e.g. Micromonospora tulbaghiae CNY-010 = marine algae/Bahamas, while the type is
garlic/South Africa), which is exactly why a species-name join is unsafe.

v9.7.432 (TREES_432_reference_metadata_resolver_ignores_biosample): after the SOURCE feature the
record's OWN linked BioSample is consulted (the /db_xref="BioSample:SAMN…" on the SOURCE feature,
else elink nuccore→biosample; then efetch db=biosample). The BioSample often carries what the
SOURCE feature omits (isolation_source, geo_loc_name, type-material, lat_lon) or carries an explicit
INSDC null such as "missing", which is a CHECKED negative and is preserved verbatim. Every value
names where it came from (``nuccore:/isolation_source`` or ``biosample:SAMN…:isolation_source``)
in the *_provenance columns, and ``checked_biosample`` records which BioSample was read. The
BioSample is the same strain's record, not a species join; its own /strain is gated too.

Claim-safety guards (do not remove):
  * STRAIN GATE: only assign a value if the record's /strain matches the caller's expected strain
    (or the caller passes --trust-title when /strain is absent but the deposited title carries it).
    Never assign one strain's isolation to another strain of the same species. The BioSample's
    strain attribute is gated the same way; a mismatching BioSample contributes nothing.
  * PRESERVE ABSENCE: a deposit with no /isolation_source or /country yields "Not recorded" — never
    fabricate, never fall back to the species description as if it were this strain's origin.
    An explicit INSDC null ("missing", "not collected", …) is a different, checked state: the value
    is kept verbatim and verification_status says STRAIN_CONFIRMED_NULL_DECLARED.
  * DEPOSIT-CITY HEURISTIC: flag a /country whose city is a known culture-collection HQ (Braunschweig
    = DSMZ, Manassas = ATCC, etc.) as SUSPECT_DEPOSIT_LOCALITY — it may be the deposit institution,
    not the collection locality (distinguish collection locality from deposit/sequencing institution).
  * NO SEQUENCE USE: this tool reads metadata only. It never extracts or substitutes sequence
    (16S/genome); a validated query sequence remains a separate, human-gated step. Never use .ab1.
  * TRANSPORT FAILURE IS NOT A VALUE (TREES_432_reference_metadata_resolver_tls_and_silent_row_errors):
    a row whose fetch failed is written with verification_status=ERROR and NO metadata cells, and
    the process exits non-zero with the error count. --continue-on-error keeps exit 0 for a batch
    that is allowed to be partial; the count is still printed.

TLS: the default context is Python's system trust store plus the certifi bundle when certifi is
installed. On a host whose network layer re-signs TLS (CERTIFICATE_VERIFY_FAILED: self-signed
certificate in certificate chain) point SSL_CERT_FILE or REQUESTS_CA_BUNDLE at a PEM that carries
that CA. On macOS the system keychain can be exported with:
  security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain \
      /Library/Keychains/System.keychain ~/Library/Keychains/login.keychain-db > ca.pem
  SSL_CERT_FILE=ca.pem python3 tools/resolve_reference_metadata.py …
SAPOTE_EFETCH_INSECURE=1 disables verification (opt-in, logged). Never silent.

Output: the additive correction-table row shape
  identifier, exact_accession, isolation_source, host, location, geography, evidence_url,
  strain_match_basis, verification_status, unresolved_issue,
  isolation_source_provenance, location_provenance, checked_biosample, type_material
Original inputs are never modified; this emits a NEW correction table for owner review.

Stdlib only (urllib) so it runs in the offline-capable bundle env without extra deps.
Usage:
  python3 resolve_reference_metadata.py --accessions CP129614.1 NZ_CP016174.1
  python3 resolve_reference_metadata.py --tsv worklist.tsv --acc-col chromosome_accession \
        --strain-col strain --out correction_table.tsv
"""
from __future__ import annotations
import argparse, csv, json, os, re, ssl, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
try:  # v9.7.410 CSV formula-cell guard (deposited NCBI text reaches these cells)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
EFETCH = EUTILS + "efetch.fcgi"
ELINK = EUTILS + "elink.fcgi"

KEYCHAIN_HINT = (
    "TLS verification failed. If this host re-signs TLS (self-signed certificate in chain), "
    "export the trusted CAs and point SSL_CERT_FILE at them, e.g. on macOS:\n"
    "  security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain "
    "/Library/Keychains/System.keychain ~/Library/Keychains/login.keychain-db > ca.pem\n"
    "  SSL_CERT_FILE=ca.pem python3 tools/resolve_reference_metadata.py …")

# INSDC/BioSample null-value vocabulary. Kept VERBATIM in the output; only the status changes.
NULL_VOCAB = frozenset({
    "missing", "not collected", "not applicable", "not provided", "restricted access",
    "unknown", "na", "n/a", "none", "not available", "not recorded",
})


def _ssl_ctx():
    """System trust store + certifi (when installed). Env override: SSL_CERT_FILE or
    REQUESTS_CA_BUNDLE (a PEM path). SAPOTE_EFETCH_INSECURE=1 skips verification (logged)."""
    ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    if ca:
        return ssl.create_default_context(cafile=ca)
    if os.environ.get("SAPOTE_EFETCH_INSECURE") == "1":
        sys.stderr.write("[resolve_reference_metadata] WARNING: TLS verification DISABLED "
                         "(SAPOTE_EFETCH_INSECURE=1)\n")
        c = ssl.create_default_context(); c.check_hostname = False; c.verify_mode = ssl.CERT_NONE
        return c
    c = ssl.create_default_context()
    try:
        import certifi  # optional; merges the Mozilla bundle into the system store
        c.load_verify_locations(cafile=certifi.where())
    except Exception as exc:  # certifi absent or unreadable: system store only, recorded for the receipt
        os.environ.setdefault("SAPOTE_TLS_CERTIFI_NOTE", str(exc))
    return c


def _http_get(url: str, timeout: int = 30) -> str:
    """The ONLY network call in this module. Tests monkeypatch this name."""
    with urllib.request.urlopen(url, timeout=timeout, context=_ssl_ctx()) as r:
        return r.read().decode("utf-8", "replace")


def _get_with_retry(url: str, what: str, retries: int = 3, pause: float = 0.34) -> str:
    last = None
    for _ in range(retries):
        try:
            return _http_get(url)
        except Exception as e:  # network hiccup: back off and retry
            last = e
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                break  # a trust failure will not fix itself on retry
            time.sleep(pause * 3)
        time.sleep(pause)  # NCBI courtesy rate (<3 req/s without an API key)
    hint = ("\n" + KEYCHAIN_HINT) if "CERTIFICATE_VERIFY_FAILED" in str(last) else ""
    raise RuntimeError(f"{what} failed: {last}{hint}")


# City -> culture collection HQ (deposit-locality heuristic; extend as needed)
DEPOSIT_CITIES = {
    "braunschweig": "DSMZ", "manassas": "ATCC", "teddington": "NCTC/NCIMB",
    "utrecht": "CBS/WI", "tsukuba": "NBRC", "wako": "JCM", "daejeon": "KCTC",
    "beijing": "CGMCC (also a real locality — check)",
}

CONTINENT = {  # minimal country -> geography bin; owner rules on edge cases
    "usa": "US", "united states": "US", "canada": "Canada",
}


def efetch_source(accession: str, retries: int = 3, pause: float = 0.34) -> str:
    """Return the GenBank flat-file text (header + first base) for one accession."""
    params = {"db": "nuccore", "id": accession, "rettype": "gbwithparts",
              "retmode": "text", "seq_start": "1", "seq_stop": "1"}
    url = EFETCH + "?" + urllib.parse.urlencode(params)
    return _get_with_retry(url, f"efetch nuccore {accession}", retries, pause)


def elink_biosample(accession: str, retries: int = 3, pause: float = 0.34) -> str:
    """BioSample UID linked from a nuccore accession via elink, or "" when none is linked."""
    params = {"dbfrom": "nuccore", "db": "biosample", "id": accession, "retmode": "json"}
    url = ELINK + "?" + urllib.parse.urlencode(params)
    body = _get_with_retry(url, f"elink nuccore->biosample {accession}", retries, pause)
    try:
        data = json.loads(body)
        for ls in data.get("linksets", []):
            for ldb in ls.get("linksetdbs", []):
                if ldb.get("dbto") == "biosample" and ldb.get("links"):
                    return str(ldb["links"][0])
    except (ValueError, AttributeError, TypeError) as e:
        raise RuntimeError(f"elink response for {accession} not parseable: {e}")
    return ""


def efetch_biosample(biosample_id: str, retries: int = 3, pause: float = 0.34) -> str:
    """BioSample XML (BioSampleSet) for a SAMN accession or a BioSample UID."""
    params = {"db": "biosample", "id": biosample_id, "retmode": "xml"}
    url = EFETCH + "?" + urllib.parse.urlencode(params)
    return _get_with_retry(url, f"efetch biosample {biosample_id}", retries, pause)


_Q = lambda name, text: (m.group(1).strip() if (m := re.search(
    rf'/{name}="([^"]*)"', text)) else "")


def parse_source(gb_text: str) -> dict:
    # isolate the SOURCE feature block (from 'source' to the next feature line)
    m = re.search(r"\n\s{5}source\s.*?(?=\n\s{5}\S)", gb_text, re.S)
    block = m.group(0) if m else gb_text
    country = _Q("country", block) or _Q("geo_loc_name", block)
    bs = re.search(r'/db_xref="BioSample:([A-Z]+\d+)"', block)
    return {
        "isolation_source": _Q("isolation_source", block),
        "host": _Q("host", block),
        "country": country,
        "strain": _Q("strain", block),
        "biosample": bs.group(1) if bs else "",
    }


def parse_biosample(xml_text: str) -> dict:
    """Attributes of ONE BioSample as deposited. Keys are harmonized_name when present, else
    attribute_name. Returns {} for an empty set; raises on malformed XML or >1 sample."""
    root = ET.fromstring(xml_text)
    samples = root.findall(".//BioSample")
    if not samples:
        return {}
    if len(samples) > 1:
        raise RuntimeError(f"BioSample response carries {len(samples)} samples; expected one")
    s = samples[0]
    out = {"accession": s.get("accession", "")}
    if not out["accession"]:
        for i in s.findall("./Ids/Id"):
            if i.get("db") == "BioSample" and (i.text or "").strip():
                out["accession"] = i.text.strip(); break
    attrs = {}
    for a in s.findall("./Attributes/Attribute"):
        key = (a.get("harmonized_name") or a.get("attribute_name") or "").strip()
        val = " ".join((a.text or "").split())
        if key and key not in attrs:
            attrs[key] = val
    out["attributes"] = attrs
    out["strain"] = attrs.get("strain", "")
    out["isolation_source"] = attrs.get("isolation_source", "")
    out["geo_loc_name"] = attrs.get("geo_loc_name", "")
    out["host"] = attrs.get("host", "")
    out["type_material"] = attrs.get("type-material", "") or attrs.get("type_material", "")
    return out


def fetch_biosample_for(accession: str, source_biosample: str) -> dict:
    """The record's own BioSample: the SOURCE /db_xref when present, else elink. {} if none."""
    sid = source_biosample or elink_biosample(accession)
    if not sid:
        return {}
    return parse_biosample(efetch_biosample(sid))


def deposit_city_flag(country: str) -> str:
    city = country.split(":")[-1].strip().lower() if country else ""
    for k, v in DEPOSIT_CITIES.items():
        if k in city:
            return f"SUSPECT_DEPOSIT_LOCALITY ({v} HQ) — confirm collection vs deposit"
    return ""


def is_null_vocab(value: str) -> bool:
    return value.strip().lower() in NULL_VOCAB if value else False


def _refuse(accession, status, basis, unresolved):
    return dict(accession=accession, status=status, basis=basis, unresolved=unresolved,
                isolation_source="", host="", country="",
                isolation_source_provenance="", location_provenance="",
                checked_biosample="", type_material="")


def resolve(accession: str, expected_strain: str = "", trust_title: bool = False,
            use_biosample: bool = True) -> dict:
    gb = efetch_source(accession)
    q = parse_source(gb)
    got = q["strain"]
    # STRAIN GATE (nuccore SOURCE)
    if expected_strain:
        if got and got.strip().lower() != expected_strain.strip().lower():
            basis = f"STRAIN MISMATCH: record /strain={got!r} != expected {expected_strain!r}"
            return _refuse(accession, "REFUSED_STRAIN_MISMATCH", basis,
                           "record strain differs from expected — do not assign")
        if not got and not trust_title:
            return _refuse(accession, "REFUSED_NO_STRAIN_IN_RECORD",
                           "/strain absent; pass --trust-title only if the deposited title carries it",
                           "no /strain to confirm identity")
    basis = (f"/strain {got} = deposited genome strain" if got
             else "matched by deposited title (/strain absent)")

    # Nuccore SOURCE values first, each with its provenance.
    src, src_prov = "", ""
    if q["isolation_source"]:
        src, src_prov = q["isolation_source"], "nuccore:/isolation_source"
    elif q["host"]:
        src, src_prov = "host:" + q["host"], "nuccore:/host"
    country, loc_prov = q["country"], ("nuccore:/country|/geo_loc_name" if q["country"] else "")
    host = q["host"]
    unresolved = []

    # BioSample: the SAME record's linked sample, strain-gated, never a species join.
    checked, type_material = "", ""
    if use_biosample:
        bs = fetch_biosample_for(accession, q["biosample"])
        if bs:
            checked = bs.get("accession", "") or "linked"
            gate = expected_strain or got
            bs_strain = bs.get("strain", "")
            if gate and bs_strain and bs_strain.strip().lower() != gate.strip().lower():
                unresolved.append(f"BIOSAMPLE_STRAIN_MISMATCH: {checked} strain={bs_strain!r} "
                                  f"!= {gate!r}; BioSample values not assigned")
            else:
                tag = f"biosample:{checked}"
                type_material = bs.get("type_material", "")
                if not src and bs.get("isolation_source"):
                    src, src_prov = bs["isolation_source"], f"{tag}:isolation_source"
                if not host and bs.get("host"):
                    host = bs["host"]
                    if not src:
                        src, src_prov = "host:" + host, f"{tag}:host"
                if not country and bs.get("geo_loc_name"):
                    country, loc_prov = bs["geo_loc_name"], f"{tag}:geo_loc_name"
                if bs_strain and not got:
                    basis += f"; BioSample {checked} strain {bs_strain} agrees"

    flag = deposit_city_flag(country)
    if flag:
        unresolved.append(flag)
    if not src and not country:
        status = "STRAIN_CONFIRMED_NO_METADATA"
        unresolved.append("deposit carries no isolation_source/country"
                          + (f" (BioSample {checked} checked)" if checked else " (no BioSample linked)"
                             if use_biosample else " (BioSample not consulted)"))
    elif (not src or is_null_vocab(src)) and (not country or is_null_vocab(country)):
        status = "STRAIN_CONFIRMED_NULL_DECLARED"
        unresolved.append("deposit declares an explicit null value; kept verbatim")
    else:
        status = "STRAIN_CONFIRMED"
    return dict(accession=accession, status=status, basis=basis,
                isolation_source=src or "Not recorded",
                host=host, country=country or "Not recorded",
                unresolved="; ".join(unresolved),
                isolation_source_provenance=src_prov, location_provenance=loc_prov,
                checked_biosample=checked, type_material=type_material)


OUT_COLS = ["identifier", "exact_accession", "isolation_source", "host", "location",
            "geography", "evidence_url", "strain_match_basis", "verification_status", "unresolved_issue",
            "isolation_source_provenance", "location_provenance", "checked_biosample", "type_material"]


def to_row(identifier: str, r: dict) -> dict:
    return {
        "identifier": identifier, "exact_accession": r["accession"],
        "isolation_source": r["isolation_source"], "host": r.get("host", ""),
        "location": r["country"], "geography": "",  # owner/rules map country->continent bin
        "evidence_url": f"https://www.ncbi.nlm.nih.gov/nuccore/{r['accession']}",
        "strain_match_basis": r["basis"], "verification_status": r["status"],
        "unresolved_issue": r.get("unresolved", ""),
        "isolation_source_provenance": r.get("isolation_source_provenance", ""),
        "location_provenance": r.get("location_provenance", ""),
        "checked_biosample": r.get("checked_biosample", ""),
        "type_material": r.get("type_material", ""),
    }


def error_row(identifier: str, accession: str, err: Exception) -> dict:
    """A transport/parse failure: status ERROR, every metadata cell EMPTY (never 'Not recorded')."""
    return {"identifier": identifier, "exact_accession": accession,
            "verification_status": "ERROR", "unresolved_issue": str(err).splitlines()[0]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--accessions", nargs="*", default=[])
    ap.add_argument("--tsv"); ap.add_argument("--acc-col", default="chromosome_accession")
    ap.add_argument("--id-col", default="identifier"); ap.add_argument("--strain-col", default="")
    ap.add_argument("--trust-title", action="store_true")
    ap.add_argument("--no-biosample", action="store_true",
                    help="read only the nuccore SOURCE feature (pre-v9.7.432 behaviour)")
    ap.add_argument("--continue-on-error", "--allow-partial", dest="continue_on_error",
                    action="store_true",
                    help="exit 0 even when some rows are ERROR (the count is still printed)")
    ap.add_argument("--out", default="-")
    a = ap.parse_args(argv)

    jobs = []  # (identifier, accession, expected_strain)
    for acc in a.accessions:
        jobs.append((acc, acc, ""))
    if a.tsv:
        for row in csv.DictReader(open(a.tsv, newline=""), delimiter="\t"):
            acc = (row.get(a.acc_col) or "").strip()
            if not acc:
                continue
            jobs.append((row.get(a.id_col, acc), acc,
                         (row.get(a.strain_col) or "").strip() if a.strain_col else ""))

    out = sys.stdout if a.out == "-" else open(a.out, "w", newline="")
    w = _SafeDictWriter(out, fieldnames=OUT_COLS, delimiter="\t"); w.writeheader()
    errors = 0
    for ident, acc, strain in jobs:
        try:
            w.writerow(to_row(ident, resolve(acc, strain, a.trust_title,
                                             use_biosample=not a.no_biosample)))
        except Exception as e:
            errors += 1
            sys.stderr.write(f"[resolve_reference_metadata] ERROR {ident} ({acc}): {e}\n")
            w.writerow(error_row(ident, acc, e))
        out.flush()
    if out is not sys.stdout:
        out.close()
    if errors:
        sys.stderr.write(f"[resolve_reference_metadata] {errors}/{len(jobs)} row(s) ERROR"
                         + (" — continuing (--continue-on-error)\n" if a.continue_on_error
                            else " — exiting non-zero; the table is NOT resolved\n"))
        return 0 if a.continue_on_error else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
