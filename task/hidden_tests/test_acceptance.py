"""Hidden acceptance tests (FAIL_TO_PASS). Never mounted into the agent container."""
import pytest
from cart import Cart


def make():
    c = Cart()
    c.add_item("apple", 10.0, 2)   # 20.00
    c.add_item("pear", 5.55, 1)    # 5.55 -> subtotal 25.55
    return c


def test_remove_item_partial():
    c = make()
    c.remove_item("apple", 1)
    assert c.item_count() == 2
    assert c.subtotal() == 15.55


def test_remove_item_all_removes_sku():
    c = make()
    c.remove_item("apple", 2)
    assert c.item_count() == 1
    assert c.subtotal() == 5.55


def test_remove_unknown_or_too_many_raises():
    c = make()
    with pytest.raises(KeyError):
        c.remove_item("banana", 1)
    with pytest.raises(ValueError):
        c.remove_item("apple", 3)


def test_discount_save10():
    c = make()
    c.apply_discount("SAVE10")
    assert c.subtotal() == 25.55
    assert c.total() == 23.0  # 25.55 * 0.9 = 22.995 -> 23.00


def test_discount_save25():
    c = make()
    c.apply_discount("SAVE25")
    assert c.total() == 19.16  # 25.55 * 0.75 = 19.1625


def test_discount_invalid_code():
    c = make()
    with pytest.raises(ValueError):
        c.apply_discount("FREE100")
    assert c.total() == 25.55


def test_discount_no_stacking_last_wins():
    c = make()
    c.apply_discount("SAVE25")
    c.apply_discount("SAVE10")
    assert c.total() == 23.0


def test_discount_case_insensitive():
    c = make()
    c.apply_discount("save10")
    assert c.total() == 23.0


def test_discount_applies_after_cart_changes():
    c = make()
    c.apply_discount("SAVE10")
    c.add_item("pear", 5.55, 1)  # subtotal 31.10
    assert c.total() == 27.99
