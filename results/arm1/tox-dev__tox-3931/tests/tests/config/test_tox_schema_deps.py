import json
from pathlib import Path
import pytest

def test_deps_property_allows_array_in_schema():
    schema_path = Path("/testbed/src/tox/tox.schema.json")
    assert schema_path.is_file(), f"Schema file not found at {schema_path}"

    with open(schema_path, "r") as f:
        schema = json.load(f)

    # Navigate to the deps property within the schema
    # The path might vary slightly, I'll assume a common structure based on the issue description:
    # `env_run_base` table property `deps`
    # Let's try to find `env_run_base` and then `deps` within its properties.
    try:
        # Look for definitions first, as schemas often use references
        # Based on the issue's image, it looks like `deps` is under `testenv` which is likely a definition
        # Let's try to find 'testenv' definition, then 'deps' within its properties
        testenv_definition = schema.get("$defs", {}).get("testenv")
        assert testenv_definition is not None, "Could not find $defs.testenv in schema"

        deps_property = testenv_definition.get("properties", {}).get("deps")
        assert deps_property is not None, "Could not find properties.deps under $defs.testenv"

        # Assert that the 'type' allows for arrays, not just strings.
        # According to the issue, the unfixed schema only accepts strings.
        # A fixed schema would likely have type as ["string", "array"] or use oneOf/anyOf.

        deps_type = deps_property.get("type")
        assert deps_type is not None, "deps property does not have a 'type' field"

        # Check if the type is explicitly just a string
        is_only_string = deps_type == "string"
        # Check if the type is an array containing only 'string'
        is_array_with_only_string = isinstance(deps_type, list) and len(deps_type) == 1 and deps_type[0] == "string"

        # If the schema only allows strings, the test should fail.
        # If it allows arrays (e.g., type is ["string", "array"] or a more complex oneOf/anyOf), it should pass.
        # So, we assert that it's *not* only a string type.
        assert not is_only_string and not is_array_with_only_string, \
            f"Schema for 'deps' property in testenv should allow arrays, but found type: {deps_type}"

    except KeyError as e:
        pytest.fail(f"Failed to navigate schema: {e}. Full schema: {json.dumps(schema, indent=2)}")


