"""Utilities for organizing orders."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, MutableMapping, Sequence

from .models import Order


@dataclass(slots=True)
class OrderSummary:
    """Aggregated statistics about a set of orders."""

    total_orders: int
    open_orders: int
    total_revenue: float
    total_items: int


class OrderOrganizer:
    """Helper utilities for grouping and summarising orders."""

    def group_by_status(self, orders: Iterable[Order]) -> Dict[str, List[Order]]:
        """Group orders by their status."""

        grouped: MutableMapping[str, List[Order]] = defaultdict(list)
        for order in orders:
            grouped[order.status.lower()].append(order)
        return dict(grouped)

    def group_by_fulfillment(self, orders: Iterable[Order]) -> Dict[str, List[Order]]:
        """Group orders by fulfillment status."""

        grouped: MutableMapping[str, List[Order]] = defaultdict(list)
        for order in orders:
            key = (order.fulfillment_status or "unfulfilled").lower()
            grouped[key].append(order)
        return dict(grouped)

    def sort_orders(self, orders: Sequence[Order], *, reverse: bool = False) -> List[Order]:
        """Return orders sorted by creation date."""

        return sorted(orders, key=lambda order: order.created_at, reverse=reverse)

    def summary(self, orders: Iterable[Order]) -> OrderSummary:
        """Produce an :class:`OrderSummary` for the supplied orders."""

        total_orders = 0
        open_orders = 0
        total_revenue = 0.0
        total_items = 0

        for order in orders:
            total_orders += 1
            total_revenue += order.total_price
            total_items += order.total_quantity
            if order.is_open:
                open_orders += 1

        return OrderSummary(
            total_orders=total_orders,
            open_orders=open_orders,
            total_revenue=round(total_revenue, 2),
            total_items=total_items,
        )

    def to_report(self, orders: Iterable[Order]) -> Mapping[str, object]:
        """Build a dictionary report summarising the orders."""

        orders_list = list(orders)
        return {
            "summary": self.summary(orders_list),
            "by_status": {k: len(v) for k, v in self.group_by_status(orders_list).items()},
            "by_fulfillment": {
                k: len(v) for k, v in self.group_by_fulfillment(orders_list).items()
            },
        }
