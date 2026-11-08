"""Trwała baza lokalna SQLite, bez usług sieciowych."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
from .models import Payment, account_digits, valid_nrb


SCHEMA_VERSION = 1

class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA busy_timeout = 3000")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            recipient TEXT NOT NULL,
            recipient_account TEXT NOT NULL,
            amount TEXT NOT NULL,
            data_json TEXT NOT NULL
        )""")
        self.conn.commit()
        self._initialize_recipients()
        self.run_migrations()

    def run_migrations(self):
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if version < SCHEMA_VERSION:
            # v1: schemat bazowy; przyszłe migracje ALTER TABLE tutaj.
            self.conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            self.conn.commit()

    def _initialize_recipients(self):
        with self.conn:
            self.conn.execute("BEGIN IMMEDIATE")
            exists = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'recipients'"
            ).fetchone()
            if exists:
                return
            self.conn.execute("""CREATE TABLE recipients (
                name_key TEXT NOT NULL,
                account TEXT NOT NULL,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                PRIMARY KEY (name_key, account)
            )""")
            rows = self.conn.execute(
                "SELECT data_json FROM payments ORDER BY updated_at, id"
            ).fetchall()
            for row in rows:
                try:
                    fields = json.loads(row["data_json"])
                    if not isinstance(fields, dict):
                        continue
                    data = Payment(
                        recipient=fields.get("recipient", ""),
                        recipient_address=fields.get("recipient_address", ""),
                        recipient_account=fields.get("recipient_account", ""),
                    )
                except json.JSONDecodeError:
                    continue
                if all(isinstance(value, str) for value in (
                    data.recipient, data.recipient_address, data.recipient_account,
                )):
                    self._upsert_recipient(data)

    def _upsert_recipient(self, data: Payment) -> bool:
        name = data.recipient.strip()
        if not name or not valid_nrb(data.recipient_account):
            return False
        address = data.recipient_address.strip()
        self.conn.execute("""INSERT INTO recipients (name_key, account, name, address)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name_key, account) DO UPDATE SET
                name = excluded.name,
                address = COALESCE(NULLIF(excluded.address, ''), recipients.address)""",
            (" ".join(name.casefold().split()), account_digits(data.recipient_account), name, address))
        return True

    def remember_recipient(self, data: Payment) -> bool:
        with self.conn:
            return self._upsert_recipient(data)

    def recipients(self, needle: str = "") -> list[dict]:
        query = needle.casefold().strip()
        digits_query = "".join(query.split()).removeprefix("pl").replace("-", "")
        rows = self.conn.execute("SELECT name, address, account FROM recipients").fetchall()
        matches = [
            dict(row) for row in rows
            if not query or query in row["name"].casefold()
            or query in row["address"].casefold()
            or (digits_query.isdecimal() and digits_query in row["account"])
        ]
        return sorted(matches, key=lambda row: (row["name"].casefold(), row["account"]))

    def save(self, data: Payment, payment_id: int | None = None) -> int:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        values = (now, data.recipient.strip(), data.recipient_account.strip(),
                  data.amount.strip(), json.dumps(data.as_dict(),ensure_ascii=False))
        with self.conn:
            self._upsert_recipient(data)
            if payment_id is None:
                cur = self.conn.execute("""INSERT INTO payments
                   (created_at,updated_at,recipient,recipient_account,amount,data_json)
                   VALUES (?,?,?,?,?,?)""",(now,*values))
                return int(cur.lastrowid)
            cur = self.conn.execute("""UPDATE payments SET
                updated_at=?,recipient=?,recipient_account=?,amount=?,data_json=?
                WHERE id=?""",(*values,payment_id))
            if cur.rowcount != 1:
                raise KeyError(f"Nie istnieje zapis nr {payment_id}")
            return payment_id

    def all(self, needle: str = "") -> list[dict]:
        rows = self.conn.execute("SELECT * FROM payments ORDER BY updated_at DESC,id DESC").fetchall()
        result = []
        q = needle.casefold().strip()
        for row in rows:
            d = dict(row)
            if not q or any(q in str(x).casefold() for x in [d["data_json"],d["id"],d["updated_at"]]):
                result.append(d)
        return result

    def get(self, payment_id: int) -> Payment:
        row = self.conn.execute("SELECT data_json FROM payments WHERE id=?",(payment_id,)).fetchone()
        if not row:
            raise KeyError(payment_id)
        return Payment(**json.loads(row[0]))

    def delete(self, payment_id: int):
        with self.conn:
            self.conn.execute("DELETE FROM payments WHERE id=?",(payment_id,))

    def export_backup(self, path: str | Path) -> None:
        path = Path(path)
        data = {
            "schema_version": SCHEMA_VERSION,
            "payments": [dict(r) for r in self.conn.execute("SELECT * FROM payments").fetchall()],
            "recipients": [dict(r) for r in self.conn.execute("SELECT * FROM recipients").fetchall()],
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def import_backup(self, path: str | Path) -> None:
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        with self.conn:
            self.conn.execute("DELETE FROM payments")
            self.conn.execute("DELETE FROM recipients")
            for row in data.get("payments", []):
                self.conn.execute(
                    """INSERT INTO payments (id, created_at, updated_at, recipient, recipient_account, amount, data_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (row["id"], row["created_at"], row["updated_at"], row["recipient"],
                     row["recipient_account"], row["amount"], row["data_json"]),
                )
            for row in data.get("recipients", []):
                self.conn.execute(
                    """INSERT INTO recipients (name_key, account, name, address) VALUES (?, ?, ?, ?)""",
                    (row["name_key"], row["account"], row["name"], row["address"]),
                )
        self.run_migrations()

    def close(self):
        self.conn.close()
