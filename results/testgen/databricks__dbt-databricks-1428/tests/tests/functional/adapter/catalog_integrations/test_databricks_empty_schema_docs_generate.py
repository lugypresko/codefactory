import pytest
from unittest.mock import patch, MagicMock
from dbt.tests.adapter.basic.test_base import BaseSimpleMaterializations
from dbt.tests.util import run_dbt
import agate
from dbt.common.clients.agate_helper import Number, Text

# Agate Table for populated schema, ensuring 'column_name' is Text
POPULATED_SCHEMA_DATA = [
    {"column_name": "id", "data_type": "int", "comment": None},
    {"column_name": "name", "data_type": "string", "comment": None},
]
POPULATED_AGATE_TABLE = agate.Table.from_object(POPULATED_SCHEMA_DATA, column_types={"column_name": Text()})

class MockAgateTableForEmptySchema(agate.Table):
    def __init__(self, rows=None, column_names=None, column_types=None):
        if column_names is None:
            column_names = ["column_name", "data_type", "comment"]
        # This is the crucial part: 'column_name' is incorrectly inferred as Number
        if column_types is None:
            column_types = {"column_name": Number(), "data_type": Text(), "comment": Text()}
        super().__init__(rows if rows is not None else [], column_names, column_types)

class TestDatabricksEmptySchemaDocsGenerate(BaseSimpleMaterializations):
    @pytest.fixture(scope="class")
    def models(self):
        # A single model to ensure the 'populated_schema' is processed
        return {
            "model_a.sql": "select 1 as id",
        }

    @pytest.fixture(scope="class")
    def profiles_config_update(self):
        # This fixture will update the 'dbt_profile_data' from conftest.py
        # We add an 'empty_schema_target' to the outputs to ensure it's processed by docs generate
        return {
            "test": {
                "outputs": {
                    "empty_schema_target": {
                        "type": "databricks",
                        "catalog": "dbt_test_catalog", # Example catalog name
                        "schema": "empty_schema_for_test", # The schema that will be empty
                        "method": "http",
                        "host": "test-host",
                        "http_path": "test-path",
                        "token": "test-token",
                    }
                }
            }
        }

    # Override the default unique_schema to a fixed name for the populated schema
    @pytest.fixture(scope="class")
    def unique_schema(self):
        return "populated_schema"

    def test_empty_schema_docs_generate_fails_with_type_conflict(self, project, monkeypatch):
        from dbt.adapters.databricks.impl import DatabricksAdapter

        def mock_get_schema_for_catalog(self_adapter, catalog: str, schema: str, identifier: str) -> agate.Table:
            if schema == "populated_schema":
                return POPULATED_AGATE_TABLE
            elif schema == "empty_schema_for_test":
                # Simulate the bug: column_name is incorrectly inferred as Number
                # when the result set is effectively empty for type inference purposes.
                return MockAgateTableForEmptySchema()
            else:
                return agate.Table.from_object([]) # Default for other schemas not in test

        monkeypatch.setattr(
            DatabricksAdapter,
            "_get_schema_for_catalog",
            mock_get_schema_for_catalog,
        )

        with pytest.raises(RuntimeError) as excinfo:
            run_dbt(["docs", "generate"])

        assert (
            "Tables contain columns with the same names (column_name), but different types"
            in str(excinfo.value)
        )
        # Check for both possible orders of Text and Number in the error message
        assert (
            ("<agate.data_types.text.Text object" in str(excinfo.value)
             and "<dbt_common.clients.agate_helper.Number object" in str(excinfo.value))
            or ("<dbt_common.clients.agate_helper.Number object" in str(excinfo.value)
                and "<agate.data_types.text.Text object" in str(excinfo.value))
        ), f"Expected type conflict, but got: {str(excinfo.value)}"
