import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

import requests

from app import create_app
from cli import main


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_crud_workflow(self):
        self.assertEqual(len(self.client.get("/inventory").json), 1)
        created = self.client.post("/inventory", json={
            "product_name": "Oats", "price": 3.5, "stock": 7,
        })
        self.assertEqual(created.status_code, 201)
        path = f'/inventory/{created.json["id"]}'
        self.assertEqual(self.client.get(path).json["stock"], 7)
        updated = self.client.patch(path, json={"stock": 0, "price": 2.5})
        self.assertEqual(updated.json["stock"], 0)
        self.assertEqual(updated.json["price"], 2.5)
        self.assertEqual(self.client.delete(path).status_code, 204)
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_invalid_payloads(self):
        self.assertEqual(self.client.post("/inventory", json=[]).status_code, 400)
        for changes in ({"stock": -1}, {"price": True}, {"id": 3}, {"product_name": " "}):
            with self.subTest(changes=changes):
                self.assertEqual(self.client.patch("/inventory/1", json=changes).status_code, 400)
        self.assertEqual(self.client.get("/inventory/1").json["stock"], 12)

    @patch("app.requests.get")
    def test_lookup_by_barcode_and_name(self, get):
        product = {"product_name": "Oats", "brands": "Sample", "code": "1234"}
        get.return_value.status_code = 200
        get.return_value.json.side_effect = [{"product": product}, {"products": [product]}]
        self.assertEqual(self.client.get("/products/search?query=1234").json, product)
        self.assertTrue(get.call_args.args[0].endswith("/api/v2/product/1234"))
        self.assertEqual(self.client.get("/products/search?query=Oats").json, product)
        self.assertEqual(get.call_args.kwargs["params"]["search_terms"], "Oats")

    @patch("app.requests.get")
    def test_lookup_errors(self, get):
        self.assertEqual(self.client.get("/products/search").status_code, 400)
        get.assert_not_called()
        get.return_value.status_code = 404
        self.assertEqual(self.client.get("/products/search?query=1234").status_code, 404)
        get.side_effect = requests.Timeout
        self.assertEqual(self.client.get("/products/search?query=1234").status_code, 502)

    @patch("cli.requests.request")
    def test_cli_import_posts_product_details(self, send):
        product = {"product_name": "Oats", "brands": "Sample", "code": "1234"}
        item = {**product, "stock": 7, "price": 3.5}
        send.side_effect = [
            Mock(ok=True, status_code=200, json=Mock(return_value=product)),
            Mock(ok=True, status_code=201, json=Mock(return_value={"id": 2, **item})),
        ]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["import", "1234", "3.50", "7"]), 0)
        self.assertEqual(send.call_args.args[0], "POST")
        self.assertEqual(send.call_args.kwargs["json"], item)
