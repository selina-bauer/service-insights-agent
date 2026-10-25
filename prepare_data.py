"""Split the generated ticket file into the files the pipeline needs.

Input:  data/generated.csv   ticket_id,date,channel,text,product,topic
Output: data/tickets.csv     ticket_id,date,channel,text      (what the agent sees)
        data/handlabels.csv  ticket_id,product,topic          (your answer key)

It also checks product and topic names and prints how many tickets
each product/topic pair has, so you can see your hidden patterns.

Usage:
    python prepare_data.py
"""
import csv
from collections import Counter

import shop_data
from config import TOPICS

SOURCE = "data/generated.csv"


def main() -> None:
    with open(SOURCE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    products = set(shop_data.product_titles()) | {"unbekannt"}
    problems = 0
    for r in rows:
        for key in ("ticket_id", "text", "product", "topic"):
            r[key] = (r.get(key) or "").strip()
        if r["product"] not in products:
            print(f"Check {r['ticket_id']}: unknown product '{r['product']}'")
            problems += 1
        if r["topic"] not in TOPICS:
            print(f"Check {r['ticket_id']}: unknown topic '{r['topic']}'")
            problems += 1

    ids = [r["ticket_id"] for r in rows]
    duplicates = [i for i, n in Counter(ids).items() if n > 1]
    if duplicates:
        print(f"Duplicate ticket IDs: {duplicates}")
        problems += 1

    with open("data/tickets.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ticket_id", "date", "channel", "text"])
        for r in rows:
            writer.writerow([r["ticket_id"], r.get("date", ""), r.get("channel", ""), r["text"]])

    with open("data/handlabels.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ticket_id", "product", "topic"])
        for r in rows:
            writer.writerow([r["ticket_id"], r["product"], r["topic"]])

    print(f"\n{len(rows)} tickets written to data/tickets.csv and data/handlabels.csv")
    print("Tickets per product and topic (largest first):")
    for (product, topic), n in Counter((r["product"], r["topic"]) for r in rows).most_common(12):
        print(f"  {n:3d}  {product} | {topic}")
    if problems:
        print(f"\n{problems} problem(s) found. Fix them in data/generated.csv and run this again.")


if __name__ == "__main__":
    main()
