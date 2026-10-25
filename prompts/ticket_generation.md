# Prompt to generate test tickets

Paste this into a normal Claude chat (claude.ai). Run it four times, changing only the line
"PART". Copy each answer into `data/generated.csv` (the header line only once, at the top).

---

Du erzeugst realistische, aber komplett erfundene Kundenservice-Tickets für einen fiktiven
deutschen Online-Shop für Basics. Ich brauche sie als Testdaten für einen KI-Agenten.

PART: Teil 1 von 4 (Ticket-IDs T001 bis T050)

Produkte (exakte Namen):
- Leggings Classic
- Sport-BH Flow
- Boxershorts 3er-Pack
- Sneakersocken 6er-Pack
- Hoodie Oversize
- Basic T-Shirt

Erlaubte Themen: Passform, Qualität, Lieferung, Farbe/Material, Sonstiges

In diesem Teil sollen genau diese Muster vorkommen (über alle vier Teile verteilt):
- Leggings Classic | Passform: 4 Tickets, die Leggings fällt klein oder eng aus
- Sport-BH Flow | Qualität: 2 Tickets, Naht oder Träger löst sich nach dem Waschen
- Hoodie Oversize | Farbe/Material: 2 Tickets, Farbe grauer als auf dem Foto
- Sneakersocken 6er-Pack | Lieferung: 4 Tickets, Paket verspätet oder hängt fest

Die übrigen Tickets sind gemischter Alltag: Rücksendung, Adressänderung, Gutschein,
Lob, Verfügbarkeit, Rechnungen, allgemeine Größenfragen ohne Problem und so weiter.
Wichtig: Abgesehen von den Mustern und dem Thema Sonstiges darf jede Kombination
aus Produkt und Thema höchstens 1 Ticket in diesem Teil haben.

Gestaltung:
- Unterschiedliche Länge (ein Satz bis fünf Sätze), Tonfall und Formulierungen.
- Ein paar Tippfehler, Umgangssprache, zwei oder drei Tickets auf Englisch.
- Einige Tickets nennen das Produkt nur indirekt („meine neue Leggings“, „die Socken“).
- Zwei Tickets mit zwei Anliegen, eins zu einem Produkt, das wir nicht führen.
- Keine Namen, E-Mail-Adressen, Telefonnummern oder Adressen.
- Datum zwischen 2026-09-01 und 2026-10-15, Kanal: email, kontaktformular, chat oder instagram.

Gib ausschließlich CSV aus, ohne Erklärung, mit dieser Kopfzeile (nur im ersten Teil):
ticket_id,date,channel,text,product,topic

- text in doppelten Anführungszeichen, keine Zeilenumbrüche im Text.
- product: exakter Produktname oder unbekannt
- topic: eines der erlaubten Themen (das Hauptanliegen)

---

Counts for the other parts:

| Part | IDs | Leggings / Passform | Sport-BH / Qualität | Hoodie / Farbe | Socken / Lieferung |
|---|---|---|---|---|---|
| 2 | T051–T100 | 4 | 3 | 2 | 4 |
| 3 | T101–T150 | 3 | 2 | 2 | 3 |
| 4 | T151–T200 | 3 | 2 | 2 | 3 |

Totals: Leggings 14, Sport-BH 9, Hoodie 8, Socken 14 across 200 tickets.
