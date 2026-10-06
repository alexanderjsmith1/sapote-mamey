#!/usr/bin/env python3
"""Render supplied locus correspondences without running a biological search."""
from pathlib import Path
import argparse
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.figures.locus_comparison import render
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _console import emit  # noqa: E402


def main():
    """Parse the portable comparison manifest and destination."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--outdir', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = render(args.input, args.outdir)
    except (ValueError, FileNotFoundError, FileExistsError) as exc:
        parser.exit(2, f'comparison refused: {exc}\n')
    emit(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
