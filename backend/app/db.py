import sqlite3, json
from .config import DB_PATH
SCHEMA = """
CREATE TABLE IF NOT EXISTS deals(adsh TEXT PRIMARY KEY, form TEXT, target TEXT, acquirer TEXT, ann_date TEXT,
  deal_value_musd REAL, price_per_share REAL, premium REAL, premium_ref TEXT, multiple REAL, multiple_type TEXT,
  sector TEXT, sic TEXT, confidence TEXT, flags TEXT, url TEXT);
CREATE TABLE IF NOT EXISTS unparsed(adsh TEXT PRIMARY KEY, form TEXT, target TEXT, sector TEXT, url TEXT,
  reasons TEXT, partial TEXT, snippets TEXT);
CREATE TABLE IF NOT EXISTS saved_analyses(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT DEFAULT CURRENT_TIMESTAMP, title TEXT, payload TEXT);
CREATE TABLE IF NOT EXISTS watchlist(id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT UNIQUE, note TEXT);
CREATE TABLE IF NOT EXISTS latency_log(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT DEFAULT CURRENT_TIMESTAMP,
  question TEXT, embed_ms REAL, retrieve_ms REAL, llm_ms REAL, crosscheck_ms REAL, total_ms REAL);
"""
def conn():
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row; c.executescript(SCHEMA); return c
def rows(sql, args=()):
    with conn() as c: return [dict(r) for r in c.execute(sql, args).fetchall()]
def jdump(x): return json.dumps(x, default=str)
