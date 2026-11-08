"""Testy v0.12: kalibracja, migracje, backup."""
import json
import tempfile
import unittest
from pathlib import Path

from app.database import Database, SCHEMA_VERSION
from app.models import Payment
from app.pdfgen import generate_pdf, preview_png


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