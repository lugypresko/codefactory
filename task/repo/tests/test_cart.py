import pytest
from cart import Cart


def test_empty_cart():
    c = Cart()
    assert c.item_count() == 0
    assert c.total() == 0


def test_add_items_and_total():
    c = Cart()
    c.add_item("apple", 1.25, 4)
    c.add_item("pear", 2.0)
    assert c.item_count() == 5
    assert c.subtotal() == 7.0
    assert c.total() == 7.0


def test_add_same_sku_accumulates():
    c = Cart()
    c.add_item("apple", 1.0, 2)
    c.add_item("apple", 1.0, 3)
    assert c.item_count() == 5


def test_invalid_qty():
    with pytest.raises(ValueError):
        Cart().add_item("x", 1.0, 0)


def test_invalid_price():
    with pytest.raises(ValueError):
        Cart().add_item("x", -1.0)
