"""A tiny shopping cart."""


class Cart:
    def __init__(self):
        self._items = {}  # sku -> {"price": float, "qty": int}

    def add_item(self, sku: str, price: float, qty: int = 1) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")
        if price < 0:
            raise ValueError("price must be non-negative")
        if sku in self._items:
            self._items[sku]["qty"] += qty
        else:
            self._items[sku] = {"price": price, "qty": qty}

    def item_count(self) -> int:
        return sum(i["qty"] for i in self._items.values())

    def subtotal(self) -> float:
        return round(sum(i["price"] * i["qty"] for i in self._items.values()), 2)

    def total(self) -> float:
        return self.subtotal()
