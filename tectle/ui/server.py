"""Simple HTML dashboard for exploring Tectle orders."""

from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import List, Mapping, Optional, Sequence
from urllib.parse import parse_qs, urlencode, urlparse

from tectle.orders.models import Order
from tectle.orders.organizer import OrderOrganizer, OrderSummary
from tectle.orders.service import OrderService

from .sample_data import load_sample_payloads


@dataclass(slots=True)
class DashboardState:
    """Runtime state for the dashboard server."""

    orders: List[Order]
    organizer: OrderOrganizer

    def filter_orders(
        self, *, status: Optional[str] = None, platform: Optional[str] = None
    ) -> List[Order]:
        status_key = status.lower() if status else None
        platform_key = platform.lower() if platform else None
        filtered: List[Order] = []
        for order in self.orders:
            if status_key and order.status.lower() != status_key:
                continue
            if platform_key and order.platform.lower() != platform_key:
                continue
            filtered.append(order)
        return self.organizer.sort_orders(filtered, reverse=True)


def _format_currency(value: float, currency: str) -> str:
    return f"{currency} {value:,.2f}" if currency else f"{value:,.2f}"


def _format_datetime(dt: datetime) -> str:
    if dt.tzinfo:
        return dt.astimezone().strftime("%Y-%m-%d %H:%M %Z")
    return dt.strftime("%Y-%m-%d %H:%M")


def _escape(value: object) -> str:
    return html.escape(str(value))


def _build_query(**params: Optional[str]) -> str:
    cleaned = {k: v for k, v in params.items() if v}
    if not cleaned:
        return "/"
    return "/?" + urlencode(cleaned)


def _render_filters(
    state: DashboardState,
    *,
    active_status: Optional[str] = None,
    active_platform: Optional[str] = None,
) -> str:
    organizer = state.organizer
    status_counts = organizer.group_by_status(state.orders)
    platform_counts = Counter(order.platform.lower() for order in state.orders)

    status_links = [
        _filter_link(
            label=f"All statuses ({len(state.orders)})",
            href=_build_query(platform=active_platform),
            active=not active_status,
        )
    ]
    for status, orders in sorted(status_counts.items()):
        status_key = status.lower()
        status_links.append(
            _filter_link(
                label=f"{status.title()} ({len(orders)})",
                href=_build_query(status=status_key, platform=active_platform),
                active=active_status == status_key,
            )
        )

    platform_links = [
        _filter_link(
            label=f"All platforms ({len(state.orders)})",
            href=_build_query(status=active_status),
            active=not active_platform,
        )
    ]
    for platform, count in sorted(platform_counts.items()):
        platform_links.append(
            _filter_link(
                label=f"{platform.title()} ({count})",
                href=_build_query(status=active_status, platform=platform),
                active=active_platform == platform,
            )
        )

    return f"""
    <section class="filters">
        <div>
            <h2>Status</h2>
            <nav class="filter-group">{''.join(status_links)}</nav>
        </div>
        <div>
            <h2>Platform</h2>
            <nav class="filter-group">{''.join(platform_links)}</nav>
        </div>
    </section>
    """


def _filter_link(*, label: str, href: str, active: bool) -> str:
    classes = "filter-link active" if active else "filter-link"
    return f'<a class="{classes}" href="{href}">{_escape(label)}</a>'


def _render_summary(summary: OrderSummary) -> str:
    metrics = [
        ("Total Orders", summary.total_orders),
        ("Open Orders", summary.open_orders),
        ("Total Items", summary.total_items),
        ("Total Revenue", f"{summary.total_revenue:,.2f}"),
    ]
    metric_html = "".join(
        f"<div class='metric'><span class='label'>{_escape(label)}</span><span class='value'>{_escape(value)}</span></div>"
        for label, value in metrics
    )
    return f"<section class='summary'>{metric_html}</section>"


def _render_orders_table(orders: Sequence[Order]) -> str:
    if not orders:
        return "<p class='empty'>No orders match the current filters.</p>"

    rows = "".join(_render_order_row(order) for order in orders)
    return f"""
    <table class="orders">
        <thead>
            <tr>
                <th>Order</th>
                <th>Created</th>
                <th>Customer</th>
                <th>Status</th>
                <th>Fulfillment</th>
                <th>Total</th>
                <th>Details</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    """


def _render_order_row(order: Order) -> str:
    items_details = "".join(
        f"<li><span class='sku'>{_escape(item.sku)}</span> — {_escape(item.name)} × {item.quantity} @ {_format_currency(item.price, item.currency)}</li>"
        for item in order.items
    )
    raw_payload = json.dumps(order.raw_payload, indent=2, default=str) if order.raw_payload else "{}"
    customer_email = _escape(order.customer_email) if order.customer_email else "<span class='muted'>No email</span>"
    fulfillment = _escape(order.fulfillment_status or "—")
    return f"""
    <tr>
        <td>
            <strong>{_escape(order.id)}</strong>
            <div class="muted">{_escape(order.platform.title())}</div>
        </td>
        <td>{_escape(_format_datetime(order.created_at))}</td>
        <td>
            <div>{_escape(order.customer_name or 'Unknown customer')}</div>
            <div class="muted">{customer_email}</div>
        </td>
        <td><span class="status">{_escape(order.status.title())}</span></td>
        <td>{fulfillment}</td>
        <td>{_escape(_format_currency(order.total_price, order.currency))}</td>
        <td>
            <details>
                <summary>{len(order.items)} items / {order.total_quantity} units</summary>
                <ul class="items">{items_details}</ul>
            </details>
            <details>
                <summary>Raw payload</summary>
                <pre>{_escape(raw_payload)}</pre>
            </details>
        </td>
    </tr>
    """


def render_dashboard(
    orders: Sequence[Order],
    *,
    status_filter: Optional[str] = None,
    platform_filter: Optional[str] = None,
) -> str:
    """Return the dashboard HTML for the supplied orders."""

    organizer = OrderOrganizer()
    state = DashboardState(orders=list(organizer.sort_orders(orders, reverse=True)), organizer=organizer)
    filtered = state.filter_orders(status=status_filter, platform=platform_filter)
    summary = organizer.summary(filtered)
    filters_html = _render_filters(state, active_status=(status_filter or "").lower() or None, active_platform=(platform_filter or "").lower() or None)
    table_html = _render_orders_table(filtered)

    def _label(value: Optional[str]) -> str:
        if not value:
            return "All"
        return value.replace("_", " ").title()

    status_label = _label(status_filter)
    platform_label = _label(platform_filter)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>Tectle Orders Dashboard</title>
    <style>
        :root {{
            color-scheme: light dark;
            font-family: system-ui, sans-serif;
        }}
        body {{
            margin: 0;
            padding: 0;
            background: #f6f8fb;
            color: #1d1f24;
        }}
        header {{
            background: linear-gradient(120deg, #2845ff, #7324ff);
            color: white;
            padding: 2.5rem 3rem 1.5rem;
        }}
        header h1 {{
            margin: 0 0 0.5rem 0;
            font-size: 2rem;
        }}
        header p {{
            margin: 0;
            opacity: 0.85;
        }}
        main {{
            padding: 2rem 3rem 4rem;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .metric {{
            background: white;
            border-radius: 0.75rem;
            padding: 1rem 1.25rem;
            box-shadow: 0 10px 25px rgba(31, 35, 45, 0.1);
        }}
        .metric .label {{
            display: block;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #5b6170;
            margin-bottom: 0.35rem;
        }}
        .metric .value {{
            font-size: 1.75rem;
            font-weight: 600;
        }}
        .filters {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        .filters h2 {{
            margin-bottom: 0.5rem;
        }}
        .filter-group {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}
        .filter-link {{
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 0.35rem 0.9rem;
            background: rgba(115, 36, 255, 0.1);
            color: #4520a5;
            text-decoration: none;
            font-weight: 500;
        }}
        .filter-link.active {{
            background: #4520a5;
            color: white;
        }}
        table.orders {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 1rem;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(31, 35, 45, 0.12);
        }}
        table.orders th {{
            text-align: left;
            padding: 0.75rem 1rem;
            background: #f0f2f8;
            color: #3a3f4b;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        table.orders td {{
            padding: 1rem;
            vertical-align: top;
            border-top: 1px solid #eef0f6;
        }}
        table.orders tr:first-child td {{
            border-top: none;
        }}
        .status {{
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            background: rgba(40, 69, 255, 0.12);
            color: #2845ff;
            font-weight: 600;
            font-size: 0.85rem;
        }}
        details {{
            margin-top: 0.5rem;
        }}
        details summary {{
            cursor: pointer;
            font-weight: 600;
            color: #2845ff;
        }}
        ul.items {{
            margin: 0.5rem 0 0 1rem;
            padding: 0;
            list-style-type: disc;
        }}
        ul.items li {{
            margin-bottom: 0.35rem;
        }}
        .muted {{
            color: #6b7183;
            font-size: 0.85rem;
        }}
        pre {{
            background: #0f172a;
            color: #e2e8f0;
            padding: 1rem;
            border-radius: 0.75rem;
            overflow-x: auto;
        }}
        .empty {{
            padding: 2rem;
            background: white;
            border-radius: 1rem;
            text-align: center;
            color: #5b6170;
            box-shadow: 0 10px 30px rgba(31, 35, 45, 0.05);
        }}
        @media (prefers-color-scheme: dark) {{
            body {{
                background: #0f172a;
                color: #e2e8f0;
            }}
            header {{
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.35);
            }}
            .metric, table.orders, .empty {{
                background: rgba(15, 23, 42, 0.8);
                box-shadow: 0 10px 30px rgba(15, 23, 42, 0.4);
            }}
            table.orders th {{
                background: rgba(148, 163, 184, 0.15);
            }}
            table.orders td {{
                border-top-color: rgba(148, 163, 184, 0.1);
            }}
            .filter-link {{
                background: rgba(129, 140, 248, 0.2);
                color: #c7d2fe;
            }}
            .filter-link.active {{
                background: #6366f1;
            }}
            .muted {{
                color: #94a3b8;
            }}
            pre {{
                background: rgba(15, 23, 42, 0.95);
            }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>Tectle Orders Dashboard</h1>
        <p>Showing {len(filtered)} orders (Status: {status_label}, Platform: {platform_label})</p>
    </header>
    <main>
        {_render_summary(summary)}
        {filters_html}
        {table_html}
    </main>
</body>
</html>
    """


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP handler that serves the dashboard."""

    state: DashboardState

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        parsed = urlparse(self.path)
        if parsed.path not in {"/", ""}:
            self.send_error(404)
            return

        params = parse_qs(parsed.query)
        status_filter = params.get("status", [None])[0]
        platform_filter = params.get("platform", [None])[0]

        html_body = render_dashboard(
            self.state.orders,
            status_filter=status_filter.lower() if status_filter else None,
            platform_filter=platform_filter.lower() if platform_filter else None,
        )

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html_body.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(html_body.encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003 - signature inherited
        return


def _load_payload(path: Optional[Path]) -> Mapping[str, Sequence[Mapping[str, object]]]:
    if path is None:
        return load_sample_payloads()
    data = json.loads(path.read_text())
    if not isinstance(data, Mapping):
        raise ValueError("Payload file must contain a mapping of platform to orders")
    return data  # type: ignore[return-value]


def _load_orders(payload: Mapping[str, Sequence[Mapping[str, object]]]) -> List[Order]:
    service = OrderService()
    return service.import_all(payload)


def launch_dashboard(
    *, host: str = "127.0.0.1", port: int = 8000, data_path: Optional[str] = None
) -> None:
    """Start the dashboard web server."""

    payload = _load_payload(Path(data_path) if data_path else None)
    orders = _load_orders(payload)
    dashboard_state = DashboardState(orders=orders, organizer=OrderOrganizer())

    class Handler(DashboardHandler):
        state = dashboard_state  # type: ignore[assignment]

    with ThreadingHTTPServer((host, port), Handler) as httpd:
        address, bound_port = httpd.server_address
        print(f"Dashboard running on http://{address}:{bound_port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:  # pragma: no cover - manual interruption
            print("Shutting down dashboard...")


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Launch the Tectle orders dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server")
    parser.add_argument(
        "--data",
        type=Path,
        help="Path to a JSON file containing platform keyed payloads. Defaults to sample data.",
    )

    args = parser.parse_args(argv)
    launch_dashboard(host=args.host, port=args.port, data_path=str(args.data) if args.data else None)


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
