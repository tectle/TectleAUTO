from tectle.orders.service import OrderService
from tectle.ui.sample_data import load_sample_payloads
from tectle.ui.server import render_dashboard


def _load_orders():
    service = OrderService()
    return service.import_all(load_sample_payloads())


def test_dashboard_renders_sample_data():
    orders = _load_orders()
    html = render_dashboard(orders)
    assert "Tectle Orders Dashboard" in html
    assert "Ada Lovelace" in html
    assert "Sticker Pack" in html


def test_dashboard_filters_by_status():
    orders = _load_orders()
    html = render_dashboard(orders, status_filter="closed")
    assert "ETSY-1001" not in html
    assert "ETSY-1002" in html


def test_dashboard_filters_by_platform():
    orders = _load_orders()
    html = render_dashboard(orders, platform_filter="etsy")
    assert "ETSY-1001" in html
    assert "Sticker Pack" not in html
