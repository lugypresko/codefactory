import pytest
from virtualizarr import open_virtual_dataset
from virtualizarr.parsers import KerchunkJSONParser
from obspec_utils.registry import ObjectStoreRegistry
from obstore.store import LocalStore

def test_open_virtual_dataset_with_inlined_data_raises_notimplementederror():
    """
    Tests that open_virtual_dataset raises NotImplementedError when attempting
    to read a kerchunk file with inlined reference data.
    """
    kerchunk_file_path = "/tmp/inlined_kerchunk.json"
    expected_error_message = "Reading inlined reference data is currently not supported. [ToDo]"

    file_url = f"file://{kerchunk_file_path}"
    registry = ObjectStoreRegistry({"file:///": LocalStore("/")})
    parser = KerchunkJSONParser()

    with pytest.raises(NotImplementedError) as excinfo:
        open_virtual_dataset(file_url, registry=registry, parser=parser)

    assert expected_error_message in str(excinfo.value)
