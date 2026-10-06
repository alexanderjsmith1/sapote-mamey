#!/usr/bin/env python3
"""Provision a source-bound scanner subset from an operator's Pfam-A.hmm; no network.

Preset 35/148 selectors are pinned from existing model-header accession evidence.
This builds a new-source artifact, not an attestation of historical exact reconstruction.
Missing/version-mismatched models fail before publication; gathering cutoffs are copied unchanged.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def binding(path):
    path = Path(path).resolve()
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return {'path': str(path), 'sha256': h.hexdigest()}


def build(source, out, accessions, *, hmmfetch='hmmfetch', hmmpress='hmmpress'):
    source, out, accessions = Path(source).resolve(), Path(out).absolute(), Path(accessions).resolve()
    source_receipt, list_receipt = binding(source), binding(accessions)
    selectors = [line.strip() for line in accessions.read_text().splitlines()
                 if line.strip() and not line.lstrip().startswith('#')]
    if not selectors or len(set(selectors)) != len(selectors) or any(
            not re.fullmatch(r'PF\d{5}(?:\.\d+)?', value) for value in selectors):
        raise ValueError('accessions must be nonempty, unique Pfam selectors')
    targets = [out] + [Path(str(out) + suffix) for suffix in ('.h3f', '.h3i', '.h3m', '.h3p')] + [Path(str(out) + '.build_receipt.json')]
    if any(os.path.lexists(p) for p in targets):
        raise ValueError('existing output or index/receipt refused; choose fresh output paths')
    for program in (hmmfetch, hmmpress):
        if not shutil.which(program):
            raise ValueError(f'{program} unavailable; install HMMER separately')
    out.parent.mkdir(parents=True, exist_ok=True)
    published = []
    with tempfile.TemporaryDirectory(prefix='.scanner_build_', dir=out.parent) as td:
        staged = Path(td) / out.name
        with staged.open('wb') as stream:
            for selector in selectors:
                result = subprocess.run([hmmfetch, str(source), selector], capture_output=True, check=True)
                found = re.findall(rb'^ACC\s+(PF\d{5}(?:\.\d+)?)\s*$', result.stdout, re.M)
                if found != [selector.encode()] or len(re.findall(rb'^//\s*$', result.stdout, re.M)) != 1:
                    raise ValueError(f'{selector}: fetched output must contain exactly its one pinned model')
                stream.write(result.stdout)
        subprocess.run([hmmpress, str(staged)], check=True, capture_output=True)
        staged_files = [staged] + [Path(str(staged) + suffix) for suffix in ('.h3f', '.h3i', '.h3m', '.h3p')]
        if any(not p.is_file() for p in staged_files):
            raise ValueError('hmmpress did not produce all four index files')
        if binding(source) != source_receipt or binding(accessions) != list_receipt:
            raise ValueError('source or accession list changed during build')
        receipt = {'status': 'COMPLETE_NEW_SOURCE_BUILD', 'source': source_receipt,
                   'accessions': list_receipt, 'selectors': selectors,
                   'outputs': [{'path': str(target), 'sha256': binding(staging)['sha256']}
                               for target, staging in zip(targets, staged_files)]}
        staged_receipt = Path(td) / 'receipt.json'
        staged_receipt.write_text(json.dumps(receipt, indent=2) + '\n')
        try:
            for staging, target in zip(staged_files + [staged_receipt], targets):
                os.link(staging, target)  # no replacement, including a concurrent claimant
                published.append(target)
        except BaseException:
            for target in reversed(published):
                target.unlink()
            raise
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--out', required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--preset', choices=['35', '148'])
    group.add_argument('--accessions')
    args = parser.parse_args(argv)
    accessions = args.accessions or ROOT / f'bundle_support/scanner_pfam_{args.preset}_accessions.txt'
    try:
        receipt = build(args.source, args.out, accessions)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f'SCANNER_BUILD_REFUSED: {exc}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
