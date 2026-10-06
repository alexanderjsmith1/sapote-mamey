"""Public examples must use the real CLI argument contract; no tools are run."""
import re
from pathlib import Path
import pytest
from mamey.cli import build_parser

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('document',['README.md','docs/COMPANION_CLASS_EVIDENCE.md'])
def test_new_reader_commands_have_parseable_package_arguments(document):
    source=(ROOT/document).read_text()
    parser=build_parser()
    for command in ('gecco-crosscheck','export-metabolomics','two-proof-rescue'):
        assert re.search(r'\b'+command+r' --package <package>',source)
        args=[command,'--package','synthetic-package']
        if command=='gecco-crosscheck':args.extend(['--zip','synthetic.zip'])
        elif command=='export-metabolomics':args.extend(['--source-zip','synthetic.zip'])
        else:args.extend(['--policy','nonks_position_v1','--scorecard','synthetic.tsv'])
        parsed=parser.parse_args(args)
        assert parsed.package=='synthetic-package' and callable(parsed.func)


def test_completed_workflow_guides_are_indexed_inside_source():
    index=(ROOT/'CURRENT_DOCS_INDEX.md').read_text()
    for path in ('docs/POSTSEAL_READERS.md','docs/COHORT_BANK_TRANSACTIONS.md','docs/447_COMPANION_RETRIEVAL_CONTROLS.md','docs/COMPANION_CLASS_EVIDENCE.md'):
        assert ']('+path+')' in index and (ROOT/path).is_file()
