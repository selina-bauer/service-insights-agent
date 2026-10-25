# Service Insights Agent

> Turns repetitive customer service tickets into concrete product improvements.

**Status:** work in progress. Replace every `TODO` before you share this repository.

## What it does

Customer service teams answer the same questions again and again, while the root cause stays in place.
This agent reads service tickets, finds recurring problems per product and proposes a fix in the right place:

- a fit note on the product page in Shopify (for example "runs small, order one size up"),
- a message to product management (quality issues),
- a message to supply chain (delivery issues).

A person approves every proposal before anything changes.

TODO: screenshot of the approval page

## How it works

```
Tickets ──> 1 Classify ──> 2 Cluster (SQL) ──> 3 Analyse (agent + Shopify data) ──> 4 Human approval
            Claude Haiku     tickets per 100       Claude Sonnet with tools             Streamlit app
                             units sold
```

| Step | File | What happens |
|---|---|---|
| 1 | `classify.py` | Claude Haiku assigns product, topic, detail and sentiment to each ticket |
| 2 | `cluster.py` | SQL counts tickets per product and topic, relative to units sold, and flags outliers |
| 3 | `analyze.py` | An agent with three tools (product info, sales, example tickets) proposes an action |
| 4 | `app.py` | Approval page; approved fit notes are written to Shopify via the Admin API |
| 5 | `evaluate.py` | Measures accuracy, detected patterns, false alarms, cost and speed |

Design choices:

- **Small model for volume, large model for judgement.** TODO: explain with your numbers.
- **Relative, not absolute counts.** A bestseller gets more tickets anyway.
- **Human in the loop.** Nothing is published without approval.
- **No personal data.** Tickets are passed to the model without names or e-mail addresses.
- **Complements existing helpdesk tools** instead of replacing them: tickets are the input.

## Evaluation

Test data: TODO number of synthetic tickets with TODO hidden patterns, TODO hand-labelled tickets.

| Version | Classification correct | Patterns found | False alarms | Cost per run | Time per ticket |
|---|---|---|---|---|---|
| TODO | | | | | |

What I changed between versions: TODO

## Limitations

TODO: be honest, for example ambiguous tickets, small sample sizes, synthetic data.

## Setup

Runs in GitHub Codespaces, nothing to install locally.

1. Add Codespaces secrets: `ANTHROPIC_API_KEY`, and for Shopify `SHOPIFY_SHOP`, `SHOPIFY_CLIENT_ID`, `SHOPIFY_CLIENT_SECRET`.
2. `pip install -r requirements.txt`
3. Try it with sample data (no Shopify needed):

```bash
python classify.py --tickets data/sample/tickets.csv
python cluster.py
python analyze.py
streamlit run app.py
python evaluate.py --handlabels data/sample/handlabels.csv --patterns data/sample/expected_patterns.csv
```

4. To use your Shopify dev store, set the environment variable `DATA_SOURCE=shopify`.

## Built with

Python, Claude API (Haiku 5.5, Sonnet 5.5), Shopify Admin GraphQL API, SQLite, Streamlit, GitHub Codespaces.
Built with the help of AI coding tools (Claude). I reviewed, tested and evaluated every part myself.
