"""Sample payloads for the HTML dashboard."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Mapping, Sequence

Payload = Mapping[str, Sequence[Mapping[str, object]]]


def load_sample_payloads() -> Dict[str, List[Mapping[str, object]]]:
    """Return example payloads for the dashboard."""

    created = datetime(2024, 5, 10, 14, 30, tzinfo=timezone.utc)
    return {
        "etsy": [
            {
                "receipt_id": "ETSY-1001",
                "creation_tsz": int(created.timestamp()),
                "status": "open",
                "currency_code": "USD",
                "buyer": {"name": "Ada Lovelace", "email": "ada@example.com"},
                "transactions": [
                    {
                        "listing_id": "SKU-1",
                        "title": "Notebook",
                        "quantity": 2,
                        "price": "12.50",
                    },
                    {
                        "listing_id": "SKU-2",
                        "title": "Pen Set",
                        "quantity": 1,
                        "price": "8.00",
                    },
                ],
                "grandtotal": "33.00",
                "fulfillment_status": "processing",
            },
            {
                "receipt_id": "ETSY-1002",
                "creation_tsz": int(created.replace(day=9).timestamp()),
                "status": "closed",
                "currency_code": "USD",
                "buyer": {"name": "Katherine Johnson", "email": "kj@example.com"},
                "transactions": [
                    {
                        "listing_id": "SKU-3",
                        "title": "Planner",
                        "quantity": 1,
                        "price": "18.00",
                    }
                ],
                "grandtotal": "18.00",
                "fulfillment_status": "shipped",
            },
        ],
        "shopify": [
            {
                "id": 456,
                "created_at": "2024-05-08T09:15:00Z",
                "financial_status": "paid",
                "currency": "USD",
                "customer": {
                    "first_name": "Grace",
                    "last_name": "Hopper",
                    "email": "grace@example.com",
                },
                "line_items": [
                    {
                        "sku": "SKU-4",
                        "title": "Sticker Pack",
                        "quantity": 3,
                        "price": "4.00",
                    }
                ],
                "total_price": "12.00",
                "fulfillment_status": "fulfilled",
            },
            {
                "id": 789,
                "created_at": "2024-05-11T11:45:00Z",
                "financial_status": "pending",
                "currency": "USD",
                "customer": {
                    "first_name": "Margaret",
                    "last_name": "Hamilton",
                    "email": "margaret@example.com",
                },
                "line_items": [
                    {
                        "sku": "SKU-5",
                        "title": "Algorithm Poster",
                        "quantity": 1,
                        "price": "25.00",
                    }
                ],
                "total_price": "25.00",
                "fulfillment_status": "unfulfilled",
            },
        ],
    }
