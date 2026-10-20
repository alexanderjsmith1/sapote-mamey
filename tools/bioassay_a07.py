#!/usr/bin/env python3
"""A07 portable bioassay paper renderer: every fraction, Candida against MRSA."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mamey.bioassay_paper import cli
if __name__ == "__main__":
    cli("A07",Path(__file__).with_suffix(".R"))
