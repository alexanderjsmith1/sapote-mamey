#!/usr/bin/env python3
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.thesis_handoff import build_thesis_handoff

def main() -> int:
    parser=argparse.ArgumentParser(description="Build a portable thesis handoff")
    parser.add_argument("--index-tsv",type=Path,required=True)
    parser.add_argument("--input-root",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args();build_thesis_handoff(args.index_tsv,args.input_root,args.output_dir);return 0
if __name__ == "__main__": raise SystemExit(main())
