"""Step 1: classify every ticket (product, topic, detail, sentiment).

Usage:
    python classify.py --tickets data/tickets.csv
    python classify.py --tickets data/tickets.csv --model claude-sonnet-5-5
    python classify.py --tickets data/tickets.csv --limit 10      # quick test
    python classify.py --fresh                                    # start over for this model

Tickets that were already classified with the same model are skipped,
so you can stop and restart at any time.
"""
import argparse
import csv
import time

import shop_data
from config import CLASSIFY_MODEL, TOPICS, cost_usd
from db import connect
from llm import client, parse_json, response_text

PROMPT = """Du ordnest Kundenservice-Tickets eines Mode-Onlineshops ein.

Produkte im Shop (exakte Namen):
{products}

Erlaubte Themen: {topics}

Antworte ausschließlich mit einem JSON-Objekt in genau diesem Format:
{{"product": "<exakter Produktname aus der Liste oder unbekannt>",
  "topic": "<genau eines der erlaubten Themen>",
  "detail": "<Kernanliegen in höchstens 6 Wörtern>",
  "sentiment": "<positiv, neutral oder negativ>"}}

Regeln:
Themen-Definitionen:
- Passform: Größe, Schnitt und Sitz eines Produkts, auch Größenberatung vor dem Kauf (z. B. "M oder L?").
- Qualität: Verarbeitung und Haltbarkeit, z. B. Nähte, Löcher, Einlaufen, Ausleiern.
- Lieferung: Versand, Lieferzeit, Sendungsstatus, Zustellung, Lieferadresse, falscher oder fehlender Artikel im Paket.
- Farbe/Material: Farbe oder Material weicht von Foto oder Beschreibung ab, Verfärben, Ausbleichen, Fragen zur Materialzusammensetzung.
- Sonstiges: alles andere, z. B. Zahlung, Rechnung, Gutscheine, Kundenkonto, Newsletter, Ablauf von Rücksendungen, Verfügbarkeit von Größen oder Farben, Lob, Sortiment.

Regeln:
- Hat das Ticket mehrere Anliegen, wähle das produktbezogene Hauptanliegen.
- Lässt sich kein Produkt eindeutig zuordnen, schreibe "unbekannt".
- Erfinde keine Produktnamen.

Ticket:
{ticket}"""


def load_tickets(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def classify_ticket(text: str, products: list[str], model: str) -> tuple[dict, object, float]:
    prompt = PROMPT.format(products="\n".join(f"- {p}" for p in products),
                           topics=", ".join(TOPICS), ticket=text)
    start = time.perf_counter()
    response = client.messages.create(
        model=model,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    seconds = time.perf_counter() - start
    result = parse_json(response_text(response))

    # Guard rails: only allow known products and topics
    if result.get("product") not in products:
        result["product"] = "unbekannt"
    if result.get("topic") not in TOPICS:
        result["topic"] = "Sonstiges"
    return result, response.usage, seconds


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickets", default="data/tickets.csv")
    parser.add_argument("--model", default=CLASSIFY_MODEL)
    parser.add_argument("--limit", type=int, default=0, help="only classify the first N tickets")
    parser.add_argument("--fresh", action="store_true",
                        help="delete this model's earlier results first (after you changed the prompt)")
    args = parser.parse_args()

    con = connect()
    if args.fresh:
        con.execute("DELETE FROM classified WHERE model = ?", (args.model,))
        con.commit()
        print(f"Deleted earlier results of {args.model}.")
    tickets = load_tickets(args.tickets)
    if args.limit:
        tickets = tickets[: args.limit]
    con.executemany(
        "INSERT OR REPLACE INTO tickets (ticket_id, date, channel, text) VALUES (?, ?, ?, ?)",
        [(t["ticket_id"], t.get("date", ""), t.get("channel", ""), t["text"]) for t in tickets],
    )
    con.commit()

    products = shop_data.product_titles()
    done = {row[0] for row in con.execute("SELECT ticket_id FROM classified WHERE model = ?", (args.model,))}
    todo = [t for t in tickets if t["ticket_id"] not in done]
    print(f"{len(tickets)} tickets, {len(done)} already classified with {args.model}, {len(todo)} to go.")

    total_cost = 0.0
    for i, ticket in enumerate(todo, start=1):
        try:
            result, usage, seconds = classify_ticket(ticket["text"], products, args.model)
        except Exception as error:  # keep going if one ticket fails
            print(f"  [{i}/{len(todo)}] {ticket['ticket_id']}: FAILED ({error})")
            continue
        con.execute(
            """INSERT OR REPLACE INTO classified
               (ticket_id, model, product, topic, detail, sentiment, input_tokens, output_tokens, seconds)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ticket["ticket_id"], args.model, result["product"], result["topic"],
             result.get("detail", ""), result.get("sentiment", ""),
             usage.input_tokens, usage.output_tokens, seconds),
        )
        con.commit()
        total_cost += cost_usd(args.model, usage.input_tokens, usage.output_tokens)
        print(f"  [{i}/{len(todo)}] {ticket['ticket_id']}: {result['product']} | {result['topic']} | {result.get('detail', '')}")

    print(f"Done. Cost of this run: about ${total_cost:.4f}")


if __name__ == "__main__":
    main()
