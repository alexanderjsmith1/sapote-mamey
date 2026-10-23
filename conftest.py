"""Shared partition options for tests, tools and deliverable_tools.

Root placement ensures pytest registers options before parsing selectors in any
configured test root. Only explicit slow/network/needs_arial marks control default skips.
"""

import pytest


def _real_arial_present():
    """True when matplotlib can find a font family named Arial. A metric-compatible stand-in (Liberation Sans on a Linux runner)
    is not found by name, which is the point: see the needs_arial marker in pyproject.toml."""
    try:
        from matplotlib import font_manager
        font_manager.findfont("Arial", fallback_to_default=False)
        return True
    except Exception:
        return False


def pytest_addoption(parser):
    parser.addoption("--run-slow", action="store_true", default=False,
                     help="include slow tests (figure/plot rendering, cohort builds)")
    parser.addoption("--run-network", action="store_true", default=False,
                     help="include tests marked @pytest.mark.network (need live network)")


def pytest_collection_modifyitems(config, items):
    run_slow = config.getoption("--run-slow")
    run_network = config.getoption("--run-network")
    skip_slow = pytest.mark.skip(reason="slow test; run with --run-slow")
    skip_network = pytest.mark.skip(reason="network test; run with --run-network")
    skip_arial = pytest.mark.skip(reason="needs real Arial: the layout and fit checks pass with Arial and are refused on a runner whose only metric-compatible font is Liberation Sans (GitHub CI .456); run them on a machine with Arial")
    arial_present = None

    for item in items:
        # No filename, import or parametrisation-value hints: explicit marks only.
        is_slow = "slow" in item.keywords
        if is_slow:
            item.add_marker(pytest.mark.slow)
            if not run_slow:
                item.add_marker(skip_slow)
        if "network" in item.keywords and not run_network:
            item.add_marker(skip_network)
        if "needs_arial" in item.keywords:
            if arial_present is None:
                arial_present = _real_arial_present()
            if not arial_present:
                item.add_marker(skip_arial)
