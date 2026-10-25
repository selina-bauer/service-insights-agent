"""Step 2: group classified tickets with SQL and flag unusual product/topic pairs.

Usage:
    python cluster.py
    python cluster.py --model claude-sonnet-5-5   # use that model's classifications
"""
import argparse

import shop_data
from config import CLASSIFY_MODEL, MIN_TICKETS, MIN_TICKETS_PER_100_SOLD
from db import connect

# Tickets per product and topic, set in relation to how often the product sold.
# A bestseller gets more tickets anyway, so the ratio matters more than the count.
FINDINGS_SQL = """
SELECT c.product,
       c.topic,
       COUNT(*)                                  AS tickets,
       s.units_sold,
       ROUND(100.0 * COUNT(*) / s.units_sold, 1) AS tickets_per_100
FROM classified AS c
JOIN sales AS s ON s.product = c.product
WHERE c.model = :model
  AND c.topic != 'Sonstiges'
  AND s.units_sold > 0
GROUP BY c.product, c.topic
HAVING COUNT(*) >= :min_tickets
   AND 100.0 * COUNT(*) / s.units_sold >= :min_rate
ORDER BY tickets_per_100 DESC;
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=CLASSIFY_MODEL)
    args = parser.parse_args()

    con = connect()

    # Refresh sales numbers from Shopify (or data/shop.json)
    sales = shop_data.sales_by_product()
    con.execute("DELETE FROM sales")
    con.executemany("INSERT INTO sales (product, units_sold) VALUES (?, ?)", sales.items())

    rows = con.execute(FINDINGS_SQL, {
        "model": args.model,
        "min_tickets": MIN_TICKETS,
        "min_rate": MIN_TICKETS_PER_100_SOLD,
    }).fetchall()

    # Replace this model's earlier findings and their open proposals
    old_ids = [r[0] for r in con.execute("SELECT id FROM findings WHERE model = ?", (args.model,))]
    if old_ids:
        marks = ",".join("?" * len(old_ids))
        con.execute(f"DELETE FROM proposals WHERE status = 'open' AND finding_id IN ({marks})", old_ids)
        con.execute("DELETE FROM findings WHERE model = ?", (args.model,))

    for r in rows:
        con.execute(
            """INSERT INTO findings (model, product, topic, tickets, units_sold, tickets_per_100)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (args.model, r["product"], r["topic"], r["tickets"], r["units_sold"], r["tickets_per_100"]),
        )
    con.commit()

    print(f"Thresholds: at least {MIN_TICKETS} tickets and {MIN_TICKETS_PER_100_SOLD} tickets per 100 units sold")
    if not rows:
        print("No findings.")
    for r in rows:
        print(f"  {r['product']} | {r['topic']}: {r['tickets']} tickets, "
              f"{r['units_sold']} sold, {r['tickets_per_100']} per 100")


if __name__ == "__main__":
    main()
