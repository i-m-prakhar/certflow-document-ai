"""Workspace-scoped SQLite indexes and audit history; one-host demonstration."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

class Store:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.conn() as con:
            con.executescript("""
              CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT NOT NULL, workspace TEXT NOT NULL, filename TEXT NOT NULL,
                sha256 TEXT NOT NULL, fields TEXT NOT NULL, validation TEXT NOT NULL,
                created_at TEXT NOT NULL, PRIMARY KEY (workspace, document_id)
              );
              CREATE TABLE IF NOT EXISTS passages (
                workspace TEXT NOT NULL, document_id TEXT NOT NULL, page INTEGER NOT NULL,
                text TEXT NOT NULL, PRIMARY KEY(workspace, document_id, page)
              );
              CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT, workspace TEXT NOT NULL,
                document_id TEXT, action TEXT NOT NULL, created_at TEXT NOT NULL
              );
            """)

    def conn(self):
        con = sqlite3.connect(self.db_path, timeout=15)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        return con

    def audit(self, workspace: str, document_id: str | None, action: str):
        with self.conn() as con:
            con.execute("INSERT INTO audit (workspace, document_id, action, created_at) VALUES (?, ?, ?, ?)",
                        (workspace, document_id, action, datetime.now(timezone.utc).isoformat()))

    def put(self, workspace: str, doc_id: str, filename: str, sha: str, fields: dict, validation: dict, pages: list[str]):
        now = datetime.now(timezone.utc).isoformat()
        with self.conn() as con:
            exists = con.execute("SELECT 1 FROM documents WHERE workspace=? AND document_id=?", (workspace, doc_id)).fetchone()
            if exists: return False
            con.execute("""INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (doc_id, workspace, filename, sha, json.dumps(fields), json.dumps(validation), now))
            con.executemany("INSERT INTO passages VALUES (?, ?, ?, ?)",
                            [(workspace, doc_id, i + 1, text) for i, text in enumerate(pages) if text.strip()])
            con.execute("INSERT INTO audit (workspace, document_id, action, created_at) VALUES (?, ?, ?, ?)",
                        (workspace, doc_id, "INGESTED", now))
        return True

    def get(self, workspace: str, doc_id: str):
        with self.conn() as con:
            row = con.execute("SELECT * FROM documents WHERE workspace=? AND document_id=?", (workspace, doc_id)).fetchone()
        return ({**dict(row), "fields": json.loads(row["fields"]),
                 "validation": json.loads(row["validation"])} if row else None)

    def passages(self, workspace: str):
        with self.conn() as con:
            rows = con.execute("SELECT document_id, page, text FROM passages WHERE workspace=? ORDER BY document_id, page", (workspace,)).fetchall()
        return [dict(row) for row in rows]

    def documents(self, workspace: str):
        with self.conn() as con:
            rows = con.execute("SELECT document_id FROM documents WHERE workspace=? ORDER BY document_id", (workspace,)).fetchall()
        return [r["document_id"] for r in rows]

    def events(self, workspace: str, doc_id: str | None = None, limit: int = 100):
        with self.conn() as con:
            if doc_id:
                rows = con.execute("SELECT * FROM audit WHERE workspace=? AND document_id=? ORDER BY id DESC LIMIT ?", (workspace,doc_id,limit)).fetchall()
            else:
                rows = con.execute("SELECT * FROM audit WHERE workspace=? ORDER BY id DESC LIMIT ?", (workspace,limit)).fetchall()
        return [dict(r) for r in rows]
