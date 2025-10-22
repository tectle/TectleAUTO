"""Importer for Etsy orders."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping

from ..models import Order, OrderItem
from .base import BaseOrderImporter


class EtsyOrderImporter(BaseOrderImporter):
    """Convert Etsy order payloads into normalized :class:`Order` objects."""

    platform = "etsy"

    def parse_order(self, payload: Mapping[str, object]) -> Order:
        receipt_id = str(payload.get("receipt_id") or payload.get("order_id"))
        buyer = payload.get("buyer") or {}
        customer_name = str(buyer.get("name") or buyer.get("username") or "")
        customer_email = str(buyer.get("email") or "")
        created_at = self._parse_datetime(payload.get("creation_tsz"))
        status = str(payload.get("status") or "open")
        currency = str(payload.get("currency_code") or "USD")
        transactions = payload.get("transactions") or []

        items = [self._parse_transaction(tx, currency) for tx in transactions]
        total_price = float(payload.get("grandtotal") or sum(item.price * item.quantity for item in items))
        fulfillment_status = str(payload.get("fulfillment_status") or payload.get("was_paid") or "pending")

        return Order(
            id=receipt_id,
            platform=self.platform,
            created_at=created_at,
            customer_name=customer_name,
            customer_email=customer_email,
            status=status,
            currency=currency,
            total_price=total_price,
            items=items,
            fulfillment_status=fulfillment_status if fulfillment_status else None,
            raw_payload=payload,
        )

    @staticmethod
    def _parse_transaction(payload: Mapping[str, object], default_currency: str) -> OrderItem:
        currency = str(payload.get("currency_code") or default_currency)
        return OrderItem(
            sku=str(payload.get("product_id") or payload.get("listing_id") or ""),
            name=str(payload.get("title") or payload.get("name") or ""),
            quantity=int(payload.get("quantity") or 0),
            price=float(payload.get("price") or payload.get("transaction_total") or 0.0),
            currency=currency,
            metadata={
                "transaction_id": str(payload.get("transaction_id") or ""),
            },
        )

    @staticmethod
    def _parse_datetime(value: object) -> datetime:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        if isinstance(value, str) and value.isdigit():
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
        return datetime.now(tz=timezone.utc)
