"""Testy v0.12: kalibracja, migracje, backup."""
from contextlib import closing
import json
import tempfile
import unittest
import sqlite3
from pathlib import Path
import pymupdf

from app.database import Database, SCHEMA_VERSION
from app.models import Payment
from app.pdfgen import generate_pdf, preview_png, MM_PT
from test_core import valid_test_account


class V012Tests(unittest.TestCase):
    def test_calibration_offset_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Payment()
            out = generate_pdf(data, Path(tmp) / "calib.pdf", strict=False, offset_x_mm=1.5, offset_y_mm=-2.0)
            self.assertTrue(out.is_file())
            png = preview_png(data, offset_x_mm=1.5, offset_y_mm=-2.0, strict=False)
            self.assertTrue(len(png) > 0)

    def test_user_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "t.sqlite3")
            v = db.conn.execute("PRAGMA user_version").fetchone()[0]
            self.assertEqual(v, SCHEMA_VERSION)
            db.close()

    def test_backup_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "t.sqlite3")
            data = Payment(recipient="Jan Testowy")
            db.save(data)
            backup = Path(tmp) / "backup.json"
            db.export_backup(backup)
            self.assertTrue(backup.is_file())
            payload = json.loads(backup.read_text())
            self.assertIn("payments", payload)
            db2 = Database(Path(tmp) / "t2.sqlite3")
            db2.import_backup(backup)
            rows = db2.all()
            self.assertEqual(len(rows), 1)
            db.close()
            db2.close()

    def test_sender_backup_roundtrip_and_legacy_import(self):
        with tempfile.TemporaryDirectory() as tmp, \
                closing(Database(Path(tmp) / "history.sqlite3")) as db, \
                closing(Database(Path(tmp) / "restored.sqlite3")) as db2:
            root = Path(tmp)
            db.remember_sender(Payment(payer="Jan Testowy"))
            db.remember_sender(Payment(payer="Firma Testowa", payer_address="ul. Próbna 1",
                                      payment_type="P", payer_account=valid_test_account()))
            backup = root / "backup.json"
            db.export_backup(backup)
            db2.remember_sender(Payment(payer="Dotychczasowy nadawca"))
            db2.import_backup(backup)
            self.assertEqual(db2.senders(), db.senders())

            payload = json.loads(backup.read_text(encoding="utf-8"))
            payload["senders"][0]["account"] = "123"
            backup.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                db2.import_backup(backup)
            self.assertEqual(db2.senders(), db.senders())

            payload["schema_version"] = 1
            del payload["senders"]
            backup.write_text(json.dumps(payload), encoding="utf-8")
            db2.import_backup(backup)
            self.assertEqual(db2.senders(), db.senders())

    def test_calibration_moves_text_and_lines_once(self):
        data = Payment(recipient="ODBIORCA Z BARDZO DLUGA NAZWA TESTOWA", recipient_account=valid_test_account(),
                       amount="500,00", payer="TESTOWY", title="TYTUL TESTOWY")
        with tempfile.TemporaryDirectory() as tmp:
            paths = [generate_pdf(data, Path(tmp) / f'{i}.pdf', offset_x_mm=x, offset_y_mm=y)
                     for i, (x, y) in enumerate(((0, 0), (1.5, -2.0)))]
            with pymupdf.open(paths[0]) as before, pymupdf.open(paths[1]) as after:
                pages = (before[0], after[0])
                texts = [[ch['bbox'] for b in p.get_text('rawdict')['blocks'] if 'lines' in b
                          for line in b['lines'] for span in line['spans'] for ch in span['chars']]
                         for p in pages]
                self.assertGreater(len(texts[0]), 20)
                self.assertEqual(len(texts[0]), len(texts[1]))
                for a, b in zip(*texts):
                    self.assertAlmostEqual(b[0] - a[0], 1.5 * MM_PT, delta=0.03)
                    self.assertAlmostEqual(b[1] - a[1], -2 * MM_PT, delta=0.03)
                lines = [[item for drawing in p.get_drawings()
                          if drawing['color'] and 0.01 < max(drawing['color']) < 0.2
                          for item in drawing['items'] if item[0] == 'l'] for p in pages]
                self.assertGreaterEqual(len(lines[0]), 6)
                self.assertEqual(len(lines[0]), len(lines[1]))
                for a, b in zip(*lines):
                    for p1, p2 in zip(a[1:], b[1:]):
                        self.assertAlmostEqual(p2.x - p1.x, 1.5 * MM_PT, delta=0.03)
                        self.assertAlmostEqual(p2.y - p1.y, -2 * MM_PT, delta=0.03)

    def test_invalid_backup_preserves_data_and_valid_import_saves_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = Database(root / 'history.sqlite3')
            ident = db.save(Payment(recipient='Oryginał'))
            path = root / 'incoming.json'
            for payload in ({}, {'schema_version': 1, 'payments': [], 'recipients': 'bad'},
                            {'schema_version': 99, 'payments': [], 'recipients': []},
                            {'schema_version': 1, 'payments': [{'id': 1}], 'recipients': []}):
                path.write_text(json.dumps(payload), encoding='utf-8')
                with self.assertRaises(ValueError):
                    db.import_backup(path)
                self.assertEqual(db.get(ident).recipient, 'Oryginał')
            path.write_text(json.dumps({'schema_version': 1, 'payments': [], 'recipients': []}), encoding='utf-8')
            saved = db.import_backup(path)
            self.assertEqual(db.all(), [])
            with sqlite3.connect(saved) as snapshot:
                self.assertEqual(snapshot.execute('select recipient from payments').fetchone()[0], 'Oryginał')
                self.assertEqual(snapshot.execute('pragma integrity_check').fetchone()[0], 'ok')
            db.close()
