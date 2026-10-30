"""Public examples must use the real CLI argument contract; no tools are run."""
import re
import shlex
from pathlib import Path
import pytest
from mamey.cli import build_parser

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('document',['docs/COMPANION_CLASS_EVIDENCE.md'])
def test_new_reader_commands_have_parseable_package_arguments(document):
    source=(ROOT/document).read_text()
    parser=build_parser()
    seen=set()
    for block in re.findall(r'```bash\n(.*?)\n```', source, re.S):
        tokens=shlex.split(block.replace('\\\n', ' '))
        if tokens[:2] != ['python', 'mamey_run.py']:
            continue
        parsed=parser.parse_args(tokens[2:])
        assert parsed.package=='runs/EXAMPLE/package' and callable(parsed.func)
        seen.add(tokens[2])
    assert {'gecco-crosscheck','export-metabolomics','two-proof-rescue'} <= seen


def test_landing_page_routes_to_the_command_guide():
    assert '](docs/COMPANION_CLASS_EVIDENCE.md)' in (ROOT / 'README.md').read_text()


def test_completed_workflow_guides_are_indexed_inside_source():
    index=(ROOT/'CURRENT_DOCS_INDEX.md').read_text()
    for path in ('docs/POSTSEAL_READERS.md','docs/COHORT_BANK_TRANSACTIONS.md','docs/447_COMPANION_RETRIEVAL_CONTROLS.md','docs/COMPANION_CLASS_EVIDENCE.md'):
        assert ']('+path+')' in index and (ROOT/path).is_file()
