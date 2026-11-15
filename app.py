from itertools import count
from math import isfinite
from threading import Lock

import requests
from flask import Flask, jsonify, request

BASE_URL = "https://world.openfoodfacts.org"
PRODUCT_FIELDS = ("product_name", "brands", "ingredients_text", "code")
ITEM_FIELDS = {*PRODUCT_FIELDS, "price", "stock"}


def find_product(query):
    options = {
        "headers": {"User-Agent": "InventoryManagementLab/1.0 (educational demo)"},
        "timeout": 10,
    }
    fields = ",".join(PRODUCT_FIELDS)
    if query.isascii() and query.isdigit():
        response = requests.get(
            f"{BASE_URL}/api/v2/product/{query}",
            params={"fields": fields},
            **options,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        product = response.json().get("product")
    else:
        response = requests.get(
            f"{BASE_URL}/cgi/search.pl",
            params={"search_terms": query, "search_simple": 1, "action": "process",
                    "json": 1, "page_size": 10, "fields": fields},
            **options,
        )
        response.raise_for_status()
        product = next(
            (item for item in response.json().get("products", []) if item.get("product_name")),
            None,
        )
    if product and product.get("product_name"):
        return {field: product[field] for field in PRODUCT_FIELDS if isinstance(product.get(field), str)}
    return None


def validate_item(data, partial=False):
    if not isinstance(data, dict) or not data or data.keys() - ITEM_FIELDS:
        return "Send an object containing supported inventory fields."
    if not partial and not {"product_name", "price", "stock"} <= data.keys():
        return "Product name, price, and stock are required."
    for field, value in data.items():
        if field == "stock":
            if type(value) is not int or value < 0:
                return "Stock must be a nonnegative integer."
        elif field == "price":
            if type(value) not in (int, float) or value < 0 or (
                isinstance(value, float) and not isfinite(value)
            ):
                return "Price must be a finite nonnegative number."
        elif not isinstance(value, str) or (field == "product_name" and not value.strip()):
            return f"Invalid {field}."
    return None


def create_app():
    app = Flask(__name__)
    inventory = [
        {"id": 1, "product_name": "Organic Almond Milk", "brands": "Sample Brand",
         "ingredients_text": "Filtered water, almonds", "price": 3.49, "stock": 12},
    ]
    ids = count(2)
    lock = Lock()

    @app.route("/inventory", methods=["GET", "POST"])
    def collection():
        if request.method == "GET":
            with lock:
                return jsonify(inventory)

        data = request.get_json(silent=True)
        error = validate_item(data)
        if error:
            return jsonify(error=error), 400
        with lock:
            item = {"id": next(ids), **data}
            inventory.append(item)
            return jsonify(item), 201

    @app.route("/inventory/<int:item_id>", methods=["GET", "PATCH", "DELETE"])
    def item_detail(item_id):
        with lock:
            item = next((item for item in inventory if item["id"] == item_id), None)
            if item is None:
                return jsonify(error="Inventory item not found."), 404
            if request.method == "DELETE":
                inventory.remove(item)
                return "", 204
            if request.method == "PATCH":
                data = request.get_json(silent=True)
                error = validate_item(data, partial=True)
                if error:
                    return jsonify(error=error), 400
                item.update(data)
            return jsonify(item)

    @app.get("/products/search")
    def search():
        query = request.args.get("query", "").strip()
        if not query:
            return jsonify(error="Enter a product name or barcode."), 400
        try:
            product = find_product(query)
        except (requests.RequestException, ValueError, AttributeError, TypeError):
            return jsonify(error="Open Food Facts is unavailable."), 502
        if product is None:
            return jsonify(error="Product not found."), 404
        return jsonify(product)

    return app


app = create_app()
