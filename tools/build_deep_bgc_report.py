#!/usr/bin/env python3
"""Build one exact-identity deep BGC report from portable inputs."""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.deep_bgc_report import build_deep_report

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--locus-json", type=Path, required=True)
    parser.add_argument("--evidence-tsv", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    build_deep_report(args.locus_json, args.output_dir, args.evidence_tsv)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
