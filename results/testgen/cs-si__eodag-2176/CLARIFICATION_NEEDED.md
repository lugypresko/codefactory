## Clarification Needed: Network Access for EODAG Tests

The GitHub issue describes an `AttributeError` that occurs when `eodag` attempts to process queryable information fetched from a remote STAC endpoint (specifically, `https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-rtc/queryables`).

The acceptance criteria for this task explicitly state: "There is no network access. Tests must not need the network."

EODAG, by its nature, makes network requests to fetch provider configurations (like `ext_collections.json`) and specific collection queryables from STAC endpoints. While I have successfully configured `eodag` to use a local `ext_collections.json` file by setting `EODAG_EXT_COLLECTIONS_CONF_URI`, the `planetary_computer` provider's configuration in `providers.yml` does not expose a direct option to redirect its STAC queryables endpoint to a local file. It implicitly constructs the URL for queryables from its `api_endpoint`.

To trigger the `AttributeError` (`'FieldInfo' object has no attribute 'asdict'`) as described in the issue, `eodag` needs to successfully retrieve a (potentially malformed, to trigger the bug) JSON response from the `/queryables` endpoint. Without network access, and without the ability to use standard mocking libraries (like `unittest.mock`) to intercept and provide a simulated HTTP response, it is impossible to reach the code path where the `AttributeError` occurs.

**Question for the reporter:**
How should I simulate the network response from `https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-rtc/queryables` to trigger the `AttributeError` without making actual network requests and without using dynamic mocking libraries that would alter the core `eodag` search plugin's behavior? Is there an `eodag` configuration option or environment variable that allows a provider's queryables endpoint to be directed to a local file or a hardcoded string representation of a JSON response?

Without a mechanism to provide a local equivalent of the network response for queryables, the test cannot proceed to the point of triggering the `AttributeError`.
