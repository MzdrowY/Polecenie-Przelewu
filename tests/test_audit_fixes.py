"""Testy regresyjne po audycie 2026-11-09."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QPixmap, QContextMenuEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox, QPushButton

import pymupdf

from app.database import Database, DatabaseOpenError
from app.models import Payment, requirement_gaps
from app.pdfgen import generate_pdf, illegible_fields
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

    def choose_unsaved_action(self, label):
        def choose():
            dialog = QApplication.activeModalWidget()
            if dialog is None:
                return
            try:
                next(button for button in dialog.findChildren(QPushButton) if button.text() == label).click()
            finally:
                if dialog.isVisible():
                    dialog.reject()

        QTimer.singleShot(0, choose)
        self.window.new_document()

    def test_new_document_asks_before_discarding_unsaved_changes(self):
        self.fill()
        appearance = []

        def cancel_dialog():
            dialog = QApplication.activeModalWidget()
            if dialog is None:
                return
            try:
                buttons = {button.text(): button.isDefault() for button in dialog.findChildren(QPushButton)}
                appearance.append((dialog.grab().toImage().pixelColor(4, 4).name(), buttons))
                QTest.keyClick(dialog, Qt.Key.Key_Escape)
                appearance.append(dialog.isVisible())
            finally:
                if dialog.isVisible():
                    dialog.reject()

        QTimer.singleShot(0, cancel_dialog)
        self.window.new_document()
        self.assertEqual(appearance, [
            ("#f3f2ee", {"Anuluj": True, "Nie zapisuj": False, "Zapisz": False}), False,
        ])
        self.assertEqual(self.window.current_data().recipient, "Jan Kowalski")
        self.assertTrue(self.window._dirty)

        self.choose_unsaved_action("Nie zapisuj")
        self.assertEqual(self.window.current_data().recipient, "")
        self.assertFalse(self.window._dirty)
        self.assertIsNone(self.window.current_id)

    def test_new_document_save_choice_persists_form_before_clearing(self):
        self.fill()
        self.choose_unsaved_action("Zapisz")
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
        with patch.object(QDialog, "exec", return_value=QDialog.DialogCode.Rejected):
            self.window.open_history(item_first, None)
        self.assertEqual(self.window.current_data().recipient, "Zmieniony")
        self.assertIsNone(self.window.current_id)

        with patch.object(QDialog, "exec", return_value=QMessageBox.StandardButton.Discard.value):
            self.window.open_history(item_first, None)
        self.assertEqual(self.window.current_id, first_id)
        self.assertEqual(self.window.current_data().recipient, "Pierwszy")
        self.assertFalse(self.window._dirty)

        self.window._fields["recipient"].setText("Edytowany")
        # Zapis pierwszego wpisu odświeża listę historii.
        item_second = self.history_item(second_id)
        item_first = self.history_item(first_id)
        with patch.object(QDialog, "exec", return_value=QDialog.DialogCode.Accepted):
            self.window.open_history(item_second, item_first)
        self.assertEqual(self.window.current_id, second_id)
        self.assertEqual(self.window.current_data().recipient, "Drugi")
        self.assertEqual(self.db.get(first_id).recipient, "Edytowany")

    def test_close_event_respects_unsaved_changes(self):
        self.fill()
        with patch.object(QDialog, "exec", return_value=QDialog.DialogCode.Rejected):
            self.window.close()
        self.assertTrue(self.window.isVisible())
        self.assertEqual(self.window.current_data().recipient, "Jan Kowalski")

        with patch.object(QDialog, "exec", return_value=QMessageBox.StandardButton.Discard.value):
            self.window.close()
        self.assertFalse(self.window.isVisible())

    def test_close_event_save_choice_persists_form(self):
        self.fill()
        with patch.object(QDialog, "exec", return_value=QDialog.DialogCode.Accepted):
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

    def test_title_counter_refreshes_after_loading(self):
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



class PdfPerformanceTests(unittest.TestCase):
    def test_readability_warning_flags_only_illegible_rows(self):
        base = dict(recipient_account=valid_test_account(), amount="1,00")
        self.assertEqual(illegible_fields(Payment(title="A" * 100, **base)), [])
        self.assertEqual(illegible_fields(Payment(title="A" * 200, **base)), [])
        warned = illegible_fields(Payment(title="A" * 400, **base))
        self.assertTrue(warned)
        self.assertEqual(warned[0][0], "Tytuł płatności")
        self.assertLess(warned[0][2], 4.5)

    def test_readability_warning_does_not_truncate_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Payment(title="A" * 400, recipient_account=valid_test_account(),
                           amount="1,00")
            out = Path(tmp) / "dlugi.pdf"
            generate_pdf(data, out)
            import pymupdf
            with pymupdf.open(out) as doc:
                text = "".join(doc[0].get_text().split())
            self.assertIn("A" * 200, text)

    def test_readability_warning_flags_huge_amount_words(self):
        data = Payment(amount="999999999,99", recipient_account=valid_test_account())
        warned = illegible_fields(data)
        self.assertTrue(any(label == "Kwota słownie" for label, _, _ in warned))

    def test_readability_warning_flags_long_recipient_and_payer(self):
        data = Payment(
            recipient="ODBIORCA " + "X" * 400,
            payer="ZLECENIODAWCA " + "Y" * 400,
            recipient_account=valid_test_account(),
            amount="1,00",
        )
        labels = {label for label, _count, _effective in illegible_fields(data)}
        self.assertIn("Odbiorca (nazwa i adres)", labels)
        self.assertIn("Zleceniodawca (nazwa i adres)", labels)


@unittest.skipUnless(sys.platform == "darwin", "Test okna macOS")
class AuditGuiStage2Tests(unittest.TestCase):
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
        self.window.resize(850, 540)
        self.window.show()

    def close_window(self):
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

    def test_edit_menu_copies_and_pastes_selected_text(self):
        field = self.window._fields["recipient"]
        field.setText("Ala ma kota")
        field.setFocus()
        field.selectAll()
        self.window._update_edit_actions()
        self.window._edit_actions["copy"].trigger()
        self.assertEqual(QApplication.clipboard().text(), "Ala ma kota")
        field.clear()
        self.window._update_edit_actions()
        self.window._edit_actions["paste"].trigger()
        self.assertEqual(field.text(), "Ala ma kota")

    def test_qt_context_menu_uses_polish_labels(self):
        from app.ui import install_polish_translations
        app = QApplication.instance()
        install_polish_translations(app)
        field = self.window._fields["recipient"]
        menu = field.createStandardContextMenu()
        labels = [action.text().split("\t")[0].replace("&", "") for action in menu.actions() if action.text()]
        self.assertIn("Skopiuj", labels)
        self.assertIn("Wklej", labels)

    def test_field_context_menu_matches_project_style_and_copies(self):
        field = self.window._fields["recipient"]
        field.setText("Ala ma kota")
        field.selectAll()
        menu = self.window._build_field_context_menu(field)
        self.addCleanup(menu.deleteLater)
        labels = [action.text() for action in menu.actions() if action.text()]
        self.assertEqual(
            labels,
            ["Cofnij", "Ponów", "Wytnij", "Skopiuj", "Wklej", "Usuń", "Zaznacz wszystko"],
        )
        self.assertIn("#ffffff", menu.styleSheet())
        self.assertIn("#eae8e1", menu.styleSheet())
        copy_action = next(action for action in menu.actions() if action.text() == "Skopiuj")
        self.assertTrue(copy_action.isEnabled())
        copy_action.trigger()
        self.assertEqual(QApplication.clipboard().text(), "Ala ma kota")

    def test_field_context_menu_pastes_and_uses_custom_policy(self):
        field = self.window._fields["recipient"]
        field.clear()
        QApplication.clipboard().setText("Nowy tekst")
        menu = self.window._build_field_context_menu(field)
        self.addCleanup(menu.deleteLater)
        paste_action = next(action for action in menu.actions() if action.text() == "Wklej")
        self.assertTrue(paste_action.isEnabled())
        paste_action.trigger()
        self.assertEqual(field.text(), "Nowy tekst")
        self.assertEqual(field.contextMenuPolicy(), Qt.ContextMenuPolicy.CustomContextMenu)

    def test_custom_context_menu_opens_for_line_and_plain_text_fields(self):
        for key in ("recipient", "title"):
            field = self.window._fields[key]
            target = field.viewport() if key == "title" else field
            pos = QPoint(20, 10)
            event = QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, pos, target.mapToGlobal(pos)
            )
            menu = Mock()
            with patch.object(self.window, "_build_field_context_menu", return_value=menu) as build:
                QApplication.sendEvent(target, event)
                self.assertTrue(build.called)
                self.assertTrue(menu.exec.called)
            self.assertEqual(field.contextMenuPolicy(), Qt.ContextMenuPolicy.CustomContextMenu)

    def test_history_panel_close_button_hides_panel(self):
        self.window.history_toggle.setChecked(True)
        self.assertTrue(self.window.history_panel.isVisible())
        self.window.history_close.click()
        self.assertFalse(self.window.history_panel.isVisible())
        self.assertFalse(self.window.history_toggle.isChecked())

    def test_history_panel_reduces_editor_width_without_overlay(self):
        before = self.window.editor.width()
        self.window.history_toggle.setChecked(True)
        after = self.window.editor.width()
        self.assertLess(after, before)
        # panel nie leży nad edytorem: sąsiaduje z nim w układzie
        self.assertFalse(self.window.history_panel.geometry().intersects(self.window.editor.geometry()))

    def test_export_warns_about_illegible_text_and_can_abort(self):
        self.fill()
        self.window._fields["title"].setPlainText("A" * 400)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No) as question:
            with patch.object(QFileDialog, "getSaveFileName", return_value=(str(self.root / "x.pdf"), "PDF")):
                self.window.click_export = None
                self.window.export_document()
        self.assertTrue(question.called)
        self.assertFalse((self.root / "x.pdf").exists())

    def test_export_warns_about_illegible_text_and_can_continue(self):
        self.fill()
        self.window._fields["title"].setPlainText("A" * 400)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            with patch.object(QFileDialog, "getSaveFileName", return_value=(str(self.root / "x.pdf"), "PDF")):
                self.window.export_document()
        self.assertTrue((self.root / "x.pdf").exists())
        with pymupdf.open(self.root / "x.pdf") as doc:
            self.assertIn("A" * 200, "".join(doc[0].get_text().split()))

    def test_export_warns_about_heavily_compressed_person_details(self):
        self.fill()
        name = "Firma " + "Transport " * 23 + "Oddział Centralny"
        address = "ul. " + "Międzynarodowa " * 18 + "123, 00-001 Warszawa"
        self.window._fields["recipient"].setText(name)
        self.window._fields["recipient_address"].setText(address)
        path = self.root / "dlugi-adres.pdf"
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes) as question:
            with patch.object(QFileDialog, "getSaveFileName", return_value=(str(path), "PDF")):
                self.window.export_document()
        self.assertTrue(question.called)
        self.assertIn("Odbiorca (nazwa i adres)", question.call_args.args[2])
        with pymupdf.open(path) as doc:
            text = "".join(doc[0].get_text().replace("\xad", "-").split())
        self.assertEqual(text.count("".join((name + address).upper().split())), 2)

    def test_dirty_stays_set_when_saving_fails(self):
        self.fill()
        with patch.object(self.window.db, "save", side_effect=OSError("błąd zapisu")) as save:
            with patch.object(QMessageBox, "critical"), patch.object(
                QDialog, "exec", return_value=QDialog.DialogCode.Accepted,
            ):
                self.window.new_document()
        save.assert_called_once()
        self.assertTrue(self.window._dirty)
        self.assertEqual(len(self.db.all()), 0)
        self.assertEqual(self.window.current_data().recipient, "Jan Kowalski")



class RequirementGapTests(unittest.TestCase):
    def base(self, **kwargs):
        fields = dict(recipient="Jan Kowalski", payer="Anna Nowak",
                      payer_address="ul. Przykładowa 2, 00-001 Warszawa",
                      title="Tytuł", recipient_account=valid_test_account(),
                      amount="1,00", payment_type="W")
        fields.update(kwargs)
        return Payment(**fields)

    def test_complete_payment_has_no_gaps(self):
        self.assertEqual(requirement_gaps(self.base()), [])

    def test_missing_regulated_fields_are_reported(self):
        gaps = requirement_gaps(self.base(payer="", payer_address="", title=""))
        self.assertEqual([key for key, _ in gaps], ["payer", "payer_address", "title"])

    def test_recipient_address_is_optional_per_regulation(self):
        self.assertEqual(requirement_gaps(self.base(recipient_address="")), [])

    def test_transfer_is_not_checked(self):
        self.assertEqual(requirement_gaps(self.base(payment_type="P", payer="")), [])

    def test_gaps_do_not_block_pdf_generation(self):
        data = self.base(payer="", title="")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "brak-pol.pdf"
            generate_pdf(data, out)
            self.assertTrue(out.exists())
            import pymupdf
            with pymupdf.open(out) as doc:
                self.assertIn("1,00", "".join(doc[0].get_text().split()))


@unittest.skipUnless(sys.platform == "darwin", "Test okna macOS")
class AuditGuiStage2WarningTests(unittest.TestCase):
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
        self.window.resize(850, 540)
        self.window.show()

    def close_window(self):
        self.window._dirty = False
        self.window.close()

    def fill(self):
        fields = self.window._fields
        fields["recipient"].setText("Jan Kowalski")
        fields["recipient_account"].setText("PL " + valid_test_account())
        fields["amount"].setText("1,01")
        fields["title"].setPlainText("Tytuł testowy")

    def test_export_warns_about_missing_required_fields_and_can_abort(self):
        self.fill()  # bez wpłacającego i adresu wpłacającego
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No) as question:
            with patch.object(QFileDialog, "getSaveFileName", return_value=(str(self.root / "y.pdf"), "PDF")):
                self.window.export_document()
        self.assertTrue(question.called)
        text = question.call_args.args[2]
        self.assertIn("regulamin Poczty Polskiej", text)
        self.assertFalse((self.root / "y.pdf").exists())

    def test_export_without_gaps_does_not_warn(self):
        self.fill()
        fields = self.window._fields
        fields["payer"].setText("Anna Nowak")
        fields["payer_address"].setText("ul. Przykładowa 2, 00-001 Warszawa")
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes) as question:
            with patch.object(QFileDialog, "getSaveFileName", return_value=(str(self.root / "y.pdf"), "PDF")):
                self.window.export_document()
            self.assertFalse(question.called)
        self.assertTrue((self.root / "y.pdf").exists())
