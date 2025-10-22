"""High level service for importing and organizing orders."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, MutableMapping, Sequence

from .importers import BaseOrderImporter, EtsyOrderImporter, ShopifyOrderImporter
from .models import Order
from .organizer import OrderOrganizer


@dataclass
class OrderService:
    """Coordinate order imports across multiple platforms."""

    organizer: OrderOrganizer = field(default_factory=OrderOrganizer)
    importers: MutableMapping[str, BaseOrderImporter] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.importers:
            self.importers.update(
                {
                    "etsy": EtsyOrderImporter(),
                    "shopify": ShopifyOrderImporter(),
                }
            )

    def register_importer(self, importer: BaseOrderImporter) -> None:
        """Register an importer instance for a platform."""

        self.importers[importer.platform.lower()] = importer

    def import_orders(
        self, platform: str, raw_orders: Iterable[Mapping[str, object]]
    ) -> List[Order]:
        """Import orders for a single platform using the registered importer."""

        importer = self._get_importer(platform)
        return importer.import_orders(raw_orders)

    def import_all(
        self, payload: Mapping[str, Sequence[Mapping[str, object]]]
    ) -> List[Order]:
        """Import orders from multiple platforms and return a combined list."""

        all_orders: List[Order] = []
        for platform, raw_orders in payload.items():
            importer = self._get_importer(platform)
            all_orders.extend(importer.import_orders(raw_orders))
        return self.organizer.sort_orders(all_orders)

    def organize_by_status(
        self, orders: Iterable[Order]
    ) -> Dict[str, List[Order]]:
        return self.organizer.group_by_status(orders)

    def report(self, orders: Iterable[Order]) -> Mapping[str, object]:
        """Return a structured summary report for the given orders."""

        return self.organizer.to_report(orders)

    def _get_importer(self, platform: str) -> BaseOrderImporter:
        key = platform.lower()
        if key not in self.importers:
            raise KeyError(f"No importer registered for platform '{platform}'")
        return self.importers[key]
