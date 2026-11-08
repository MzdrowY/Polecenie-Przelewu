import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from app.database import Database
from app.models import Payment
from test_core import valid_test_account


class RecipientTests(unittest.TestCase):
    def test_migrates_latest_details_once_and_keeps_recipient_after_history_deletion(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.sqlite3"
            account = valid_test_account()
            old = Payment(recipient="Jan Kowalski", recipient_account=account,
                          recipient_address="Stary adres")
            new = Payment(recipient="JAN KOWALSKI", recipient_account="PL " + account,
                          recipient_address="Nowy adres")
            conn = sqlite3.connect(path)
            with conn:
                conn.execute("""CREATE TABLE payments (
                    id INTEGER PRIMARY KEY, created_at TEXT, updated_at TEXT,
                    recipient TEXT, recipient_account TEXT, amount TEXT, data_json TEXT
                )""")
                for date, data in (("2026-10-01", old), ("2026-10-02", new)):
                    conn.execute("""INSERT INTO payments
                        (created_at,updated_at,recipient,recipient_account,amount,data_json)
                        VALUES (?,?,?,?,?,?)""",
                        (date, date, data.recipient, data.recipient_account, "1",
                         json.dumps(data.as_dict(), ensure_ascii=False)))
            conn.close()
            db = Database(path)
            self.assertEqual(db.recipients("kowalski"), [
                {"name": "JAN KOWALSKI", "address": "Nowy adres", "account": account},
            ])
            self.assertEqual(len(db.all()), 2)
            db.delete(2)
            db.close()
            db = Database(path)
            self.assertEqual(db.recipients("PL " + account)[0]["address"], "Nowy adres")
            self.assertFalse(db.remember_recipient(Payment(recipient="Bez rachunku")))
            db.close()
