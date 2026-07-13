"""Database layer for the coffee tracker.

Five tables: grinders, brewing_methods, brewers, beans, brew_entries.
Everything except brew_entries supplies reusable dropdown options.
Storage fields live directly on `beans` for this first version.
"""
import os
import sqlite3
from datetime import datetime

from flask import g

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "coffee.db")

# Columns that may be written via forms / the JSON API, per table. `id`,
# `created_at`, and `active` are managed by the DB layer, not the forms.
EDITABLE = {
    "grinders": ["name", "brand", "model", "grinder_type", "burr_type", "notes"],
    "brewing_methods": ["name", "description"],
    "brewers": ["name", "brand", "model", "method_id", "material", "size", "notes"],
    "beans": [
        "display_name", "roaster", "coffee_name", "origin_country", "region",
        "producer", "variety", "process", "roast_level", "roast_date",
        "purchase_date", "bag_weight_grams", "storage_method",
        "storage_location", "opened_date", "notes",
    ],
}

# Column used as the human label in dropdowns.
LABEL_COLUMN = {
    "grinders": "name",
    "brewing_methods": "name",
    "brewers": "name",
    "beans": "display_name",
}

DEFAULT_METHODS = [
    "Pour-over", "Espresso", "French press", "AeroPress",
    "Cold brew", "Moka pot", "Automatic drip",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS grinders (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    brand        TEXT,
    model        TEXT,
    grinder_type TEXT,
    burr_type    TEXT,
    notes        TEXT,
    active       INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS brewing_methods (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT,
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS brewers (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    brand      TEXT,
    model      TEXT,
    method_id  INTEGER REFERENCES brewing_methods(id),
    material   TEXT,
    size       TEXT,
    notes      TEXT,
    active     INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS beans (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name     TEXT NOT NULL,
    roaster          TEXT,
    coffee_name      TEXT,
    origin_country   TEXT,
    region           TEXT,
    producer         TEXT,
    variety          TEXT,
    process          TEXT,
    roast_level      TEXT,
    roast_date       TEXT,
    purchase_date    TEXT,
    bag_weight_grams REAL,
    storage_method   TEXT,
    storage_location TEXT,
    opened_date      TEXT,
    notes            TEXT,
    active           INTEGER NOT NULL DEFAULT 1,
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS brew_entries (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    brewed_at         TEXT NOT NULL,
    bean_id           INTEGER REFERENCES beans(id),
    grinder_id        INTEGER REFERENCES grinders(id),
    grind_setting     TEXT,
    grind_category    TEXT,
    method_id         INTEGER REFERENCES brewing_methods(id),
    brewer_id         INTEGER REFERENCES brewers(id),
    water_temperature REAL,
    temperature_unit  TEXT,
    coffee_grams      REAL,
    water_grams       REAL,
    brew_time_seconds INTEGER,
    yield_grams       REAL,
    rating            INTEGER,
    notes             TEXT,
    created_at        TEXT NOT NULL
);
"""


def get_db():
    if "db" not in g:
        os.makedirs(DATA_DIR, exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()
    seed_methods()


def seed_methods():
    db = get_db()
    count = db.execute("SELECT COUNT(*) AS n FROM brewing_methods").fetchone()["n"]
    if count:
        return
    now = _now()
    db.executemany(
        "INSERT INTO brewing_methods (name, active, created_at) VALUES (?, 1, ?)",
        [(name, now) for name in DEFAULT_METHODS],
    )
    db.commit()


def _now():
    return datetime.now().isoformat(timespec="seconds")


# --- generic CRUD -----------------------------------------------------------

def fetch_all(table, active_only=False, order_by=None):
    order = order_by or (LABEL_COLUMN.get(table) or "id")
    where = "WHERE active = 1" if active_only else ""
    rows = get_db().execute(
        f"SELECT * FROM {table} {where} ORDER BY {order} COLLATE NOCASE"
    ).fetchall()
    return [dict(r) for r in rows]


def fetch_one(table, row_id):
    row = get_db().execute(
        f"SELECT * FROM {table} WHERE id = ?", (row_id,)
    ).fetchone()
    return dict(row) if row else None


def insert(table, data):
    """Insert a row using only whitelisted editable columns; returns new id."""
    cols = [c for c in EDITABLE[table] if c in data]
    values = [data[c] for c in cols]
    cols += ["active", "created_at"]
    values += [1, _now()]
    placeholders = ", ".join("?" for _ in cols)
    db = get_db()
    cur = db.execute(
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})",
        values,
    )
    db.commit()
    return cur.lastrowid


def update(table, row_id, data):
    cols = [c for c in EDITABLE[table] if c in data]
    if not cols:
        return
    assignments = ", ".join(f"{c} = ?" for c in cols)
    values = [data[c] for c in cols] + [row_id]
    db = get_db()
    db.execute(f"UPDATE {table} SET {assignments} WHERE id = ?", values)
    db.commit()


def set_active(table, row_id, active):
    db = get_db()
    db.execute(
        f"UPDATE {table} SET active = ? WHERE id = ?", (1 if active else 0, row_id)
    )
    db.commit()


# --- brew entries -----------------------------------------------------------

BREW_COLUMNS = [
    "brewed_at", "bean_id", "grinder_id", "grind_setting", "grind_category",
    "method_id", "brewer_id", "water_temperature", "temperature_unit",
    "coffee_grams", "water_grams", "brew_time_seconds", "yield_grams",
    "rating", "notes",
]


def insert_brew(data):
    cols = [c for c in BREW_COLUMNS if c in data]
    values = [data[c] for c in cols]
    cols.append("created_at")
    values.append(_now())
    placeholders = ", ".join("?" for _ in cols)
    db = get_db()
    cur = db.execute(
        f"INSERT INTO brew_entries ({', '.join(cols)}) VALUES ({placeholders})",
        values,
    )
    db.commit()
    return cur.lastrowid


def fetch_brews():
    """Brew entries joined with the reusable records' display labels."""
    rows = get_db().execute(
        """
        SELECT e.*,
               b.display_name AS bean_name,
               g.name         AS grinder_name,
               m.name         AS method_name,
               w.name         AS brewer_name
        FROM brew_entries e
        LEFT JOIN beans           b ON b.id = e.bean_id
        LEFT JOIN grinders        g ON g.id = e.grinder_id
        LEFT JOIN brewing_methods m ON m.id = e.method_id
        LEFT JOIN brewers         w ON w.id = e.brewer_id
        ORDER BY e.brewed_at DESC, e.id DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]


def delete_brew(row_id):
    db = get_db()
    db.execute("DELETE FROM brew_entries WHERE id = ?", (row_id,))
    db.commit()
