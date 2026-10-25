"""Step 4: approval page for the business teams.

Start it with:
    streamlit run app.py
"""
import html
import os
from datetime import date

import streamlit as st

import shop_data
from db import connect

st.set_page_config(page_title="Service Insights", layout="wide")
st.title("Service Insights")
st.caption("Vorschläge aus den Kundenservice-Tickets. Nichts wird ohne Freigabe geändert.")

ACTION_LABELS = {
    "produktseite": "Produktseite anpassen",
    "produktmanagement": "Meldung an Produktmanagement",
    "supply_chain": "Meldung an Supply Chain",
    "kein_handlungsbedarf": "Kein Handlungsbedarf",
}
STATUS_LABELS = {"open": "Offen", "approved": "Freigegeben", "rejected": "Abgelehnt"}

con = connect()
status = st.radio("Anzeigen", list(STATUS_LABELS), format_func=STATUS_LABELS.get, horizontal=True)
proposals = con.execute("SELECT * FROM proposals WHERE status = ? ORDER BY id", (status,)).fetchall()

if not proposals:
    st.info("Keine Vorschläge in dieser Ansicht.")


def apply_proposal(p, text: str) -> str:
    """Carry out an approved proposal and return a short confirmation."""
    if p["action"] == "produktseite":
        product = shop_data.get_product(p["product"])
        if not product:
            raise RuntimeError(f"Produkt nicht gefunden: {p['product']}")
        hint = f"<p><strong>Passform-Hinweis:</strong> {html.escape(text)}</p>"
        shop_data.update_description(product, product["description_html"] + hint)
        return "Hinweis auf der Produktseite ergänzt."
    # Team messages are saved as Markdown reports (later: Slack or e-mail)
    os.makedirs("reports", exist_ok=True)
    path = f"reports/{date.today()}_{p['action']}_{p['id']}.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {ACTION_LABELS[p['action']]}: {p['product']} ({p['topic']})\n\n{text}\n")
    return f"Meldung gespeichert: {path}"


for p in proposals:
    finding = con.execute("SELECT * FROM findings WHERE id = ?", (p["finding_id"],)).fetchone()
    with st.container(border=True):
        st.subheader(f"{p['product']} · {p['topic']}")
        st.markdown(f"**Vorschlag:** {ACTION_LABELS.get(p['action'], p['action'])}")
        if finding:
            c1, c2, c3 = st.columns(3)
            c1.metric("Tickets", finding["tickets"])
            c2.metric("Verkauft", finding["units_sold"])
            c3.metric("Tickets pro 100 Verkäufe", finding["tickets_per_100"])
        st.markdown(f"**Ursache:** {p['cause']}")
        st.markdown(f"**Begründung:** {p['reasoning']}")

        examples = con.execute(
            """SELECT t.text FROM tickets t JOIN classified c ON c.ticket_id = t.ticket_id
               WHERE c.product = ? AND c.topic = ? AND c.model = ? LIMIT 3""",
            (p["product"], p["topic"], finding["model"] if finding else ""),
        ).fetchall()
        with st.expander("Beispiel-Tickets"):
            for e in examples:
                st.markdown(f"> {e['text']}")

        if p["action"] == "kein_handlungsbedarf":
            text = ""
        elif p["action"] == "produktseite":
            text = st.text_area("Hinweis für die Produktseite", p["proposed_text"], key=f"text{p['id']}")
        else:
            text = st.text_area("Meldung an das Team", p["team_message"], key=f"text{p['id']}", height=180)

        if status == "open":
            b1, b2 = st.columns(2)
            if b1.button("Freigeben", key=f"ok{p['id']}", type="primary"):
                try:
                    message = apply_proposal(p, text) if text else "Nichts zu tun."
                    con.execute("UPDATE proposals SET status = 'approved' WHERE id = ?", (p["id"],))
                    con.commit()
                    st.success(message)
                    st.rerun()
                except Exception as error:
                    st.error(f"Fehler: {error}")
            if b2.button("Ablehnen", key=f"no{p['id']}"):
                con.execute("UPDATE proposals SET status = 'rejected' WHERE id = ?", (p["id"],))
                con.commit()
                st.rerun()
