"""BLACK_CHERRY_4_423: --bioassay-table wires strain-level MEASURED bioassay onto EPA-ng placement
query tips only. Real CLI subprocess calls, mirroring tests/test_ggtree_inputs_positive_path.py."""
from pathlib import Path
import csv
import os
import subprocess
import sys

TOOL = Path(__file__).resolve().parents[1] / 'tools/build_placement_ggtree_inputs.py'


def _run(tmp_path, *extra_args):
    result = subprocess.run(
        [sys.executable, str(TOOL), *extra_args],
        cwd=tmp_path, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
        capture_output=True, text=True, timeout=30,
    )
    return result


def _rows(prefix):
    with open(str(prefix) + '_ggtree_annotation.tsv', newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh, delimiter='\t'))


def test_matched_query_reads_measured_with_verbatim_values(tmp_path):
    tree = tmp_path / 'input.nwk'
    tree.write_text('((AS-100:0.1,RefB:0.2):0.3,outgroup_X:0.4);\n')
    bio = tmp_path / 'af_dossier_activity_table.csv'
    bio.write_text('strain,anti_Candida,anti_MRSA,host,genus\nAS-100,positive,negative,Bombus sp.,Streptomyces sp.\n')
    prefix = tmp_path / 'result'
    r = _run(tmp_path, '--graft', str(tree), '--bioassay-table', str(bio),
             '--out-prefix', str(prefix), '--keep-all-refs')
    assert r.returncode == 0, r.stderr
    rows = {row['tip']: row for row in _rows(prefix)}
    q = rows['AS-100']
    assert q['bioassay_status'] == 'MEASURED'
    assert q['anti_candida'] == 'positive'
    assert q['anti_mrsa'] == 'negative'


def test_comma_delimited_source_autodetected(tmp_path):
    """The shipped af_dossier_activity_table.csv is comma-delimited; every other metadata table
    this tool reads is TSV. The loader must not require the caller to convert it."""
    tree = tmp_path / 'input.nwk'
    tree.write_text('(AS-100:0.1,outgroup_X:0.4);\n')
    bio = tmp_path / 'bio.csv'
    bio.write_text('strain,anti_Candida,anti_MRSA\nAS-100,positive,positive\n')
    prefix = tmp_path / 'result'
    r = _run(tmp_path, '--graft', str(tree), '--bioassay-table', str(bio),
             '--out-prefix', str(prefix), '--keep-all-refs')
    assert r.returncode == 0, r.stderr
    rows = {row['tip']: row for row in _rows(prefix)}
    assert rows['AS-100']['bioassay_status'] == 'MEASURED'


def test_unmatched_query_reads_not_recorded_and_warns(tmp_path):
    tree = tmp_path / 'input.nwk'
    tree.write_text('(AS-999:0.1,outgroup_X:0.4);\n')
    bio = tmp_path / 'bio.tsv'
    bio.write_text('strain\tanti_Candida\tanti_MRSA\nAS-100\tpositive\tnegative\n')
    prefix = tmp_path / 'result'
    r = _run(tmp_path, '--graft', str(tree), '--bioassay-table', str(bio),
             '--out-prefix', str(prefix), '--keep-all-refs')
    assert r.returncode == 0, r.stderr
    rows = {row['tip']: row for row in _rows(prefix)}
    q = rows['AS-999']
    assert q['bioassay_status'] == 'NOT_RECORDED'
    assert q['anti_candida'] == '' and q['anti_mrsa'] == ''
    assert 'no query strain in this tree matched' in r.stderr


def test_omitted_table_reads_not_requested_back_compat(tmp_path):
    """A caller that never heard of --bioassay-table (every existing script, every landed patch
    card) must see byte-identical behaviour on the columns it already reads."""
    tree = tmp_path / 'input.nwk'
    tree.write_text('(AS-100:0.1,outgroup_X:0.4);\n')
    prefix = tmp_path / 'result'
    r = _run(tmp_path, '--graft', str(tree), '--out-prefix', str(prefix), '--keep-all-refs')
    assert r.returncode == 0, r.stderr
    rows = {row['tip']: row for row in _rows(prefix)}
    q = rows['AS-100']
    assert q['bioassay_status'] == 'NOT_REQUESTED'
    assert q['anti_candida'] == '' and q['anti_mrsa'] == ''


def test_reference_tips_never_carry_bioassay_columns(tmp_path):
    """Claim-safety: bioassay is this project's own strain-level MEASURED data. A public
    reference/type-strain tip is a comparator, not an isolate that was ever assayed -- it must
    read blank/NOT_APPLICABLE regardless of whether a table happens to key-match its label."""
    tree = tmp_path / 'input.nwk'
    tree.write_text('((AS-100:0.1,RefB:0.2):0.3,outgroup_X:0.4);\n')
    bio = tmp_path / 'bio.tsv'
    # deliberately key RefB too, to prove the row-writer -- not merely an empty table -- is what
    # keeps reference tips clean
    bio.write_text('strain\tanti_Candida\tanti_MRSA\nAS-100\tpositive\tnegative\nRefB\tpositive\tpositive\n')
    prefix = tmp_path / 'result'
    r = _run(tmp_path, '--graft', str(tree), '--bioassay-table', str(bio),
             '--out-prefix', str(prefix), '--keep-all-refs')
    assert r.returncode == 0, r.stderr
    rows = {row['tip']: row for row in _rows(prefix)}
    ref = rows['RefB']
    assert ref['bioassay_status'] == '' and ref['anti_candida'] == '' and ref['anti_mrsa'] == ''
    og = rows['outgroup_X']
    assert og['bioassay_status'] == '' and og['anti_candida'] == '' and og['anti_mrsa'] == ''


def test_malformed_table_refuses_typed_not_a_traceback(tmp_path):
    tree = tmp_path / 'input.nwk'
    tree.write_text('(AS-100:0.1,outgroup_X:0.4);\n')
    bio = tmp_path / 'bad.tsv'
    bio.write_text('strain\tsomething_else\nAS-100\tx\n')  # missing anti_Candida/anti_MRSA
    prefix = tmp_path / 'result'
    r = _run(tmp_path, '--graft', str(tree), '--bioassay-table', str(bio),
             '--out-prefix', str(prefix), '--keep-all-refs')
    assert r.returncode == 2, r.stderr
    assert 'BIOASSAY_METADATA_SCHEMA' in r.stderr
    assert 'Traceback' not in r.stderr
