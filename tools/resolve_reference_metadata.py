#!/usr/bin/env python3
"""Resolve reference-genome isolation metadata from the deposited NCBI record (strain-level, cited).

Proven method (peer-lane, 2026-09-14): for a genome/nuccore accession, fetch ONLY the record
header + SOURCE feature via NCBI E-utilities efetch with seq_stop=1 (tiny payload, no sequence), then
read the source qualifiers /isolation_source, /host, /country|/geo_loc_name, /strain. This is the
genome's OWN deposited metadata — NOT a species-level guess. It repeatedly differs from the species
type strain (e.g. Micromonospora tulbaghiae CNY-010 = marine algae/Bahamas, while the type is
garlic/South Africa), which is exactly why a species-name join is unsafe.

Claim-safety guards (do not remove):
  * STRAIN GATE: only assign a value if the record's /strain matches the caller's expected strain
    (or the caller passes --trust-title when /strain is absent but the deposited title carries it).
    Never assign one strain's isolation to another strain of the same species.
  * PRESERVE ABSENCE: a deposit with no /isolation_source or /country yields "Not recorded" — never
    fabricate, never fall back to the species description as if it were this strain's origin.
  * DEPOSIT-CITY HEURISTIC: flag a /country whose city is a known culture-collection HQ (Braunschweig
    = DSMZ, Manassas = ATCC, etc.) as SUSPECT_DEPOSIT_LOCALITY — it may be the deposit institution,
    not the collection locality (distinguish collection locality from deposit/sequencing institution).
  * NO SEQUENCE USE: this tool reads metadata only. It never extracts or substitutes sequence
    (16S/genome); a validated query sequence remains a separate, human-gated step. Never use .ab1.

Output: the additive correction-table row shape
  identifier, exact_accession, isolation_source, host, location, geography, evidence_url,
  strain_match_basis, verification_status, unresolved_issue
Original inputs are never modified; this emits a NEW correction table for owner review.

Stdlib only (urllib) so it runs in the offline-capable bundle env without extra deps.
Usage:
  python3 resolve_reference_metadata.py --accessions CP129614.1 NZ_CP016174.1
  python3 resolve_reference_metadata.py --tsv worklist.tsv --acc-col chromosome_accession \
        --strain-col strain --out correction_table.tsv
"""
from __future__ import annotations
import argparse, csv, os, re, ssl, sys, time, urllib.parse, urllib.request
try:  # v9.7.410 CSV formula-cell guard (deposited NCBI text reaches these cells)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

def _ssl_ctx():
    """Default: system trust store. In a TLS-intercepting proxy env (self-signed cert in the
    chain — common in sandboxed CI), point SSL_CERT_FILE/REQUESTS_CA_BUNDLE at the proxy CA, or set
    SAPOTE_EFETCH_INSECURE=1 to skip verification (opt-in; logged). Never silent."""
    ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    if ca:
        return ssl.create_default_context(cafile=ca)
    if os.environ.get("SAPOTE_EFETCH_INSECURE") == "1":
        sys.stderr.write("[resolve_reference_metadata] WARNING: TLS verification DISABLED "
                         "(SAPOTE_EFETCH_INSECURE=1)\n")
        c = ssl.create_default_context(); c.check_hostname = False; c.verify_mode = ssl.CERT_NONE
        return c
    return ssl.create_default_context()

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
    last = None
    ctx = _ssl_ctx()
    for _ in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30, context=ctx) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # network hiccup: back off and retry
            last = e; time.sleep(pause * 3)
        time.sleep(pause)  # NCBI courtesy rate (<3 req/s without an API key)
    raise RuntimeError(f"efetch failed for {accession}: {last}")

_Q = lambda name, text: (m.group(1).strip() if (m := re.search(
    rf'/{name}="([^"]*)"', text)) else "")

def parse_source(gb_text: str) -> dict:
    # isolate the SOURCE feature block (from 'source' to the next feature line)
    m = re.search(r"\n\s{5}source\s.*?(?=\n\s{5}\S)", gb_text, re.S)
    block = m.group(0) if m else gb_text
    country = _Q("country", block) or _Q("geo_loc_name", block)
    return {
        "isolation_source": _Q("isolation_source", block),
        "host": _Q("host", block),
        "country": country,
        "strain": _Q("strain", block),
    }

def deposit_city_flag(country: str) -> str:
    city = country.split(":")[-1].strip().lower() if country else ""
    for k, v in DEPOSIT_CITIES.items():
        if k in city:
            return f"SUSPECT_DEPOSIT_LOCALITY ({v} HQ) — confirm collection vs deposit"
    return ""

def resolve(accession: str, expected_strain: str = "", trust_title: bool = False) -> dict:
    gb = efetch_source(accession)
    q = parse_source(gb)
    got = q["strain"]
    # STRAIN GATE
    if expected_strain:
        if got and got.strip().lower() != expected_strain.strip().lower():
            basis = f"STRAIN MISMATCH: record /strain={got!r} != expected {expected_strain!r}"
            return dict(accession=accession, status="REFUSED_STRAIN_MISMATCH",
                        basis=basis, **{k: "" for k in ("isolation_source","host","country")},
                        unresolved="record strain differs from expected — do not assign")
        if not got and not trust_title:
            return dict(accession=accession, status="REFUSED_NO_STRAIN_IN_RECORD",
                        basis="/strain absent; pass --trust-title only if the deposited title carries it",
                        isolation_source="", host="", country="",
                        unresolved="no /strain to confirm identity")
    basis = (f"/strain {got} = deposited genome strain" if got
             else "matched by deposited title (/strain absent)")
    src = q["isolation_source"] or (("host:" + q["host"]) if q["host"] else "")
    unresolved = deposit_city_flag(q["country"])
    if not src and not q["country"]:
        status = "STRAIN_CONFIRMED_NO_METADATA"
        unresolved = unresolved or "deposit carries no isolation_source/country"
    else:
        status = "STRAIN_CONFIRMED"
    return dict(accession=accession, status=status, basis=basis,
                isolation_source=src or "Not recorded",
                host=q["host"], country=q["country"] or "Not recorded",
                unresolved=unresolved)

OUT_COLS = ["identifier","exact_accession","isolation_source","host","location",
            "geography","evidence_url","strain_match_basis","verification_status","unresolved_issue"]

def to_row(identifier: str, r: dict) -> dict:
    return {
        "identifier": identifier, "exact_accession": r["accession"],
        "isolation_source": r["isolation_source"], "host": r.get("host",""),
        "location": r["country"], "geography": "",  # owner/rules map country->continent bin
        "evidence_url": f"https://www.ncbi.nlm.nih.gov/nuccore/{r['accession']}",
        "strain_match_basis": r["basis"], "verification_status": r["status"],
        "unresolved_issue": r.get("unresolved",""),
    }

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--accessions", nargs="*", default=[])
    ap.add_argument("--tsv"); ap.add_argument("--acc-col", default="chromosome_accession")
    ap.add_argument("--id-col", default="identifier"); ap.add_argument("--strain-col", default="")
    ap.add_argument("--trust-title", action="store_true")
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
    for ident, acc, strain in jobs:
        try:
            w.writerow(to_row(ident, resolve(acc, strain, a.trust_title)))
        except Exception as e:
            w.writerow({"identifier": ident, "exact_accession": acc,
                        "verification_status": "ERROR", "unresolved_issue": str(e)})
        out.flush()
    if out is not sys.stdout:
        out.close()

if __name__ == "__main__":
    main()
