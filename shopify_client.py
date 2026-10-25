"""Talks to the Shopify Admin GraphQL API of your dev store.

Needs these environment variables (set them as Codespaces secrets):
    SHOPIFY_SHOP           store name without ".myshopify.com", e.g. "demo-basics"
    SHOPIFY_CLIENT_ID      from your app's settings in the Dev Dashboard
    SHOPIFY_CLIENT_SECRET  from your app's settings in the Dev Dashboard

Run `python shopify_client.py` to test the connection.
"""
import os
import time

import requests

from config import SHOPIFY_API_VERSION

_token = {"value": None, "expires_at": 0.0}


def _shop() -> str:
    return os.environ["SHOPIFY_SHOP"].replace(".myshopify.com", "").strip()


def get_token() -> str:
    """Get an access token with the client credentials grant.

    Tokens expire after about 24 hours, so we cache one and fetch a new one
    shortly before it runs out.
    """
    if _token["value"] and time.time() < _token["expires_at"] - 60:
        return _token["value"]
    response = requests.post(
        f"https://{_shop()}.myshopify.com/admin/oauth/access_token",
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ["SHOPIFY_CLIENT_ID"],
            "client_secret": os.environ["SHOPIFY_CLIENT_SECRET"],
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    _token["value"] = data["access_token"]
    _token["expires_at"] = time.time() + int(data.get("expires_in", 86399))
    return _token["value"]


def graphql(query: str, variables: dict | None = None) -> dict:
    """Send one GraphQL request and return its "data" part."""
    response = requests.post(
        f"https://{_shop()}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/graphql.json",
        headers={"X-Shopify-Access-Token": get_token(), "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}},
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    if body.get("errors"):
        raise RuntimeError(f"Shopify error: {body['errors']}")
    return body["data"]


def list_products() -> list[dict]:
    """All products as {"id", "title", "description_html"}."""
    query = """
    query {
      products(first: 50) {
        nodes { id title descriptionHtml }
      }
    }"""
    nodes = graphql(query)["products"]["nodes"]
    return [{"id": n["id"], "title": n["title"], "description_html": n["descriptionHtml"] or ""} for n in nodes]


def sales_by_product() -> dict[str, int]:
    """Units sold per product title, summed over all orders."""
    query = """
    query($cursor: String) {
      orders(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes { lineItems(first: 50) { nodes { title quantity } } }
      }
    }"""
    totals: dict[str, int] = {}
    cursor = None
    while True:
        orders = graphql(query, {"cursor": cursor})["orders"]
        for order in orders["nodes"]:
            for item in order["lineItems"]["nodes"]:
                totals[item["title"]] = totals.get(item["title"], 0) + item["quantity"]
        if not orders["pageInfo"]["hasNextPage"]:
            return totals
        cursor = orders["pageInfo"]["endCursor"]


def update_description(product_id: str, description_html: str) -> None:
    """Replace a product's description (needs the write_products scope)."""
    mutation = """
    mutation($product: ProductUpdateInput!) {
      productUpdate(product: $product) {
        product { id }
        userErrors { field message }
      }
    }"""
    result = graphql(mutation, {"product": {"id": product_id, "descriptionHtml": description_html}})
    errors = result["productUpdate"]["userErrors"]
    if errors:
        raise RuntimeError(f"Shopify could not update the product: {errors}")


if __name__ == "__main__":
    print("Testing the Shopify connection ...")
    products = list_products()
    print(f"{len(products)} products found:")
    for p in products:
        print("  -", p["title"])
    print("Units sold per product:")
    for title, units in sales_by_product().items():
        print(f"  - {title}: {units}")
