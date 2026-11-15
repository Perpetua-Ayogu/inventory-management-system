# Inventory Management System

A Flask inventory API with a Python command-line client. The API starts with
one sample item in an in-memory list. Restarting the server resets inventory.
Product details come from [Open Food Facts](https://world.openfoodfacts.org/).

## Run

Install dependencies with `python -m pip install -r requirements.txt`.
Start the API with `python -m flask --app app run`. In another terminal:

```text
python cli.py list
python cli.py add "Oat Milk" 3.99 10
python cli.py get 2
python cli.py update 2 --stock 8
python cli.py delete 2
python cli.py lookup "Almond Milk"
python cli.py import 3017620422003 4.99 5
```

## API

| Method and path | Input | Result |
| --- | --- | --- |
| GET /inventory | None | All items |
| GET /inventory/<id> | Item ID | One item |
| POST /inventory | JSON with product_name, price, and stock | New item with assigned ID (201) |
| PATCH /inventory/<id> | JSON with fields to change | Updated item |
| DELETE /inventory/<id> | Item ID | Empty response (204) |
| GET /products/search | query parameter with a barcode or name | Product details for the first named match |

Items may also include brands, ingredients_text, and code. Invalid requests
return 400, missing records return 404, and upstream failures return 502.
The import command looks up a product and posts its details with price and stock.

## Test

Run `python -m unittest discover -v`. Tests use Flask's test client and mock
the external HTTP calls so they can run without an internet connection.
