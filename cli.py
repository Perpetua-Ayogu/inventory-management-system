import argparse
import json
import sys

import requests


def main(argv=None):
    parser = argparse.ArgumentParser(description="Manage store inventory")
    parser.add_argument("--url", default="http://127.0.0.1:5000")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    for name in ("get", "update", "delete"):
        command = commands.add_parser(name)
        command.add_argument("id", type=int)
        if name == "update":
            command.add_argument("--price", type=float)
            command.add_argument("--stock", type=int)
    commands.add_parser("lookup").add_argument("query")
    for name in ("add", "import"):
        command = commands.add_parser(name)
        command.add_argument("query" if name == "import" else "product_name")
        command.add_argument("price", type=float)
        command.add_argument("stock", type=int)
    args = parser.parse_args(argv)

    def call(method, path, **options):
        response = requests.request(method, args.url.rstrip("/") + path, timeout=15, **options)
        if not response.ok:
            try:
                message = response.json().get("error", response.reason)
            except ValueError:
                message = response.reason
            raise RuntimeError(f"{response.status_code}: {message}")
        return None if response.status_code == 204 else response.json()

    try:
        if args.command == "list":
            result = call("GET", "/inventory")
        elif args.command in ("lookup", "import"):
            result = call("GET", "/products/search", params={"query": args.query})
            if args.command == "import":
                result = call("POST", "/inventory", json={**result, "price": args.price, "stock": args.stock})
        elif args.command == "add":
            result = call("POST", "/inventory", json={
                "product_name": args.product_name, "price": args.price, "stock": args.stock,
            })
        else:
            path = f"/inventory/{args.id}"
            if args.command == "update":
                changes = {field: getattr(args, field) for field in ("price", "stock")
                           if getattr(args, field) is not None}
                if not changes:
                    parser.error("update requires --price or --stock")
                result = call("PATCH", path, json=changes)
            elif args.command == "delete":
                call("DELETE", path)
                result = {"deleted": args.id}
            else:
                result = call("GET", path)
    except (requests.RequestException, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
