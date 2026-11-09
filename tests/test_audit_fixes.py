"""Testy regresyjne po audycie 2026-11-09."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from app.database import Database, DatabaseOpenError
from app.models import Payment
from app.ui import Window
from test_core import valid_test_account


class DatabaseOpenErrorTests(unittest.TestCase):
    def test_corrupt_database_raises_and_preserves_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "historia.sqlite3"
            path.write_bytes(b"to nie jest baza sqlite")
            with self.assertRaises(DatabaseOpenError) as ctx:
                Database(path)
            self.assertIsInstance(ctx.exception.cause, sqlite3.DatabaseError)
            self.assertEqual(path.read_bytes(), b"to nie jest baza sqlite")

    def test_unwritable_directory_raises_and_creates_nothing(self):
        if sys.platform == "win32" or getattr(os, "geteuid", lambda: 1000)() == 0:
            self.skipTest("Test wymaga katalogu bez prawa zapisu niebędącego rootem.")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "readonly"
            root.mkdir()
            root.chmod(0o500)
            try:
                target = root / "historia.sqlite3"
                with self.assertRaises(DatabaseOpenError):
                    Database(target)
                self.assertFalse(target.exists())
            finally:
                root.chmod(0o700)


@unittest.skipUnless(sys.platform == "darwin", "Test okna macOS")
class AuditGuiRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = Database(self.root / "history.sqlite3")
        self.window = Window(self.db)
        self.addCleanup(self.close_window)
        self.window.show()

    def close_window(self):
        # Testy nie mogą zawiesić się na pytaniu o niezapisane zmiany.
        self.window._dirty = False
        self.window.close()

    def fill(self):
        fields = self.window._fields
        fields["recipient"].setText("Jan Kowalski")
        fields["recipient_address"].setText("ul. Testowa 1, 00-001 Warszawa")
        fields["recipient_account"].setText("PL " + valid_test_account())
        fields["payer"].setText("Anna Nowak")
        fields["payer_address"].setText("ul. Przykładowa 2")
        fields["amount"].setText("1,01")
        fields["title"].setPlainText("Tytuł testowy\nDrugi wiersz")

    def history_item(self, payment_id):
        for row in range(self.window.history.count()):
            item = self.window.history.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == payment_id:
                return item
        raise AssertionError(f"Brak wpisu {payment_id} w historii")

    def test_new_document_asks_before_discarding_unsaved_changes(self):
        self.fill()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Cancel):
            self.window.new_document()
        self.assertEqual(self.window.current_data().recipient, "Jan Kowalski")
        self.assertTrue(self.window._dirty)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            self.window.new_document()
        self.assertEqual(self.window.current_data().recipient, "")
        self.assertFalse(self.window._dirty)
        self.assertIsNone(self.window.current_id)

    def test_new_document_save_choice_persists_form_before_clearing(self):
        self.fill()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.window.new_document()
        self.assertEqual(len(self.db.all()), 1)
        self.assertEqual(self.window.current_data().recipient, "")
        self.assertFalse(self.window._dirty)

    def test_history_selection_asks_before_discarding_unsaved_changes(self):
        first = Payment(recipient="Pierwszy", recipient_account="PL " + valid_test_account(),
                        amount="10,00", title="A")
        second = Payment(recipient="Drugi", recipient_account="PL " + valid_test_account(),
                         amount="20,00", title="B")
        first_id = self.db.save(first)
        second_id = self.db.save(second)
        self.window.refresh_history()
        item_first = self.history_item(first_id)
        item_second = self.history_item(second_id)

        self.fill()
        self.window._fields["recipient"].setText("Zmieniony")
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Cancel):
            self.window.open_history(item_first, None)
        self.assertEqual(self.window.current_data().recipient, "Zmieniony")
        self.assertIsNone(self.window.current_id)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            self.window.open_history(item_first, None)
        self.assertEqual(self.window.current_id, first_id)
        self.assertEqual(self.window.current_data().recipient, "Pierwszy")
        self.assertFalse(self.window._dirty)

        self.window._fields["recipient"].setText("Edytowany")
        # Zapis pierwszego wpisu odświeża listę historii.
        item_second = self.history_item(second_id)
        item_first = self.history_item(first_id)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.window.open_history(item_second, item_first)
        self.assertEqual(self.window.current_id, second_id)
        self.assertEqual(self.window.current_data().recipient, "Drugi")
        self.assertEqual(self.db.get(first_id).recipient, "Edytowany")

    def test_close_event_respects_unsaved_changes(self):
        self.fill()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Cancel):
            self.window.close()
        self.assertTrue(self.window.isVisible())
        self.assertEqual(self.window.current_data().recipient, "Jan Kowalski")

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            self.window.close()
        self.assertFalse(self.window.isVisible())

    def test_close_event_save_choice_persists_form(self):
        self.fill()
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.window.close()
        self.assertFalse(self.window.isVisible())
        with closing(sqlite3.connect(self.db.path)) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM payments").fetchone()[0], 1)

    def test_new_document_clears_preview(self):
        self.window._preview_pixmap = QPixmap(10, 10)
        self.window._preview_pixmap.fill()
        self.window.pages.setCurrentWidget(self.window.preview_page)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            self.window.new_document()
        self.assertIs(self.window.pages.currentWidget(), self.window.form_page)
        self.assertTrue(self.window._preview_pixmap.isNull())

    def test_counters_refresh_after_loading(self):
        payment = Payment(
            recipient="Jan Kowalski",
            recipient_address="ul. Testowa 1, 00-001 Warszawa",
            recipient_account="PL " + valid_test_account(),
            payer="Anna Nowak",
            payer_address="ul. Przykładowa 2",
            amount="1,01",
            title="Tytuł testowy\nDrugi wiersz",
        )
        ident = self.db.save(payment)
        self.window.refresh_history()
        self.window.open_history(self.history_item(ident), None)
        self.assertEqual(self.window.recipient_char_count.text(),
                         f"{max(len(payment.recipient), len(payment.recipient_address))}/27 zn.")
        self.assertEqual(self.window.payer_char_count.text(),
                         f"{max(len(payment.payer), len(payment.payer_address))}/27 zn.")
        self.assertEqual(self.window.title_char_count.text(),
                         f"{max(len(line) for line in payment.title.splitlines())}/27 zn.")

    def test_tab_moves_from_title_to_note(self):
        title = self.window._fields["title"]
        note = self.window._fields["note"]
        title.setPlainText("Tytuł testowy")
        title.setFocus()
        QTest.keyClick(title, Qt.Key.Key_Tab)
        self.assertEqual(title.toPlainText(), "Tytuł testowy")
        self.assertIs(self.window.focusWidget(), note)

    def test_payment_options_mark_form_dirty(self):
        self.window.payment_types.button(1).setChecked(True)
        self.assertTrue(self.window._dirty)
        self.window.new_document(force=True)
        self.window.amount_stars_box.setChecked(True)
        self.assertTrue(self.window._dirty)
