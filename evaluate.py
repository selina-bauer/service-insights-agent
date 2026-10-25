"""Step 5: measure quality, cost and speed.

Compares the results with your own answer key:
    data/handlabels.csv          ticket_id,product,topic        (tickets you labelled by hand)
    data/expected_patterns.csv   product,topic                  (patterns you hid in the tickets)

Usage:
    python evaluate.py
    python evaluate.py --model claude-sonnet-5-5
"""
import argparse
import csv

from config import CLASSIFY_MODEL, cost_usd
from db import connect


def load_csv_into(con, path: str, table: str, columns: list[str]) -> int:
    """Load a CSV file into a temporary table so we can compare with SQL."""
    con.execute(f"DROP TABLE IF EXISTS {table}")
    con.execute(f"CREATE TEMP TABLE {table} ({', '.join(c + ' TEXT' for c in columns)})")
    with open(path, encoding="utf-8") as f:
        rows = [[r[c].strip() for c in columns] for r in csv.DictReader(f)]
    con.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * len(columns))})", rows)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=CLASSIFY_MODEL)
    parser.add_argument("--handlabels", default="data/handlabels.csv")
    parser.add_argument("--patterns", default="data/expected_patterns.csv")
    args = parser.parse_args()
    con = connect()

    # 1. Classification accuracy against your hand labels
    load_csv_into(con, args.handlabels, "handlabels", ["ticket_id", "product", "topic"])
    acc = con.execute(
        """SELECT COUNT(*) AS n,
                  ROUND(100.0 * SUM(c.product = h.product) / COUNT(*), 1) AS product_ok,
                  ROUND(100.0 * SUM(c.topic = h.topic) / COUNT(*), 1)     AS topic_ok,
                  ROUND(100.0 * SUM(c.product = h.product AND c.topic = h.topic) / COUNT(*), 1) AS both_ok
           FROM handlabels h
           JOIN classified c ON c.ticket_id = h.ticket_id AND c.model = ?""",
        (args.model,),
    ).fetchone()

    wrong = con.execute(
        """SELECT h.ticket_id, h.product AS expected_product, h.topic AS expected_topic,
                  c.product, c.topic
           FROM handlabels h
           JOIN classified c ON c.ticket_id = h.ticket_id AND c.model = ?
           WHERE c.product != h.product OR c.topic != h.topic""",
        (args.model,),
    ).fetchall()

    # 2. Pattern detection against the patterns you hid
    n_patterns = load_csv_into(con, args.patterns, "expected", ["product", "topic"])
    found = con.execute(
        """SELECT e.product, e.topic FROM expected e
           JOIN findings f ON f.product = e.product AND f.topic = e.topic AND f.model = ?""",
        (args.model,),
    ).fetchall()
    false_alarms = con.execute(
        """SELECT f.product, f.topic, f.tickets FROM findings f
           LEFT JOIN expected e ON e.product = f.product AND e.topic = f.topic
           WHERE f.model = ? AND e.product IS NULL""",
        (args.model,),
    ).fetchall()

    # 3. Cost and speed
    cls = con.execute(
        """SELECT COUNT(*) AS n, SUM(input_tokens) AS tin, SUM(output_tokens) AS tout, AVG(seconds) AS sec
           FROM classified WHERE model = ?""",
        (args.model,),
    ).fetchone()
    cls_cost = cost_usd(args.model, cls["tin"] or 0, cls["tout"] or 0)
    ana = con.execute(
        """SELECT p.model, COUNT(*) AS n, SUM(p.input_tokens) AS tin, SUM(p.output_tokens) AS tout,
                  AVG(p.seconds) AS sec
           FROM proposals p JOIN findings f ON f.id = p.finding_id
           WHERE f.model = ? GROUP BY p.model""",
        (args.model,),
    ).fetchall()
    ana_cost = sum(cost_usd(r["model"], r["tin"] or 0, r["tout"] or 0) for r in ana)

    print(f"\n=== Evaluation for classification model {args.model} ===")
    print(f"Hand-labelled tickets compared: {acc['n']}")
    print(f"  product correct: {acc['product_ok']} %  | topic correct: {acc['topic_ok']} %  | both: {acc['both_ok']} %")
    for w in wrong:
        print(f"    {w['ticket_id']}: expected {w['expected_product']} / {w['expected_topic']}, "
              f"got {w['product']} / {w['topic']}")
    print(f"Patterns found: {len(found)} of {n_patterns}")
    for f in found:
        print(f"    found: {f['product']} / {f['topic']}")
    print(f"False alarms: {len(false_alarms)}")
    for f in false_alarms:
        print(f"    {f['product']} / {f['topic']} ({f['tickets']} tickets)")
    print(f"Classification: {cls['n']} tickets, ${cls_cost:.4f} total, "
          f"${(cls_cost / cls['n'] * 1000) if cls['n'] else 0:.3f} per 1,000 tickets, "
          f"{(cls['sec'] or 0):.1f} s per ticket")
    for r in ana:
        print(f"Analysis ({r['model']}): {r['n']} findings, "
              f"${cost_usd(r['model'], r['tin'] or 0, r['tout'] or 0):.4f}, {(r['sec'] or 0):.1f} s per finding")
    print(f"Total cost of this run: ${cls_cost + ana_cost:.4f}")

    print("\nRow for your results table (paste into README / PDF):")
    print(f"| {args.model} | {acc['both_ok']} % | {len(found)} of {n_patterns} | {len(false_alarms)} "
          f"| ${cls_cost + ana_cost:.3f} | {(cls['sec'] or 0):.1f} s |")


if __name__ == "__main__":
    main()
