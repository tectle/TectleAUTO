"""Base classes and interfaces for order importers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List, Mapping

from ..models import Order


class BaseOrderImporter(ABC):
    """Base class used by channel specific order importers."""

    platform: str

    def import_orders(self, raw_orders: Iterable[Mapping[str, object]]) -> List[Order]:
        """Transform raw order payloads into normalized :class:`Order` objects."""

        return [self.parse_order(payload) for payload in raw_orders]

    @abstractmethod
    def parse_order(self, payload: Mapping[str, object]) -> Order:
        """Convert a raw payload into an :class:`Order`."""

    def __repr__(self) -> str:  # pragma: no cover - simple helper
        return f"{self.__class__.__name__}(platform={self.platform!r})"
