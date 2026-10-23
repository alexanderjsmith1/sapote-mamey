"""Small, read-only input and fail-closed output helpers for figure route drivers."""
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from mamey.csv_safety import SafeDictWriter
from mamey.logging_setup import get_logger
ROOT = Path(__file__).resolve().parents[1]
LOG = get_logger('figure_routes')
_ADMITTED = {}
_DEADLINE = time.monotonic()+1740

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def bind(paths):
    records=[]
    for p in dict.fromkeys(map(Path,paths)):
        key=str(p.resolve());digest=sha(p)
        if key in _ADMITTED and _ADMITTED[key]!=digest:
            raise ValueError('admitted input changed: '+key)
        _ADMITTED[key]=digest
        records.append({'path':key,'sha256':digest})
    return records

def table(path, required):
    with Path(path).open(newline='', encoding='utf-8-sig') as stream:
        r = csv.DictReader(stream, delimiter='\t')
        if not set(required) <= set(r.fieldnames or []):
            raise ValueError(f'{path}: required columns {sorted(required)}')
        rows = list(r)
    if not rows or any(None in r or any(v is None for v in r.values()) for r in rows):
        raise ValueError(f'{path}: empty or malformed table')
    return rows

def unique(rows, key):
    values = [r[key] for r in rows]
    if any(not v.strip() for v in values) or len(values) != len(set(values)):
        raise ValueError(f'empty or duplicate {key}')
    return {r[key]: r for r in rows}

def write_table(path, rows, columns):
    with Path(path).open('x', newline='', encoding='utf-8') as stream:
        w = SafeDictWriter(stream, fieldnames=columns, delimiter='\t', lineterminator='\n')
        w.writeheader(); w.writerows(rows)

def output_dir(path):
    p = Path(path)
    p.mkdir(parents=True, exist_ok=False)
    return p

def number(value, low=None, high=None):
    x = float(value)
    if not math.isfinite(x) or low is not None and x < low or high is not None and x > high:
        raise ValueError(f'invalid numeric value: {value}')
    return x

def command(tool, args):
    p = ROOT/'tools'/tool
    if not p.is_file():
        raise FileNotFoundError(p)
    return [sys.executable, '-B', str(p), *map(str, args)]

def execute(argv, log, env=None):
    settings = os.environ.copy()
    settings.update(PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4', MKL_NUM_THREADS='4')
    settings.update(env or {})
    remaining=_DEADLINE-time.monotonic()
    if remaining<=0: raise TimeoutError('figure route batch exceeded its 29-minute budget')
    with Path(log).open('x', encoding='utf-8') as stream:
        subprocess.run(argv, cwd=ROOT, env=settings, stdout=stream, stderr=subprocess.STDOUT,
                       check=True, timeout=min(1740,remaining))

def receipt(out, tool, inputs, extra=None, *, figures=True):
    out = Path(out)
    products = [p for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'ROUTE_RECEIPT.json']
    if figures:
        for ext in ('.png', '.pdf', '.svg'):
            if not any(p.suffix.lower() == ext for p in products):
                raise ValueError(f'{tool}: missing {ext} output')
    record = dict(tool=tool, inputs=bind(list(inputs)+[Path(__file__)]), outputs=bind(products),
                  runtime_state='completed', visual_qa='NOT_PERFORMED', publication_acceptance='NOT_ESTABLISHED')
    record.update(extra or {})
    with (out/'ROUTE_RECEIPT.json').open('x') as stream:
        json.dump(record, stream, indent=2); stream.write('\n')
    LOG.info('%s completed: %s', tool, out)
    return record

def save(fig, stem, tool):
    from mamey.figure_theme import save_figure_pair
    from mamey.figure_stamp import stamp_file
    png, svg = save_figure_pair(fig, stem, profile='manuscript')
    pdf = Path(stem).with_suffix('.pdf')
    fig.savefig(pdf, bbox_inches='tight', metadata={'Creator': tool})
    for p in (png, svg, pdf):
        stamp_file(p, tool)
    return [png, svg, pdf]
