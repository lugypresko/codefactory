import pytest
from api.config import resolve_model_provider, _custom_slug_rest_looks_like_host_port
from unittest.mock import MagicMock


def test_custom_provider_name_with_parentheses_and_port(monkeypatch):
    mock_cfg = {
        "custom_providers": [
            {
                "name": "Local (127.0.0.1:15721)",
                "base_url": "http://127.0.0.1:15721/v1",
                "model": "deepseek-v4-flash"
            }
        ]
    }
    
    # Monkeypatch the global 'cfg' object used by resolve_model_provider
    monkeypatch.setattr("api.config.cfg", mock_cfg)

    model_id = "@custom:local-(127.0.0.1:15721):deepseek-v4-flash"

    resolved_model, resolved_provider, resolved_base_url = resolve_model_provider(model_id)

    assert resolved_model == "deepseek-v4-flash", (
        f"Expected model 'deepseek-v4-flash', but got '{resolved_model}'. "
        "This indicates the custom provider name parsing is still corrupted."
    )
    assert resolved_provider == "custom:local-(127.0.0.1:15721)", (
        f"Expected provider 'custom:local-(127.0.0.1:15721)', but got '{resolved_provider}'. "
        "This indicates the custom provider name parsing is still corrupted."
    )

def test_custom_provider_name_with_parentheses_and_port_no_model_suffix(monkeypatch):
    mock_cfg = {
        "custom_providers": [
            {
                "name": "Local (127.0.0.1:15721)",
                "base_url": "http://127.0.0.1:15721/v1",
                "model": "deepseek-v4-flash"
            }
        ]
    }
    monkeypatch.setattr("api.config.cfg", mock_cfg)

    # Test case where model_id does not include a model suffix, just the provider.
    # This might not directly hit the reported bug, but ensures the provider parsing is robust.
    model_id = "@custom:local-(127.0.0.1:15721)"

    resolved_model, resolved_provider, resolved_base_url = resolve_model_provider(model_id)

    assert resolved_model is None, (
        f"Expected resolved_model to be None, but got '{resolved_model}'. "
        "Incorrectly extracted model from provider-only slug."
    )
    assert resolved_provider == "custom:local-(127.0.0.1:15721)", (
        f"Expected provider 'custom:local-(127.0.0.1:15721)', but got '{resolved_provider}'. "
        "This indicates the custom provider name parsing is still corrupted."
    )

def test_custom_provider_name_with_brackets_and_port(monkeypatch):
    mock_cfg = {
        "custom_providers": [
            {
                "name": "Local [127.0.0.1:15721]",
                "base_url": "http://127.0.0.1:15721/v1",
                "model": "deepseek-v4-flash"
            }
        ]
    }
    monkeypatch.setattr("api.config.cfg", mock_cfg)

    # Test with square brackets instead of parentheses, as an edge case
    model_id = "@custom:local-[127.0.0.1:15721]:deepseek-v4-flash"

    resolved_model, resolved_provider, resolved_base_url = resolve_model_provider(model_id)

    assert resolved_model == "deepseek-v4-flash", (
        f"Expected model 'deepseek-v4-flash', but got '{resolved_model}'. "
        "This indicates the custom provider name parsing is still corrupted with brackets."
    )
    assert resolved_provider == "custom:local-[127.0.0.1:15721]", (
        f"Expected provider 'custom:local-[127.0.0.1:15721]', but got '{resolved_provider}'. "
        "This indicates the custom provider name parsing is still corrupted with brackets."
    )

def test_custom_provider_name_with_multiple_colons_not_host_port(monkeypatch):
    mock_cfg = {
        "custom_providers": [
            {
                "name": "Local (scope:id:version)",
                "base_url": "http://test.com/v1",
                "model": "deepseek-v4-flash"
            }
        ]
    }
    monkeypatch.setattr("api.config.cfg", mock_cfg)

    # Test with multiple colons that are NOT part of a host:port, but still within parentheses
    # E.g., a "scope:id:version" pattern inside a custom name.
    model_id = "@custom:local-(scope:id:version):deepseek-v4-flash"

    resolved_model, resolved_provider, resolved_base_url = resolve_model_provider(model_id)

    assert resolved_model == "deepseek-v4-flash", (
        f"Expected model 'deepseek-v4-flash', but got '{resolved_model}'. "
        "This indicates the custom provider name parsing is still corrupted with multiple colons."
    )
    assert resolved_provider == "custom:local-(scope:id:version)", (
        f"Expected provider 'custom:local-(scope:id:version)', but got '{resolved_provider}'. "
        "This indicates the custom provider name parsing is still corrupted with multiple colons."
    )

