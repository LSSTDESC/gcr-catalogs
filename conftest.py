"""
conftest.py
"""

def pytest_addoption(parser):
    parser.addoption(
        "--no-catalog", action="store_true", default=False, help="skip tests that need catalogs"
    )

_SKIP_IF_NO_CATALOG = {
    'test_protoDC2.py',
    'test_catalogs.py',
}

def pytest_ignore_collect(path, config):
    if config.getoption('--no-catalog') and path.basename in _SKIP_IF_NO_CATALOG:
        return True
