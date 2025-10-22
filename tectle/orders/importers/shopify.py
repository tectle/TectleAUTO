"""Importer for Shopify orders."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping

from ..models import Order, OrderItem
from .base import BaseOrderImporter


class ShopifyOrderImporter(BaseOrderImporter):
    """Normalize Shopify order payloads."""

    platform = "shopify"

    def parse_order(self, payload: Mapping[str, object]) -> Order:
        order_id = str(payload.get("id"))
        customer = payload.get("customer") or {}
        customer_name = self._build_customer_name(customer)
        customer_email = str(customer.get("email") or payload.get("email") or "")
        created_at = self._parse_datetime(payload.get("created_at"))
        status = str(payload.get("financial_status") or payload.get("fulfillment_status") or "open")
        currency = str(payload.get("currency") or "USD")
        fulfillment_status = payload.get("fulfillment_status")

        items = [self._parse_line_item(item, currency) for item in payload.get("line_items") or []]
        total_price = float(payload.get("total_price") or sum(item.price * item.quantity for item in items))

        return Order(
            id=order_id,
            platform=self.platform,
            created_at=created_at,
            customer_name=customer_name,
            customer_email=customer_email,
            status=status,
            currency=currency,
            total_price=total_price,
            items=items,
            fulfillment_status=str(fulfillment_status) if fulfillment_status else None,
            raw_payload=payload,
        )

    @staticmethod
    def _parse_line_item(payload: Mapping[str, object], default_currency: str) -> OrderItem:
        return OrderItem(
            sku=str(payload.get("sku") or payload.get("variant_id") or ""),
            name=str(payload.get("title") or ""),
            quantity=int(payload.get("quantity") or 0),
            price=float(payload.get("price") or 0.0),
            currency=str(payload.get("currency") or default_currency),
            metadata={
                "variant_title": str(payload.get("variant_title") or ""),
                "fulfillment_status": str(payload.get("fulfillment_status") or ""),
            },
        )

    @staticmethod
    def _build_customer_name(customer: Mapping[str, object]) -> str:
        if not customer:
            return ""
        first_name = str(customer.get("first_name") or "").strip()
        last_name = str(customer.get("last_name") or "").strip()
        if first_name or last_name:
            return (first_name + " " + last_name).strip()
        return str(customer.get("name") or "")

    @staticmethod
    def _parse_datetime(value: object) -> datetime:
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass
        return datetime.now(tz=timezone.utc)
