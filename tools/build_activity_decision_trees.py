#!/usr/bin/env python3
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.activity_decision_tree import build_activity_decision_trees

def main() -> int:
    parser = argparse.ArgumentParser(description="Build exact-identity activity decision trees")
    parser.add_argument("--leads-tsv", type=Path, required=True)
    parser.add_argument("--receipt-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    build_activity_decision_trees(args.leads_tsv, args.receipt_root, args.output_dir)
    return 0

if __name__ == "__main__": raise SystemExit(main())
