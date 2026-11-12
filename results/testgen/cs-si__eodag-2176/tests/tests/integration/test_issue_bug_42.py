import os
import pytest
from eodag import EODataAccessGateway, setup_logging

def test_sentinel_1_rtc_search_raises_attribute_error():
    # Set environment variables as described in the issue
    os.environ["EODAG__PLANETARY_COMPUTER__AUTH__CREDENTIALS__API_KEY"] = "xxx"
    os.environ["EODAG_PROVIDERS_WHITELIST"] = "planetary_computer"

    os.environ["EODAG_EXT_COLLECTIONS_CONF_URI"] = "file:///tmp/ext_collections.json"
    # Setup logging (optional for test, but good for debugging if needed)
    # setup_logging(3)  # DEBUG level

    # Create gateway and set preferred provider
    dag = EODataAccessGateway()
    dag.set_preferred_provider("planetary_computer")

    # The problematic search call
    with pytest.raises(AttributeError) as excinfo:
        dag.search_all(
            start='2021-02-10T00:00:00',
            end='2021-02-15T00:00:00',
            geom='POLYGON ((-0.957009651999954 43.624143975, -1.21432507 43.6304504720001, -1.21265838699998 43.6866459940001, -0.836793908999937 43.8657935370001, -0.776473646999932 43.866692545, -0.776474895999968 43.747621789, -0.957009651999954 43.624143975))',
            collection="sentinel-1-rtc"
        )
    # Assert the specific error message
    assert "'FieldInfo' object has no attribute 'asdict'" in str(excinfo.value)

    # Clean up environment variables to avoid interfering with other tests
    del os.environ["EODAG__PLANETARY_COMPUTER__AUTH__CREDENTIALS__API_KEY"]
    del os.environ["EODAG_PROVIDERS_WHITELIST"]
