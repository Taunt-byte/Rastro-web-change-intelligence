import sqlite3
from datetime import datetime, timezone

DB_NAME = "rastro.db"

def connect():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL,
                title TEXT,
                content TEXT NOT NULL,
                checked_at TEXT NOT NULL,
                changed INTEGER NOT NULL DEFAULT 0,
                added_lines INTEGER NOT NULL DEFAULT 0,
                removed_lines INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(site_id) REFERENCES sites(id) ON DELETE CASCADE
            )
        """)

def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def add_site(name, url):
    with connect() as conn:
        conn.execute("INSERT INTO sites(name, url, created_at) VALUES (?, ?, ?)", (name, url, now()))

def delete_site(site_id):
    with connect() as conn:
        conn.execute("DELETE FROM snapshots WHERE site_id = ?", (site_id,))
        conn.execute("DELETE FROM sites WHERE id = ?", (site_id,))

def get_sites():
    with connect() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM sites ORDER BY created_at DESC")]

def get_site(site_id):
    with connect() as conn:
        row = conn.execute("SELECT * FROM sites WHERE id = ?", (site_id,)).fetchone()
        return dict(row) if row else None

def save_snapshot(site_id, title, content, changed, added, removed):
    with connect() as conn:
        conn.execute("""
            INSERT INTO snapshots(site_id, title, content, checked_at, changed, added_lines, removed_lines)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (site_id, title, content, now(), int(changed), added, removed))

def get_latest_snapshot(site_id):
    with connect() as conn:
        row = conn.execute("""
            SELECT * FROM snapshots WHERE site_id = ? ORDER BY id DESC LIMIT 1
        """, (site_id,)).fetchone()
        return dict(row) if row else None

def get_snapshot_pair(site_id, snapshot_id):
    with connect() as conn:
        current = conn.execute("SELECT content FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
        previous = conn.execute("""
            SELECT content FROM snapshots WHERE site_id = ? AND id < ? ORDER BY id DESC LIMIT 1
        """, (site_id, snapshot_id)).fetchone()
        return (previous["content"] if previous else None,
                current["content"] if current else None)

def get_changes(limit=100):
    with connect() as conn:
        rows = conn.execute("""
            SELECT s.id AS snapshot_id, s.site_id, s.checked_at, s.added_lines, s.removed_lines,
                   w.name AS site_name, w.url
            FROM snapshots s JOIN sites w ON w.id = s.site_id
            WHERE s.changed = 1
            ORDER BY s.id DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(row) for row in rows]

def get_snapshots():
    with connect() as conn:
        rows = conn.execute("SELECT checked_at FROM snapshots ORDER BY id")
        return [dict(row) for row in rows]

def get_dashboard_stats():
    with connect() as conn:
        sites = conn.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
        checks = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
        changes = conn.execute("SELECT COUNT(*) FROM snapshots WHERE changed = 1").fetchone()[0]
        recent = conn.execute("""
            SELECT COUNT(*) FROM snapshots
            WHERE changed = 1 AND checked_at >= datetime('now', '-7 days')
        """).fetchone()[0]
        return {"sites": sites, "checks": checks, "changes": changes, "recent_changes": recent}
