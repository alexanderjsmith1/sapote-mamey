"""DEPRECATED shim — the two-strain comparison module was renamed to `mamey.compare` (v9.7.191).

This module re-exports everything from `mamey.compare` so existing imports
(`from mamey import gemini`, `from .gemini import gemini_compare_command`) keep working.
New code should import from `mamey.compare`. Remove this shim once no importer references
`mamey.gemini` (grep the tree before deleting).
"""
from mamey.compare import *  # noqa: F401,F403
from mamey.compare import compare_command, gemini_compare_command  # noqa: F401
