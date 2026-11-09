#!/usr/bin/env python3
"""Persist verified fallback SVG conversion bindings beside a completed PDF.

This records hashes, not renderer approval or scientific validity. Temporary
converted PDFs are intentionally described as not retained after fallback cleanup.
"""
import hashlib
import json
from pathlib import Path
import sys

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def persist(workdir, output_pdf, output_receipt):
    work=Path(workdir).resolve();pdf=Path(output_pdf).resolve();out=Path(output_receipt).resolve()
    if not work.is_dir() or not pdf.is_file():raise ValueError('PDF_BINDING_INPUT_MISSING')
    records=[]
    for sidecar in sorted(work.glob('*.pdf.conversion.json')):
        record=json.loads(sidecar.read_text(encoding='utf-8'))
        if record.get('schema')!='sapote_svg_pdf_conversion_v1':raise ValueError('PDF_BINDING_SCHEMA_INVALID')
        source=Path(record['source_svg']).resolve();converted=Path(record['converted_pdf']).resolve()
        if not converted.is_relative_to(work) or not source.is_file() or not converted.is_file():raise ValueError('PDF_BINDING_PATH_INVALID')
        if digest(source)!=record['source_svg_sha256'] or digest(converted)!=record['converted_pdf_sha256']:raise ValueError('PDF_BINDING_HASH_MISMATCH')
        if not record.get('converter'):raise ValueError('PDF_BINDING_CONVERTER_MISSING')
        records.append({'source_svg':str(source),'source_svg_sha256':record['source_svg_sha256'],
                        'intermediate_pdf_sha256':record['converted_pdf_sha256'],
                        'converter':record['converter'],'intermediate_retained':False})
    result={'schema':'sapote-pdf-resource-bindings-v1','output_pdf':str(pdf),'output_pdf_sha256':digest(pdf),
            'conversion_count':len(records),'conversions':records,
            'scope':'Fallback conversion bindings only; not proof of final figure rendering, provenance approval, or scientific validity.'}
    with out.open('x',encoding='utf-8') as handle:json.dump(result,handle,indent=2);handle.write('\n')
    return result

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('usage: persist_pdf_conversion_bindings.py WORKDIR OUTPUT_PDF OUTPUT_RECEIPT')
    persist(*sys.argv[1:])
