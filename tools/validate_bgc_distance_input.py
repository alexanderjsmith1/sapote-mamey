"""Validate a candidate complete BGC distance input; this does not fit a layout.

The caller must separately review whether the distances are suitable for an
embedding. A verified receipt binds bytes, not biological interpretation.
"""
import csv
import hashlib
import json
import math
from array import array
from pathlib import Path


def _digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def validate(matrix_path, receipt_path, max_bytes):
    matrix_path, receipt_path = Path(matrix_path), Path(receipt_path)
    before = _digest(matrix_path), _digest(receipt_path)
    receipt = json.loads(receipt_path.read_text())
    if before[0] != receipt.get('output_sha256'):
        raise ValueError('MATRIX_HASH_MISMATCH')
    if receipt.get('no_hsp_regions') != []:
        raise ValueError('NO_HSP_REQUIRES_REVIEW')
    with matrix_path.open(newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, [])
        if len(header) < 3 or header[0] != 'locus_identity':
            raise ValueError('INVALID_HEADER')
        ids = header[1:]
        if len(set(ids)) != len(ids):
            raise ValueError('DUPLICATE_IDENTITY')
        for identity in ids:
            parts = identity.split(' / ')
            if len(parts) != 4 or any(not p or p != p.strip() for p in parts):
                raise ValueError('INCOMPLETE_LOCUS_IDENTITY')
        n = len(ids)
        if receipt.get('records') != n or receipt.get('unordered_pairs') != n * (n - 1) // 2:
            raise ValueError('RECEIPT_SIZE_MISMATCH')
        if not isinstance(max_bytes, int) or max_bytes <= 0 or n * n * 8 > max_bytes:
            raise ValueError('MATRIX_MEMORY_LIMIT')
        values = array('d')
        for index, row in enumerate(reader):
            if index >= n or len(row) != n + 1 or row[0] != ids[index]:
                raise ValueError('ROW_IDENTITY_OR_WIDTH_MISMATCH')
            for text in row[1:]:
                try:
                    value = float(text)
                except ValueError as exc:
                    raise ValueError('INVALID_DISTANCE') from exc
                if not math.isfinite(value) or not 0 <= value <= 1:
                    raise ValueError('INVALID_DISTANCE')
                values.append(value)
        if len(values) != n * n:
            raise ValueError('MATRIX_ROW_COUNT_MISMATCH')
    for i in range(n):
        if values[i*n+i] != 0:
            raise ValueError('NONZERO_DIAGONAL')
        for j in range(i):
            if values[i*n+j] != values[j*n+i]:
                raise ValueError('ASYMMETRIC_DISTANCE')
    if (_digest(matrix_path), _digest(receipt_path)) != before:
        raise ValueError('INPUT_CHANGED_DURING_READ')
    return {'records': n, 'unordered_pairs': n*(n-1)//2,
            'matrix_sha256': before[0], 'receipt_sha256': before[1],
            'status': 'STRUCTURAL_CHECK_ONLY',
            'limits': 'Receipt authenticity, scientific suitability and embedding are not established.'}
