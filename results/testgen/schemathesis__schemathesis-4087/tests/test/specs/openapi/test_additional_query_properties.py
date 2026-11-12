import datetime
import pytest
from flask import Flask, jsonify, request
import schemathesis
from schemathesis import Case
from schemathesis.config import SchemathesisConfig as Config
from schemathesis.engine import events # Keep this import for event types, but remove Dispatcher
from schemathesis.generation.modes import GenerationMode
import json
from urllib.parse import urlparse, urlencode, parse_qsl

@pytest.fixture
def additional_query_parameter_app_and_schema(ctx):
    app = Flask("test_app")

    @app.route("/items", methods=["GET"])
    def get_items():
        return jsonify({"message": "OK", "query": request.args}), 200

    schema_dict = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/items": {
                "get": {
                    "parameters": [
                        {
                            "name": "name",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "message": {"type": "string"},
                                            "query": {"type": "object"},
                                        },
                                        "required": ["message", "query"],
                                        "additionalProperties": True
                                    }
                                }
                            }
                        }
                    },
                }
            }
        },
    }
    
    schema = schemathesis.openapi.from_dict(schema_dict)
    return app, schema


def test_additional_query_properties_are_not_flagged_as_errors(additional_query_parameter_app_and_schema, mocker):
    app, schema = additional_query_parameter_app_and_schema
    base_url = "http://localhost"

    original_prepare_requests = Case.prepare_requests

    def prepare_request_with_extra_query(self, **kwargs):
        request = original_prepare_requests(self, **kwargs)
        if self.operation.path == "/items" and self.operation.method == "GET":
            parsed_url = urlparse(request.url)
            query_params = dict(parse_qsl(parsed_url.query))
            query_params["extra_param"] = "some_value_from_monkeypatch"
            modified_query = urlencode(query_params)
            request.url = parsed_url._replace(query=modified_query).geturl()
        return request

    mocker.patch("schemathesis.Case.prepare_requests", new=prepare_request_with_extra_query)

    config = Config(
        data_generation_methods=[GenerationMode.default()],
    )

    # Run tests and get the result object
    test_result = schemathesis.run_tests(
        schema,
        base_url=base_url,
        app=app, 
        hypothesis_settings=schemathesis.extra.hypothesis.settings(max_examples=50), 
        config=config,
    )

    # Now, inspect the `test_result` object for failures
    found_additional_properties_failure = False
    for result in test_result.results:
        if result.status == events.Status.failure: # Assuming events.Status.failure exists
            for error in result.errors:
                error_message = str(error)
                if "violates `additionalProperties` (False)" in error_message and "query" in error_message:
                    found_additional_properties_failure = True
                    print(f"Found unexpected additionalProperties query violation: {error_message}")
                    break
        if found_additional_properties_failure:
            break

    assert found_additional_properties_failure, (
        "Schemathesis should flag additional query parameters as schema violations "
        "when `additionalProperties` is not explicitly set to `False` for query parameters in the schema. "
        "The server implicitly allows them."
    )
