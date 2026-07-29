"""
Tests for restocking API endpoints.
"""
from datetime import datetime

import pytest


class TestRestockingEndpoints:
    """Test suite for restocking-related endpoints."""

    def test_get_all_restock_orders(self, client):
        """Test getting all restock orders."""
        response = client.get("/api/restock-orders")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_get_restock_lead_times(self, client):
        """Test getting supplier lead times by category."""
        response = client.get("/api/restock-lead-times")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)

        expected_categories = [
            "Circuit Boards",
            "Sensors",
            "Power Supplies",
            "Actuators",
            "Controllers"
        ]
        for category in expected_categories:
            assert category in data
            assert isinstance(data[category], int)
            assert data[category] > 0

    def test_create_restock_order(self, client):
        """Test creating a restock order."""
        response = client.post("/api/restock-orders", json={
            "budget": 25000,
            "items": [
                {"sku": "TMP-201", "quantity": 85},
                {"sku": "PCB-003", "quantity": 30}
            ]
        })
        assert response.status_code == 201

        order = response.json()
        assert order["id"].startswith("RST-")
        assert order["order_number"].startswith("RST-")
        assert order["status"] == "Processing"
        assert order["budget"] == 25000
        assert len(order["items"]) == 2

        # Server enriches each line from the matching inventory item
        for item in order["items"]:
            assert item["name"]
            assert item["category"]
            assert isinstance(item["unit_cost"], (int, float))
            assert isinstance(item["line_total"], (int, float))
            assert isinstance(item["lead_time_days"], int)

    def test_create_restock_order_ignores_client_supplied_cost(self, client):
        """Test that unit cost comes from inventory, not the request body."""
        inventory = client.get("/api/inventory").json()
        real_cost = next(i["unit_cost"] for i in inventory if i["sku"] == "TMP-201")

        response = client.post("/api/restock-orders", json={
            "budget": 25000,
            "items": [{"sku": "TMP-201", "quantity": 10, "unit_cost": 0.01}]
        })
        assert response.status_code == 201

        item = response.json()["items"][0]
        assert item["unit_cost"] == real_cost
        assert abs(item["line_total"] - 10 * real_cost) < 0.01

    def test_create_restock_order_total_value_calculation(self, client):
        """Test that the order total matches quantity times unit cost."""
        inventory = client.get("/api/inventory").json()
        inventory_by_sku = {item["sku"]: item for item in inventory}

        requested = [
            {"sku": "TMP-201", "quantity": 85},
            {"sku": "PSU-508", "quantity": 90}
        ]
        response = client.post("/api/restock-orders", json={
            "budget": 50000,
            "items": requested
        })
        assert response.status_code == 201

        order = response.json()
        calculated_total = sum(
            line["quantity"] * inventory_by_sku[line["sku"]]["unit_cost"]
            for line in requested
        )
        assert abs(order["total_value"] - calculated_total) < 0.01

    def test_create_restock_order_lead_time_is_max(self, client):
        """Test that order lead time is the longest across its items."""
        lead_times = client.get("/api/restock-lead-times").json()

        # TMP-201 is Sensors (short), PWM-404 is Controllers (long)
        response = client.post("/api/restock-orders", json={
            "budget": 50000,
            "items": [
                {"sku": "TMP-201", "quantity": 5},
                {"sku": "PWM-404", "quantity": 5}
            ]
        })
        assert response.status_code == 201

        order = response.json()
        assert order["lead_time_days"] == max(
            lead_times["Sensors"], lead_times["Controllers"]
        )

    def test_create_restock_order_expected_delivery(self, client):
        """Test that expected delivery is the order date plus the lead time."""
        response = client.post("/api/restock-orders", json={
            "budget": 10000,
            "items": [{"sku": "PCB-003", "quantity": 30}]
        })
        assert response.status_code == 201

        order = response.json()

        # Dates must match the format used across the rest of the dataset:
        # full ISO with a time component and no microseconds
        assert "T" in order["order_date"]
        assert "T" in order["expected_delivery"]
        assert "." not in order["order_date"]
        assert "." not in order["expected_delivery"]

        ordered = datetime.strptime(order["order_date"], "%Y-%m-%dT%H:%M:%S")
        delivered = datetime.strptime(order["expected_delivery"], "%Y-%m-%dT%H:%M:%S")
        assert (delivered - ordered).days == order["lead_time_days"]

    def test_create_restock_order_appears_in_list(self, client):
        """Test that a created restock order is returned by the list endpoint."""
        before = client.get("/api/restock-orders").json()

        response = client.post("/api/restock-orders", json={
            "budget": 10000,
            "items": [{"sku": "PCB-003", "quantity": 30}]
        })
        assert response.status_code == 201
        created = response.json()

        after = client.get("/api/restock-orders").json()
        assert len(after) == len(before) + 1
        assert any(order["order_number"] == created["order_number"] for order in after)

    def test_create_restock_order_sequence(self, client):
        """Test that consecutive restock orders get incrementing numbers."""
        first = client.post("/api/restock-orders", json={
            "budget": 10000,
            "items": [{"sku": "PCB-003", "quantity": 10}]
        }).json()
        second = client.post("/api/restock-orders", json={
            "budget": 10000,
            "items": [{"sku": "PCB-003", "quantity": 10}]
        }).json()

        assert first["id"] != second["id"]
        assert first["order_number"].endswith("0001")
        assert second["order_number"].endswith("0002")

    def test_create_restock_order_nonexistent_sku(self, client):
        """Test creating a restock order for a SKU that doesn't exist."""
        response = client.post("/api/restock-orders", json={
            "budget": 10000,
            "items": [{"sku": "ZZZ-999", "quantity": 5}]
        })
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_create_restock_order_empty_items(self, client):
        """Test that a restock order must contain at least one item."""
        response = client.post("/api/restock-orders", json={
            "budget": 10000,
            "items": []
        })
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data

    def test_create_restock_order_invalid_quantity(self, client):
        """Test that item quantities must be greater than zero."""
        for quantity in [0, -5]:
            response = client.post("/api/restock-orders", json={
                "budget": 10000,
                "items": [{"sku": "PCB-003", "quantity": quantity}]
            })
            assert response.status_code == 400, f"quantity {quantity} should be rejected"

    def test_create_restock_order_malformed_body(self, client):
        """Test that a malformed request body is rejected."""
        response = client.post("/api/restock-orders", json={})
        assert response.status_code == 422

    def test_restock_order_does_not_pollute_orders(self, client):
        """Test that restock orders stay out of the customer orders list."""
        orders_before = client.get("/api/orders").json()
        summary_before = client.get("/api/dashboard/summary")
        assert summary_before.status_code == 200

        response = client.post("/api/restock-orders", json={
            "budget": 25000,
            "items": [{"sku": "TMP-201", "quantity": 85}]
        })
        assert response.status_code == 201

        # A restock order has no customer and would fail the Order response_model,
        # so leaking one into `orders` would 500 these endpoints
        orders_after = client.get("/api/orders")
        assert orders_after.status_code == 200
        assert len(orders_after.json()) == len(orders_before)

        summary_after = client.get("/api/dashboard/summary")
        assert summary_after.status_code == 200
        assert summary_after.json() == summary_before.json()
