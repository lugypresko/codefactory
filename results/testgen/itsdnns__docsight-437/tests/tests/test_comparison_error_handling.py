'''Acceptance tests for hiding unsupported DOCSIS errors in Before/After Comparison.'''

import pytest
from unittest.mock import patch, MagicMock
from app.web import app

@pytest.fixture
def app_client():
    '''Create a test client with comparison module blueprint.'''
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

# SNAPSHOT data simulating unsupported DOCSIS error counters (missing key)
SNAPSHOT_UNSUPPORTED_ERRORS = {
    "timestamp": "2026-03-01T06:00:00Z",
    "summary": {
        "ds_power_avg": 3.1,
        "ds_snr_avg": 34.2,
        "us_power_avg": 42.1,
        "health": "good",
    },
    "ds_channels": [],
    "us_channels": [],
}

# SNAPSHOT data simulating zero DOCSIS error counters (key present with 0 value)
SNAPSHOT_ZERO_ERRORS = {
    "timestamp": "2026-03-08T06:00:00Z",
    "summary": {
        "ds_power_avg": 4.2,
        "ds_snr_avg": 31.5,
        "us_power_avg": 42.4,
        "ds_correctable_errors": 0,
        "ds_uncorrectable_errors": 0,
        "health": "marginal",
    },
    "ds_channels": [],
    "us_channels": [],
}

# SNAPSHOT data simulating supported DOCSIS error counters
SNAPSHOT_WITH_ERRORS = {
    "timestamp": "2026-03-15T06:00:00Z",
    "summary": {
        "ds_power_avg": 3.5,
        "ds_snr_avg": 36.0,
        "us_power_avg": 41.5,
        "ds_correctable_errors": 50,
        "ds_uncorrectable_errors": 10,
        "health": "good",
    },
    "ds_channels": [],
    "us_channels": [],
}

class TestComparisonErrorHandling:
    def test_unsupported_errors_not_shown_as_zero_in_api_response(self, app_client):
        '''
        Tests that when DOCSIS error counters are unsupported for both periods,
        the API response reflects this (e.g., None or absence, not 0).
        This test expects a failure in the unfixed code because it likely
        defaults missing values to 0 or processes them incorrectly.
        '''
        with patch("app.modules.comparison.routes._get_storage") as mock_storage:
            storage = MagicMock()
            storage.get_range_data.side_effect = [
                [SNAPSHOT_UNSUPPORTED_ERRORS],
                [SNAPSHOT_UNSUPPORTED_ERRORS],
            ]
            mock_storage.return_value = storage
            resp = app_client.get(
                "/api/comparison"
                "?from_a=2026-03-01T00:00:00Z&to_a=2026-03-01T23:59:00Z"
                "&from_b=2026-03-08T00:00:00Z&to_b=2026-03-08T23:59:00Z"
            )
        assert resp.status_code == 200
        data = resp.get_json()

        # The issue implies that unsupported counters should not be displayed or summarized as 0.
        # This test checks the API response for period_a and period_b, as well as delta.
        # Currently, the unfixed code likely treats missing as 0.
        # We expect ds_uncorrectable_errors to be None or absent for unsupported cases.
        # The exact field name for 'unsupported' might vary in a fix,
        # but for now, we'll check for absence or None.
        assert "ds_uncorrectable_errors" not in data["period_a"]["avg"] or data["period_a"]["avg"]["ds_uncorrectable_errors"] is None
        assert "ds_uncorrectable_errors" not in data["period_b"]["avg"] or data["period_b"]["avg"]["ds_uncorrectable_errors"] is None
        assert "uncorr_errors" not in data["delta"] or data["delta"]["uncorr_errors"] is None # delta should also reflect unsupported
        assert data["delta"]["verdict"] == "unchanged" # Other health metrics still allow verdict

    def test_zero_errors_displayed_correctly(self, app_client):
        '''
        Tests that explicitly zero error counters are displayed as 0,
        not conflated with unsupported.
        '''
        with patch("app.modules.comparison.routes._get_storage") as mock_storage:
            storage = MagicMock()
            storage.get_range_data.side_effect = [
                [SNAPSHOT_ZERO_ERRORS],
                [SNAPSHOT_ZERO_ERRORS],
            ]
            mock_storage.return_value = storage
            resp = app_client.get(
                "/api/comparison"
                "?from_a=2026-03-01T00:00:00Z&to_a=2026-03-01T23:59:00Z"
                "&from_b=2026-03-08T00:00:00Z&to_b=2026-03-08T23:59:00Z"
            )
        assert resp.status_code == 200
        data = resp.get_json()

        assert data["period_a"]["avg"]["ds_uncorrectable_errors"] == 0
        assert data["period_b"]["avg"]["ds_uncorrectable_errors"] == 0
        assert data["delta"]["uncorr_errors"] == 0
        assert data["delta"]["verdict"] == "unchanged"

    def test_supported_errors_displayed_normally(self, app_client):
        '''
        Tests that when DOCSIS error counters are supported, they are displayed
        normally and contribute to the delta.
        '''
        with patch("app.modules.comparison.routes._get_storage") as mock_storage:
            storage = MagicMock()
            storage.get_range_data.side_effect = [
                [SNAPSHOT_ZERO_ERRORS], # Start with 0 errors
                [SNAPSHOT_WITH_ERRORS],  # Then have some errors
            ]
            mock_storage.return_value = storage
            resp = app_client.get(
                "/api/comparison"
                "?from_a=2026-03-01T00:00:00Z&to_a=2026-03-01T23:59:00Z"
                "&from_b=2026-03-08T00:00:00Z&to_b=2026-03-08T23:59:00Z"
            )
        assert resp.status_code == 200
        data = resp.get_json()

        assert data["period_a"]["avg"]["ds_uncorrectable_errors"] == 0
        assert data["period_b"]["avg"]["ds_uncorrectable_errors"] == 10
        assert data["delta"]["uncorr_errors"] == 10 # Delta should be 10 - 0 = 10
        assert data["delta"]["verdict"] == "degraded" # More errors = degraded

    def test_mixed_error_support_one_unsupported(self, app_client):
        '''
        Tests mixed support: one period unsupported, one with errors.
        The delta for errors should reflect this (e.g., None or absence).
        '''
        with patch("app.modules.comparison.routes._get_storage") as mock_storage:
            storage = MagicMock()
            storage.get_range_data.side_effect = [
                [SNAPSHOT_UNSUPPORTED_ERRORS],
                [SNAPSHOT_WITH_ERRORS],
            ]
            mock_storage.return_value = storage
            resp = app_client.get(
                "/api/comparison"
                "?from_a=2026-03-01T00:00:00Z&to_a=2026-03-01T23:59:00Z"
                "&from_b=2026-03-08T00:00:00Z&to_b=2026-03-08T23:59:00Z"
            )
        assert resp.status_code == 200
        data = resp.get_json()

        assert "ds_uncorrectable_errors" not in data["period_a"]["avg"] or data["period_a"]["avg"]["ds_uncorrectable_errors"] is None
        assert data["period_b"]["avg"]["ds_uncorrectable_errors"] == 10
        assert "uncorr_errors" not in data["delta"] or data["delta"]["uncorr_errors"] is None
        # Other metrics still affect verdict, e.g. ds_snr and ds_power
        # Given SNAPSHOT_UNSUPPORTED_ERRORS has ds_power_avg=3.1, ds_snr_avg=34.2
        # and SNAPSHOT_WITH_ERRORS has ds_power_avg=3.5, ds_snr_avg=36.0
        # This implies: ds_power delta 0.4 (increased), ds_snr delta 1.8 (increased)
        # So overall improved
        assert data["delta"]["verdict"] == "improved" # Power/SNR improve verdict
