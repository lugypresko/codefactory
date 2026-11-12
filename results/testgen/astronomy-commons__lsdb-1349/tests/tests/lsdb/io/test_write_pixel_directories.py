import os
import shutil
from pathlib import Path

import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest

import lsdb
from lsdb.io.to_hats import to_hats

def test_write_catalog_with_pixel_directories(small_sky_catalog, tmp_path):
    catalog_path = Path(tmp_path) / "pixel_catalog"
    catalog_name = "pixel_catalog"

    # Write the catalog with pixel directories enabled
    small_sky_catalog.write_catalog(
        catalog_path, catalog_name=catalog_name, addl_hats_properties={"npix_suffix": "/"}
    )

    # Verify the directory structure
    # Expected: catalog_path/dataset/Norder=X/Dir=Y/Npix=Z/0.parquet
    # Find one example parquet file to assert its path
    found_parquet_file = False
    for root, dirs, files in os.walk(catalog_path / "dataset"):
        for file in files:
            if file.endswith(".parquet"):
                # Check for the Npix=Z directory before 0.parquet
                relative_path = Path(root).relative_to(catalog_path / "dataset")
                parts = relative_path.parts
                # Expecting parts like ('Norder=X', 'Dir=Y', 'Npix=Z')
                if len(parts) == 3 and parts[0].startswith("Norder=") and parts[1].startswith("Dir=") and parts[2].startswith("Npix="):
                    if file == "0.parquet":
                        found_parquet_file = True
                        break
        if found_parquet_file:
            break

    assert found_parquet_file, "No parquet file found in the expected Norder/Dir/Npix/0.parquet structure."

    # Read the catalog back and verify data integrity
    read_catalog = lsdb.read_hats(catalog_path)
    pd.testing.assert_frame_equal(read_catalog.compute(), small_sky_catalog.compute())

def test_write_catalog_with_pixel_directories_custom_filename(small_sky_catalog, tmp_path):
    catalog_path = Path(tmp_path) / "pixel_catalog_custom"
    catalog_name = "pixel_catalog_custom"
    custom_filename = "my_data.parquet"

    # The current `write_catalog` (and `to_hats`) doesn't have an explicit way to specify
    # the parquet file name within the pixel directory.
    # This test assumes a future fix might introduce a way to do this,
    # or that the `npix_suffix` might imply this behavior.
    # For now, it tests if the default `0.parquet` is created, and marks it as an
    # expected failure if a custom name is desired but not implemented.
    # It will fail because the current system likely ignores `npix_suffix` for writing,
    # or doesn't allow custom naming within pixel directories.

    # This test will initially fail because the feature is not implemented.
    # The expected behavior for this test case is to successfully write a catalog
    # with pixel directories and a custom parquet file name.

    # This `addl_hats_properties` is a placeholder for a future API.
    # The actual implementation might use a different property or a new function argument.
    addl_props = {
        "npix_suffix": "/",
        "parquet_file_name": custom_filename, # Assuming a new property for custom naming
    }

    small_sky_catalog.write_catalog(
        catalog_path, catalog_name=catalog_name, addl_hats_properties=addl_props
    )

    found_custom_parquet_file = False
    for root, dirs, files in os.walk(catalog_path / "dataset"):
        for file in files:
            if file == custom_filename:
                relative_path = Path(root).relative_to(catalog_path / "dataset")
                parts = relative_path.parts
                if len(parts) == 3 and parts[0].startswith("Norder=") and parts[1].startswith("Dir=") and parts[2].startswith("Npix="):
                    found_custom_parquet_file = True
                    break
        if found_custom_parquet_file:
            break

    assert found_custom_parquet_file, f"No parquet file named {custom_filename} found in the expected Norder/Dir/Npix/{custom_filename} structure."

    read_catalog = lsdb.read_hats(catalog_path)
    pd.testing.assert_frame_equal(read_catalog.compute(), small_sky_catalog.compute())

