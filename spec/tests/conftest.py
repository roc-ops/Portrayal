"""Shared fixtures over the once-parsed library. See libdata.py for why."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import libdata  # noqa: E402


@pytest.fixture(scope="session")
def library():
    return libdata.library()


@pytest.fixture(scope="session")
def devices():
    return {slug: doc for slug, doc in libdata.devices()}


@pytest.fixture(scope="session")
def components():
    return libdata.components()
