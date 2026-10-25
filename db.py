"""SQLite database: one file (insights.db) that stores every step's results."""
import sqlite3

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    date      TEXT,
    channel   TEXT,
    text      TEXT
);

CREATE TABLE IF NOT EXISTS classified (
    ticket_id     TEXT,
    model         TEXT,
    product       TEXT,
    topic         TEXT,
    detail        TEXT,
    sentiment     TEXT,
    input_tokens  INTEGER,
    output_tokens INTEGER,
    seconds       REAL,
    PRIMARY KEY (ticket_id, model)
);

CREATE TABLE IF NOT EXISTS sales (
    product    TEXT PRIMARY KEY,
    units_sold INTEGER
);

CREATE TABLE IF NOT EXISTS findings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    model           TEXT,
    product         TEXT,
    topic           TEXT,
    tickets         INTEGER,
    units_sold      INTEGER,
    tickets_per_100 REAL,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS proposals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id    INTEGER,
    product       TEXT,
    topic         TEXT,
    action        TEXT,
    cause         TEXT,
    reasoning     TEXT,
    proposed_text TEXT,
    team_message  TEXT,
    status        TEXT DEFAULT 'open',
    model         TEXT,
    input_tokens  INTEGER,
    output_tokens INTEGER,
    seconds       REAL,
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def connect() -> sqlite3.Connection:
    """Open the database and create the tables if they do not exist yet."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con
