import datetime
import logging
import os
import typing

import pytest
import requests_mock
import resolvelib
from packaging.requirements import Requirement
from packaging.version import Version

from fromager import candidate, context, resolver
from fromager.requirements_file import RequirementType

_BOOTSTRAP_TIME = datetime.datetime(2026, 3, 26, 0, 0, 0, tzinfo=datetime.UTC)
_COOLDOWN_7_DAYS = datetime.timedelta(days=7)
# cutoff = 2026-03-19T00:00:00Z

_PYPI_SIMPLE_JSON_CONTENT_TYPE = "application/vnd.pypi.simple.v1+json"

# Three versions at known ages:
#   2.0.0  uploaded 2026-03-24 ->  2 days old (within cooldown)
#   1.3.2  uploaded 2026-03-15 -> 11 days old (outside cooldown)
#   1.2.2  uploaded 2026-01-01 -> 84 days old (outside cooldown)
_cooldown_json_response = {
    "meta": {"api-version": "1.1"},
    "name": "test-pkg",
    "files": [
        {
            "filename": "test_pkg-2.0.0-py3-none-any.whl",
            "url": "https://files.pythonhosted.org/packages/test_pkg-2.0.0-py3-none-any.whl",
            "hashes": {"sha256": "aaa"},
            "upload-time": "2026-03-24T00:00:00+00:00",
        },
        {
            "filename": "test_pkg-1.3.2-py3-none-any.whl",
            "url": "https://files.pythonhosted.org/packages/test_pkg-1.3.2-py3-none-any.whl",
            "hashes": {"sha256": "bbb"},
            "upload-time": "2026-03-15T00:00:00+00:00",
        },
        {
            "filename": "test_pkg-1.2.2-py3-none-any.whl",
            "url": "https://files.pythonhosted.org/packages/test_pkg-1.2.2-py3-none-any.whl",
            "hashes": {"sha256": "ccc"},
            "upload-time": "2026-01-01T00:00:00+00:00",
        },
    ],
}

_COOLDOWN = candidate.Cooldown(
    min_age=_COOLDOWN_7_DAYS,
    bootstrap_time=_BOOTSTRAP_TIME,
)

@pytest.fixture(autouse=True)
def clear_resolver_cache() -> typing.Generator[None, None, None]:
    """Clear the class-level resolver cache before each test.

    BaseProvider.resolver_cache is a ClassVar that persists across test
    instances. Without clearing it, candidates fetched in one test are reused
    by subsequent tests, bypassing mocked HTTP responses and producing
    incorrect results.
    """
    resolver.BaseProvider.clear_cache()
    resolver.BaseProvider._cooldown_unsupported_warned.clear()
    yield

@pytest.fixture(autouse=True)
def set_debug_resolver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(resolver, "DEBUG_RESOLVER", "1")

def test_toplevel_exact_pin_exempts_from_cooldown(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A top-level requirement with an exact version pin should bypass cooldown."""
    with requests_mock.Mocker() as r:
        r.get(
            "https://pypi.org/simple/test-pkg/",
            json=_cooldown_json_response,
            headers={"Content-Type": _PYPI_SIMPLE_JSON_CONTENT_TYPE},
        )
        provider = resolver.PyPIProvider(
            include_sdists=True,
            cooldown=_COOLDOWN,
            req_type=RequirementType.TOP_LEVEL,
        )
        rslvr = resolvelib.Resolver(provider, resolvelib.BaseReporter())
        with caplog.at_level(logging.DEBUG, logger="fromager.resolver"):
            # Requesting the exact version which is *within* the cooldown period
            result = rslvr.resolve([Requirement("test-pkg==2.0.0")])

        resolved_candidate = result.mapping["test-pkg"]
        # On unfixed code, this will be 1.3.2. On fixed code, it should be 2.0.0.
        assert str(resolved_candidate.version) == "2.0.0"
        # The skipped message for 2.0.0 should NOT appear if the exemption works.
        assert "skipping 2.0.0" not in caplog.text
        assert "cooldown" not in caplog.text

def test_toplevel_range_pin_still_subject_to_cooldown(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A top-level requirement with a version range should still be subject to cooldown."""
    with requests_mock.Mocker() as r:
        r.get(
            "https://pypi.org/simple/test-pkg/",
            json=_cooldown_json_response,
            headers={"Content-Type": _PYPI_SIMPLE_JSON_CONTENT_TYPE},
        )
        provider = resolver.PyPIProvider(
            include_sdists=True,
            cooldown=_COOLDOWN,
            req_type=RequirementType.TOP_LEVEL,
        )
        rslvr = resolvelib.Resolver(provider, resolvelib.BaseReporter())
        with caplog.at_level(logging.DEBUG, logger="fromager.resolver"):
            # Requesting a version range that includes 2.0.0 (within cooldown)
            result = rslvr.resolve([Requirement("test-pkg>=1.0.0,<3.0.0")])

        resolved_candidate = result.mapping["test-pkg"]
        # 2.0.0 is within cooldown, so 1.3.2 should be selected.
        assert str(resolved_candidate.version) == "1.3.2"
        # 2.0.0 should be logged as skipped due to cooldown.
        assert "skipping 2.0.0" in caplog.text
        assert "cooldown" in caplog.text

def test_transitive_exact_pin_still_subject_to_cooldown(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A transitive requirement with an exact version pin should still be subject to cooldown."""
    # Simulate a transitive dependency by *not* setting req_type=TOP_LEVEL
    # to the PyPIProvider that resolves test-pkg.
    with requests_mock.Mocker() as r:
        r.get(
            "https://pypi.org/simple/test-pkg/",
            json=_cooldown_json_response,
            headers={"Content-Type": _PYPI_SIMPLE_JSON_CONTENT_TYPE},
        )
        # req_type is NOT TOP_LEVEL, so it's treated as a transitive dependency.
        provider = resolver.PyPIProvider(
            include_sdists=True,
            cooldown=_COOLDOWN,
            req_type=RequirementType.INSTALL, # Or any other non-TOP_LEVEL type
        )
        rslvr = resolvelib.Resolver(provider, resolvelib.BaseReporter())
        with caplog.at_level(logging.DEBUG, logger="fromager.resolver"):
            with pytest.raises(resolvelib.resolvers.exceptions.ResolverException) as excinfo:
                # Requesting the exact version which is *within* the cooldown period
                rslvr.resolve([Requirement("test-pkg==2.0.0")])

                # Check the error message contains the cooldown reason
                assert "release-age cooldown" in str(excinfo.value)
                assert "skipping 2.0.0" in caplog.text
                assert "cooldown" in caplog.text
