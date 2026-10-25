"""Step 3: an agent analyses each finding and writes a proposal.

The agent decides itself which data it needs. It can call three tools:
product details, sales numbers and example tickets.

Usage:
    python analyze.py
    python analyze.py --classify-model claude-sonnet-5-5   # findings based on that model
"""
import argparse
import json
import time

import shop_data
from config import ANALYZE_MODEL, CLASSIFY_MODEL, cost_usd
from db import connect
from llm import client, parse_json, response_text

MAX_TURNS = 6
ACTIONS = ["produktseite", "produktmanagement", "supply_chain", "kein_handlungsbedarf"]

TOOLS = [
    {
        "name": "get_product_info",
        "description": "Returns the product description from the shop, including size chart "
                       "and material, as plain text.",
        "input_schema": {
            "type": "object",
            "properties": {"product": {"type": "string", "description": "Exact product title"}},
            "required": ["product"],
        },
    },
    {
        "name": "get_sales",
        "description": "Returns how many units of the product were sold.",
        "input_schema": {
            "type": "object",
            "properties": {"product": {"type": "string", "description": "Exact product title"}},
            "required": ["product"],
        },
    },
    {
        "name": "get_example_tickets",
        "description": "Returns up to 10 customer tickets for a product and topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product": {"type": "string", "description": "Exact product title"},
                "topic": {"type": "string", "description": "Ticket topic, e.g. Passform"},
            },
            "required": ["product", "topic"],
        },
    },
]

SYSTEM = """Du bist ein Analyse-Agent für einen Mode-Onlineshop. Du bekommst eine Auffälligkeit
aus den Kundenservice-Tickets und entscheidest, wie das Unternehmen die Ursache behebt.

Mögliche Maßnahmen (action):
- produktseite: Die Produktseite informiert unzureichend (z. B. Passform). Schlage einen kurzen
  Hinweis vor, der auf der Produktseite ergänzt wird.
- produktmanagement: Ein Qualitäts- oder Produktproblem. Formuliere eine Meldung an das Produktteam.
- supply_chain: Ein Liefer- oder Logistikproblem. Formuliere eine Meldung an Supply Chain.
- kein_handlungsbedarf: Die Tickets zeigen kein echtes Problem.

Regeln:
- Nutze die Werkzeuge, bevor du entscheidest. Lies mindestens die Beispiel-Tickets und die Produktdaten.
- Nenne nur Fakten aus Werkzeugen und Tickets. Kennzeichne Vermutungen als Vermutungen.
- Ändere die Produktseite nicht bei Qualitäts- oder Lieferproblemen.
- Produktseiten-Hinweise schreibst du im Markenton (siehe unten), höchstens zwei Sätze.
- Meldungen an Teams sind sachlich, enthalten die Zahlen und zwei kurze Ticket-Zitate.

Markenton:
{brand_voice}

Antworte am Ende ausschließlich mit einem JSON-Objekt:
{{"action": "<eine der Maßnahmen>",
  "cause": "<vermutete Ursache in einem Satz>",
  "reasoning": "<Begründung mit Zahlen, höchstens drei Sätze>",
  "proposed_text": "<Hinweis für die Produktseite oder leer>",
  "team_message": "<Meldung an das Team oder leer>"}}"""


def run_tool(name: str, args: dict, con, classify_model: str) -> dict:
    """Execute one tool call from the agent and return a JSON-friendly result."""
    if name == "get_product_info":
        product = shop_data.get_product(args["product"])
        if not product:
            return {"error": f"Unknown product: {args['product']}"}
        return {"title": product["title"], "description": shop_data.html_to_text(product["description_html"])}
    if name == "get_sales":
        row = con.execute("SELECT units_sold FROM sales WHERE product = ?", (args["product"],)).fetchone()
        return {"product": args["product"], "units_sold": row["units_sold"] if row else None}
    if name == "get_example_tickets":
        rows = con.execute(
            """SELECT t.date, t.text FROM tickets t
               JOIN classified c ON c.ticket_id = t.ticket_id
               WHERE c.product = ? AND c.topic = ? AND c.model = ?
               LIMIT 10""",
            (args["product"], args["topic"], classify_model),
        ).fetchall()
        return {"tickets": [{"date": r["date"], "text": r["text"]} for r in rows]}
    return {"error": f"Unknown tool: {name}"}


def analyze_finding(finding, con, classify_model: str, brand_voice: str) -> tuple[dict, int, int, float]:
    """Run the agent loop for one finding."""
    messages = [{
        "role": "user",
        "content": (f"Auffälligkeit: Produkt '{finding['product']}', Thema '{finding['topic']}'. "
                    f"{finding['tickets']} Tickets bei {finding['units_sold']} verkauften Stück "
                    f"({finding['tickets_per_100']} Tickets pro 100 verkaufte Stück). "
                    "Analysiere die Ursache und schlage eine Maßnahme vor."),
    }]
    input_tokens = output_tokens = 0
    start = time.perf_counter()

    for _ in range(MAX_TURNS):
        response = client.messages.create(
            model=ANALYZE_MODEL,
            max_tokens=4000,
            system=SYSTEM.format(brand_voice=brand_voice),
            tools=TOOLS,
            messages=messages,
        )
        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens

        if response.stop_reason != "tool_use":
            proposal = parse_json(response_text(response))
            if proposal.get("action") not in ACTIONS:
                proposal["action"] = "kein_handlungsbedarf"
            return proposal, input_tokens, output_tokens, time.perf_counter() - start

        # The model wants to use tools: run them and send back the results
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"    tool: {block.name}({json.dumps(block.input, ensure_ascii=False)})")
                output = run_tool(block.name, block.input, con, classify_model)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(output, ensure_ascii=False),
                })
        messages.append({"role": "user", "content": results})

    raise RuntimeError("The agent did not finish within the turn limit.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--classify-model", default=CLASSIFY_MODEL,
                        help="use the findings that were based on this classification model")
    args = parser.parse_args()

    con = connect()
    with open("markenton.md", encoding="utf-8") as f:
        brand_voice = f.read()

    findings = con.execute(
        """SELECT * FROM findings f
           WHERE f.model = ?
             AND NOT EXISTS (SELECT 1 FROM proposals p WHERE p.finding_id = f.id)""",
        (args.classify_model,),
    ).fetchall()
    print(f"{len(findings)} findings to analyse with {ANALYZE_MODEL}.")

    total_cost = 0.0
    for finding in findings:
        print(f"- {finding['product']} | {finding['topic']}")
        try:
            proposal, tokens_in, tokens_out, seconds = analyze_finding(finding, con, args.classify_model, brand_voice)
        except Exception as error:
            print(f"    FAILED: {error}")
            continue
        con.execute(
            """INSERT INTO proposals (finding_id, product, topic, action, cause, reasoning,
                                      proposed_text, team_message, model, input_tokens, output_tokens, seconds)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (finding["id"], finding["product"], finding["topic"], proposal["action"],
             proposal.get("cause", ""), proposal.get("reasoning", ""),
             proposal.get("proposed_text", ""), proposal.get("team_message", ""),
             ANALYZE_MODEL, tokens_in, tokens_out, seconds),
        )
        con.commit()
        total_cost += cost_usd(ANALYZE_MODEL, tokens_in, tokens_out)
        print(f"    -> {proposal['action']}: {proposal.get('cause', '')}")

    print(f"Done. Cost of this run: about ${total_cost:.4f}")


if __name__ == "__main__":
    main()
