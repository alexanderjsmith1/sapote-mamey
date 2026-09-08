"""mibig_neighborhoods_api.py — read-only accessor for the packaged MIBiG reference "neighborhoods".

A neighborhood is a complete-linkage clade of MIBiG antimicrobial reference domains of one family
(KS/C/A/AT/glyc/resi) whose within-clade patristic diameter <= 1.5 on an LG FastTree scaffold. Each
neighborhood has a medoid representative. These are STABLE reference partitions (they depend only on the
shipped MIBiG panel, not on any query strain), so an AS-strain domain can be assigned to its nearest
neighborhood to answer "which known antimicrobial machinery does this resemble?".

Provenance + build command: mamey/data/mibig/neighborhoods/PROVENANCE.md (regenerate with tools/mibig_neighborhoods.py).
Claim-safety: neighborhood membership is a class-level HOMOLOGY grouping of biosynthetic machinery — not a
claim of compound production, structure, or activity. Judgment deferred.
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field

_HERE = os.path.dirname(os.path.abspath(__file__))
# v9.7.362: the MIBiG-derived partitions are NO LONGER REDISTRIBUTED in this bundle (MIBiG is
# CC BY 4.0; shipping it inside an MIT code release misstates the licence, and freezing a snapshot
# decouples the engine from the release the operator actually intends to cite). The data is now
# user-provisioned and resolved through mamey.external_data — env var MAMEY_MIBIG_NEIGHBORHOODS_DIR,
# or $MAMEY_DATA_ROOT/mibig/neighborhoods. Rebuildable locally: see docs/EXTERNAL_DATA.md and
# tools/mibig_neighborhoods.py. `_data_dir()` is resolved per call so an operator can provision
# mid-session without reimporting.
from . import external_data as _xd


def _data_dir() -> str:
    p = _xd.resolve("mibig_neighborhoods")
    if p is None:
        # legacy in-tree layout, for trees predating .362 only
        return os.path.join(_HERE, "data", "mibig", "neighborhoods")
    return str(p)
FAMILIES = ("KS", "C", "A", "AT", "glyc", "resi")


@dataclass
class Neighborhood:
    fam: str
    nb_id: str                      # e.g. "KS_N03"
    rep_tip: str = ""               # medoid representative tip
    metabolite: str = ""            # representative's metabolite (class-level hypothesis)
    accession: str = ""             # representative's MIBiG accession
    members: list[str] = field(default_factory=list)


def _tsv_path(fam: str) -> str:
    return os.path.join(_data_dir(), fam, f"{fam}_neighborhoods.tsv")


def load_family(fam: str) -> dict[str, Neighborhood]:
    """Return {nb_id: Neighborhood} for one family. Raises if the family is unknown/unpackaged."""
    if fam not in FAMILIES:
        raise ValueError(f"unknown family {fam!r}; expected one of {FAMILIES}")
    p = _tsv_path(fam)
    if not os.path.exists(p):
        raise FileNotFoundError(p)
    out: dict[str, Neighborhood] = {}
    with open(p, encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        idx = {c: i for i, c in enumerate(header)}
        for ln in fh:
            r = ln.rstrip("\n").split("\t")
            if len(r) < len(header):
                continue
            nb = r[idx["neighborhood"]]
            n = out.setdefault(nb, Neighborhood(fam=fam, nb_id=nb))
            n.members.append(r[idx["tip"]])
            if r[idx["is_rep"]] == "yes":
                n.rep_tip = r[idx["tip"]]
                n.metabolite = r[idx["metabolite"]]
                n.accession = r[idx["accession"]]
    return out


def reps_faa_path(fam: str) -> str:
    """Path to the one-representative-per-neighborhood FASTA (anchor set for overview/focused trees)."""
    return os.path.join(_data_dir(), fam, f"{fam}_reps.faa")


def summary() -> dict[str, int]:
    """{fam: n_neighborhoods} for every packaged family (skips families not present)."""
    out = {}
    for fam in FAMILIES:
        try:
            out[fam] = len(load_family(fam))
        except FileNotFoundError:
            pass
    return out
