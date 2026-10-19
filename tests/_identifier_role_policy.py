"""Compatibility import: production and source tests share one validator and table."""
import sys
from pathlib import Path
_TOOLS = Path(__file__).resolve().parents[1] / 'tools'
if str(_TOOLS) not in sys.path:
    sys.path.insert(0,str(_TOOLS))
from identifier_source_roles import (ID, PLACEHOLDERS, normalise, reviewed_public_sites,
                                     audit_test_identifiers, digest, read_regular)
