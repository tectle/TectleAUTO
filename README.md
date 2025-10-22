# Tectle Order Management

This repository provides the foundation for Tectle's order intake pipeline. It
normalises incoming orders from multiple commerce platforms (Etsy, Shopify, and
future integrations) into a unified data model and offers helpers to organise
and summarise those orders.

## Features

- Normalised `Order` and `OrderItem` data classes.
- Channel-specific importers for Etsy and Shopify, with an extensible base
  class for future integrations.
- Service layer that orchestrates imports and produces summary reports.
- Organizer utilities for grouping orders by status and fulfilment state.

## Getting Started

Install the project as an editable dependency:

```bash
pip install -e .
```

Then, use the service to ingest raw payloads from Etsy and Shopify:

```python
from tectle import OrderService

etsy_payloads = [
    {
        "receipt_id": "123",
        "creation_tsz": 1700000000,
        "status": "open",
        "currency_code": "USD",
        "buyer": {"name": "Ada Lovelace", "email": "ada@example.com"},
        "transactions": [
            {"listing_id": "SKU-1", "title": "Notebook", "quantity": 2, "price": "12.50"}
        ],
    }
]

shopify_payloads = [
    {
        "id": 456,
        "created_at": "2024-05-10T14:30:00Z",
        "financial_status": "paid",
        "currency": "USD",
        "customer": {"first_name": "Grace", "last_name": "Hopper", "email": "grace@example.com"},
        "line_items": [
            {"sku": "SKU-2", "title": "Sticker Pack", "quantity": 3, "price": "4.00"}
        ],
    }
]

service = OrderService()
orders = service.import_all({"etsy": etsy_payloads, "shopify": shopify_payloads})
report = service.report(orders)
print(report)
```

The example above demonstrates importing raw order payloads from Etsy and
Shopify, unifying them into the shared model, and producing a summary report.

## HTML Dashboard

Spin up a lightweight HTML dashboard to browse orders and their details:

```bash
python -m tectle.ui
```

By default the dashboard launches on <http://127.0.0.1:8000> with curated sample
data. Point it at your own payloads by supplying a JSON file that mirrors the
structure expected by `OrderService.import_all`:

```bash
python -m tectle.ui --data path/to/orders.json
```

Filters in the UI allow you to slice by status or platform, inspect item-level
details, and review the original raw payload for each order. You can also load
real Etsy exports directly from the dashboard header:

1. Click **Import Etsy Orders** in the hero area.
2. Select the JSON export you downloaded from Etsy.
3. Submit the form to merge the uploaded orders into the current view.

Only the `payload` field from the multipart form is read, so you can safely
attach exactly the file you received from Etsy without additional wrapping.

## Extending to New Platforms

To add support for another platform, subclass `BaseOrderImporter`, implement the
`parse_order` method, and register the importer with the `OrderService`:

```python
from tectle.orders.importers import BaseOrderImporter
from tectle.orders.models import Order


class FuturePlatformImporter(BaseOrderImporter):
    platform = "future"

    def parse_order(self, payload):
        # Convert `payload` into an Order instance
        ...

service = OrderService()
service.register_importer(FuturePlatformImporter())
```

This pattern keeps channel-specific logic isolated while providing a consistent
interface for downstream tooling.
