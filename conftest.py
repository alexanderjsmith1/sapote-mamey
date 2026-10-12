"""Shared partition options for tests, tools and deliverable_tools.

Root placement ensures pytest registers options before parsing selectors in any
configured test root. Only explicit slow/network marks control default skips.
"""

import pytest


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

    for item in items:
        # No filename, import or parametrisation-value hints: explicit marks only.
        is_slow = "slow" in item.keywords
        if is_slow:
            item.add_marker(pytest.mark.slow)
            if not run_slow:
                item.add_marker(skip_slow)
        if "network" in item.keywords and not run_network:
            item.add_marker(skip_network)
