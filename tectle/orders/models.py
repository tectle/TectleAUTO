"""Data models for Tectle order management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Mapping, Optional


@dataclass(slots=True)
class OrderItem:
    """Represents a single line item within an order."""

    sku: str
    name: str
    quantity: int
    price: float
    currency: str
    metadata: Dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, object]:
        """Serialize the order item to a dictionary."""

        return {
            "sku": self.sku,
            "name": self.name,
            "quantity": self.quantity,
            "price": self.price,
            "currency": self.currency,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class Order:
    """Represents a normalized order coming from any sales channel."""

    id: str
    platform: str
    created_at: datetime
    customer_name: str
    customer_email: str
    status: str
    currency: str
    total_price: float
    items: List[OrderItem]
    fulfillment_status: Optional[str] = None
    raw_payload: Optional[Mapping[str, object]] = None

    def as_dict(self) -> Dict[str, object]:
        """Serialize the order to a dictionary for downstream consumers."""

        return {
            "id": self.id,
            "platform": self.platform,
            "created_at": self.created_at.isoformat(),
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "status": self.status,
            "currency": self.currency,
            "total_price": self.total_price,
            "items": [item.as_dict() for item in self.items],
            "fulfillment_status": self.fulfillment_status,
        }

    @property
    def is_open(self) -> bool:
        """Return whether the order is in a state that requires action."""

        return self.status.lower() in {"open", "unfulfilled", "processing"}

    @property
    def total_quantity(self) -> int:
        """Return the total quantity of all items within the order."""

        return sum(item.quantity for item in self.items)


def ensure_iterable(value: Optional[Iterable[OrderItem]]) -> List[OrderItem]:
    """Ensure the provided items are converted into a list."""

    if value is None:
        return []
    if isinstance(value, list):
        return value
    return list(value)
