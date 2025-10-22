from datetime import datetime, timezone

import pytest

from tectle.orders.importers import BaseOrderImporter
from tectle.orders.models import Order, OrderItem
from tectle.orders.service import OrderService


class DummyImporter(BaseOrderImporter):
    platform = "dummy"

    def parse_order(self, payload):
        return Order(
            id=str(payload["id"]),
            platform=self.platform,
            created_at=datetime.fromtimestamp(payload.get("created_at", 0), tz=timezone.utc),
            customer_name=payload.get("customer_name", ""),
            customer_email=payload.get("customer_email", ""),
            status=payload.get("status", "open"),
            currency=payload.get("currency", "USD"),
            total_price=float(payload.get("total_price", 0.0)),
            items=[
                OrderItem(
                    sku="SKU",
                    name="Item",
                    quantity=payload.get("quantity", 1),
                    price=float(payload.get("total_price", 0.0)),
                    currency=payload.get("currency", "USD"),
                )
            ],
        )


def test_import_all_combines_platforms():
    service = OrderService()
    orders = service.import_all(
        {
            "etsy": [
                {
                    "receipt_id": "1",
                    "creation_tsz": 1700000000,
                    "buyer": {"name": "Ada", "email": "ada@example.com"},
                    "transactions": [{"listing_id": "A", "quantity": 1, "price": "10.00"}],
                }
            ],
            "shopify": [
                {
                    "id": "2",
                    "created_at": "2024-05-10T14:30:00Z",
                    "customer": {"first_name": "Grace", "last_name": "Hopper", "email": "grace@example.com"},
                    "line_items": [{"sku": "B", "quantity": 2, "price": "5.00"}],
                }
            ],
        }
    )

    assert len(orders) == 2
    assert {order.platform for order in orders} == {"etsy", "shopify"}


def test_register_importer_extends_supported_platforms():
    service = OrderService()
    importer = DummyImporter()
    service.register_importer(importer)

    orders = service.import_orders("dummy", [{"id": 1, "created_at": 1700000100}])
    assert len(orders) == 1
    assert orders[0].platform == "dummy"


def test_register_importer_conflict_requires_replace():
    service = OrderService()

    class AlternativeEtsyImporter(BaseOrderImporter):
        platform = "etsy"

        def parse_order(self, payload):
            return Order(
                id="alt",
                platform=self.platform,
                created_at=datetime.fromtimestamp(0, tz=timezone.utc),
                customer_name="",
                customer_email="",
                status="open",
                currency="USD",
                total_price=0.0,
                items=[],
            )

    importer = AlternativeEtsyImporter()

    with pytest.raises(ValueError):
        service.register_importer(importer)

    service.register_importer(importer, replace=True)
    orders = service.import_orders("etsy", [{"receipt_id": "x"}])
    assert orders[0].id == "alt"


def test_report_provides_summary():
    service = OrderService()
    orders = service.import_all(
        {
            "etsy": [
                {
                    "receipt_id": "1",
                    "creation_tsz": 1700000000,
                    "status": "open",
                    "transactions": [{"listing_id": "A", "quantity": 2, "price": "3.00"}],
                },
                {
                    "receipt_id": "2",
                    "creation_tsz": 1700000200,
                    "status": "completed",
                    "transactions": [{"listing_id": "B", "quantity": 1, "price": "5.00"}],
                },
            ]
        }
    )

    report = service.report(orders)
    summary = report["summary"]

    assert summary.total_orders == 2
    assert summary.open_orders == 1
    assert summary.total_items == 3
    assert summary.total_revenue == pytest.approx(11.0)
