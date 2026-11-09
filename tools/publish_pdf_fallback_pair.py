#!/usr/bin/env python3
"""Publish a fresh fallback PDF and its checked resource binding as a pair.

Uses the bundle's fresh_output_set. Catchable publication failures roll back
owned outputs, but flat-file publication is not crash-atomic.
"""
import json
from pathlib import Path
import shutil
import sys
# md_to_pdf.sh runs this from the caller's folder; the bundle root must be importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.output_transaction import fresh_output_set
from persist_pdf_conversion_bindings import digest, persist

def publish(workdir, draft_pdf, output_pdf, output_receipt):
    work=Path(workdir).resolve();draft=Path(draft_pdf).resolve()
    output=Path(output_pdf).absolute();receipt=Path(output_receipt).absolute()
    if output.parent!=receipt.parent:raise ValueError('PDF_PAIR_DIFFERENT_DIRECTORIES')
    if not work.is_dir() or not draft.is_file() or not draft.is_relative_to(work):raise ValueError('PDF_PAIR_DRAFT_INVALID')
    with fresh_output_set(output.parent,[output.name,receipt.name]) as stage:
        staged_pdf=stage/output.name;staged_receipt=stage/receipt.name
        shutil.copyfile(draft,staged_pdf)
        if digest(draft)!=digest(staged_pdf):raise ValueError('PDF_PAIR_COPY_MISMATCH')
        result=persist(work,staged_pdf,staged_receipt)
        result['output_pdf']=str(output)
        staged_receipt.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        if digest(draft)!=result['output_pdf_sha256']:raise ValueError('PDF_PAIR_DRAFT_CHANGED')
    return result

if __name__=='__main__':
    if len(sys.argv)!=5:raise SystemExit('usage: publish_pdf_fallback_pair.py WORKDIR DRAFT_PDF OUTPUT_PDF OUTPUT_RECEIPT')
    publish(*sys.argv[1:])
