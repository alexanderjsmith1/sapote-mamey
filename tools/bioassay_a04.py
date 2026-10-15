#!/usr/bin/env python3
"""A04 portable bioassay paper renderer."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mamey.bioassay_paper import cli
if __name__ == "__main__":
    cli("A04",Path(__file__).with_suffix(".R"))
