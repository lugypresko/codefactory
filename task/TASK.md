Implement two features in the `cart` library in /repo:

1. `Cart.remove_item(sku, qty=1)`: decreases the quantity of an item. If the quantity reaches 0 the item is removed entirely. Removing an unknown sku raises `KeyError`. Removing more than the quantity in the cart raises `ValueError` (cart unchanged). qty must be positive (`ValueError` otherwise).

2. `Cart.apply_discount(code)`: supports the discount codes `SAVE10` (10% off) and `SAVE25` (25% off). Codes are case-insensitive. An unknown code raises `ValueError` and leaves any existing discount unchanged. Discounts don't stack: applying a new code replaces the previous one. `subtotal()` stays the undiscounted sum; `total()` returns the discounted subtotal rounded to 2 decimals (round half up, e.g. 22.995 -> 23.00), and always reflects the current cart contents.

Existing behavior must not break. Add tests for the new behavior in tests/. Run the test suite with `cd /repo && python -m pytest -q`. The environment has no network access; pytest is already installed.
