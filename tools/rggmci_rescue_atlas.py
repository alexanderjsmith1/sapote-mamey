#!/usr/bin/env python3
"""Build the post-seal RG-GMCI complementary-rescue atlas."""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.rggmci_rescue_atlas import run  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", required=True, help="TSV/CSV with complete identity_a and identity_b")
    parser.add_argument("--loci", required=True, help="TSV/CSV locus logic table with complete_identity")
    parser.add_argument("--hits-root", required=True, help="root containing MIBIG_HITS_EXACT_IDENTITY.tsv files")
    parser.add_argument("--mibig", required=True, help="MIBiG GenBank .tar.gz archive")
    parser.add_argument("--out", required=True, help="new or existing output directory")
    args = parser.parse_args(argv)
    receipt = run(args.pairs, args.loci, args.hits_root, args.mibig, args.out)
    sys.stdout.write(json.dumps(receipt, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
