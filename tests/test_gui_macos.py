"""Sprawdzenie przepływu Qt na macOS bez używania historii użytkownika."""
from contextlib import closing
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import pymupdf
from PySide6.QtCore import Qt
from PySide6.QtGui import QPageSize
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QPushButton, QDialog, QLabel

from app.database import Database
from app.pdfgen import ACCOUNT_X, PX_PT
from app.ui import Window
from test_core import valid_test_account


@unittest.skipUnless(sys.platform == "darwin", "Test okna macOS")
class MacGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = Database(self.root / "history.sqlite3")
        self.window = Window(self.db)
        self.addCleanup(self.window.close)
        self.window.show()

    def click(self, label):
        button = next(w for w in self.window.findChildren(QPushButton) if w.text() == label)
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)

    def fill(self):
        fields = self.window._fields
        fields["recipient"].setText("Żółć Fikcyjna o długiej nazwie odbiorcy")
        fields["recipient_address"].setText("Łódź, ul. Próbna 1")
        fields["recipient_account"].setText("PL " + valid_test_account())
        fields["payer"].setText("Świętosław Próbny")
        fields["payer_address"].setText("Gdańsk, ul. Testowa 2")
        fields["amount"].setText("1,01")
        fields["title"].setPlainText("Tytuł testowy\nDrugi wiersz")
        fields["note"].setPlainText("NOTATKA PRYWATNA")
        self.assertTrue(fields["currency"].isReadOnly())
        self.assertEqual(fields["currency"].text(), "PLN")

    def export(self, kind):
        path = self.root / f"{kind}.pdf"
        with patch.object(QFileDialog, "getSaveFileName", return_value=(str(path), "PDF")):
            self.click("Eksportuj PDF")
        self.assertTrue(path.is_file())
        return path

    def verify_pdf(self, path, shared, amount):
        with pymupdf.open(path) as doc:
            self.assertEqual(len(doc), 1)
            page = doc[0]
            self.assertAlmostEqual(page.rect.width, 595.22, places=1)
            self.assertAlmostEqual(page.rect.height, 842, places=1)
            self.assertNotIn("NOTATKA", page.get_text())
            for offset in (0, 474):
                for baseline, expected, left, right in (
                    (240, shared, ACCOUNT_X[0], ACCOUNT_X[-1]),
                    (204, amount, 483, 745),
                ):
                    clip = pymupdf.Rect(left * PX_PT, (baseline + offset - 12) * PX_PT,
                                        right * PX_PT, (baseline + offset + 10) * PX_PT)
                    actual = "".join(page.get_text(clip=clip).split())
                    self.assertEqual(actual, expected)

    def test_cash_transfer_and_history(self):
        self.fill()
        self.assertFalse(self.window.payer_account_field.isEnabled())
        self.assertEqual(self.window.words_preview.text(), "Słownie: jeden złoty jeden grosz")
        self.click("Zapisz w historii")
        cash = self.window.current_id
        self.verify_pdf(self.export("W"), "JEDENZŁOTYJEDENGROSZ", "1,01")
        self.click("Historia")
        self.click("Użyj jako szablonu")
        self.assertIsNone(self.window.current_id)
        self.click("P · Przelew")
        self.assertTrue(self.window.payer_account_field.isEnabled())
        self.assertFalse(self.window.words_preview.isEnabled())
        self.click("Zapisz w historii")
        self.assertIn("rachunek zleceniodawcy", self.window._issue_labels["payer_account"].text())
        payer = valid_test_account("109000000000000000000099")
        self.window.payer_account_field.setText(payer)
        self.window._fields["amount"].setText("1250,50")
        self.window.amount_stars_box.click()
        self.window.amount_bar_box.click()
        self.click("Zapisz w historii")
        transfer = self.window.current_id
        self.assertNotEqual(cash, transfer)
        self.verify_pdf(self.export("P"), payer, "**1250,50")
        self.click("+ Nowy")
        self.assertEqual(self.window.current_data().recipient, "")
        self.click("Historia")
        self.window.search.setText("1250,50")
        self.assertEqual(self.window.history.count(), 1)
        self.window.history.setCurrentRow(0)
        self.assertEqual(self.window.current_id, transfer)
        self.assertTrue(self.window.amount_stars_box.isChecked())
        self.assertFalse(self.window.amount_bar_box.isChecked())
        self.assertEqual(self.window.current_data().note, "NOTATKA PRYWATNA")
        self.window._fields["amount"].setText("99,99")
        self.click("Zapisz w historii")
        self.assertEqual(self.db.get(transfer).amount, "99,99")
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            self.click("Usuń")
        self.assertEqual(len(self.db.all()), 2)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.click("Usuń")
        self.assertEqual([r["id"] for r in self.db.all()], [cash])
        with closing(Database(self.root / "history.sqlite3").conn) as conn:
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_catalog_reuses_recipient_without_overwriting_history(self):
        self.fill()
        self.window._fields["recipient"].setText("Jan Kowalski")
        self.click("Zapisz w historii")
        saved = self.window.current_id
        self.window._fields["amount"].setText("25,00")
        self.window._fields["recipient"].setText("Inna osoba")
        self.click("Odbiorcy")
        self.window.recipient_search.setText("kowalski")
        self.assertEqual(self.window.recipient_list.count(), 1)
        self.click("Wstaw do formularza")
        data = self.window.current_data()
        self.assertEqual(data.recipient, "Jan Kowalski")
        self.assertEqual(data.recipient_address, "Łódź, ul. Próbna 1")
        self.assertEqual(data.recipient_account.replace(" ", ""), valid_test_account())
        self.assertEqual(data.amount, "25,00")
        self.assertIsNone(self.window.current_id)
        self.assertEqual(self.db.get(saved).amount, "1,01")

    def test_preview_switches_to_readable_receipt_and_keeps_form(self):
        self.window.resize(850, 600)
        self.fill()
        self.window._fields["recipient_account"].setText("PL 12")
        with patch("app.ui.preview_png") as render:
            self.click("Sprawdź wydruk →")
            render.assert_not_called()
        self.assertIs(self.window.pages.currentWidget(), self.window.form_page)
        self.assertTrue(self.window._fields["recipient_account"].property("invalid"))

        self.fill()
        self.click("Sprawdź wydruk →")
        self.assertIs(self.window.pages.currentWidget(), self.window.preview_page)
        self.assertEqual(self.window.preview_modes.checkedId(), 0)
        self.assertGreaterEqual(self.window.preview_label.width(), 750)
        first = self.window.preview_label.pixmap().toImage()
        self.click("Cała strona A4")
        self.assertNotEqual(first, self.window.preview_label.pixmap().toImage())
        self.assertGreater(self.window.preview_label.height(), self.window.preview_label.width())
        self.click("← Wróć do edycji (Esc)")
        self.assertIs(self.window.pages.currentWidget(), self.window.form_page)
        self.assertEqual(self.window.current_data().title, "Tytuł testowy\nDrugi wiersz")
        self.assertIsNone(self.window.current_id)

    def test_checked_state_switch_updates_transfer_field(self):
        self.window.payment_types.button(1).setChecked(True)
        self.assertTrue(self.window.payer_account_field.isEnabled())
        self.assertEqual(self.window.shared_fields.currentIndex(), 1)
        self.window.payment_types.button(0).setChecked(True)
        self.assertFalse(self.window.payer_account_field.isEnabled())
        self.assertEqual(self.window.shared_fields.currentIndex(), 0)

    def test_about_and_import_confirmation(self):
        messages = []
        def capture_about():
            dialog = self.window.findChild(QDialog, 'aboutDialog')
            messages.extend(label.text() for label in dialog.findChildren(QLabel))
            return 0
        with patch.object(QDialog, 'exec', side_effect=capture_about):
            self.window._show_about()
            message = ' '.join(messages)
            for expected in ('0.12.1', 'Maciej Zdrowowicz', 'mzdrowy@gmail.com', 'MIT',
                             'https://github.com/MzdrowY/Polecenie-Przelewu'):
                self.assertIn(expected, message)
        self.fill()
        self.click('Zapisz w historii')
        ident = self.window.current_id
        backup = self.root / 'backup.json'
        self.db.export_backup(backup)
        with patch.object(QFileDialog, 'getOpenFileName', return_value=(str(backup), 'JSON')):
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
                self.window.import_backup()
        self.assertEqual(self.window.current_id, ident)
        with patch.object(QFileDialog, 'getOpenFileName', return_value=(str(backup), 'JSON')):
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
                with patch.object(QMessageBox, 'information') as info:
                    self.window.import_backup()
        self.assertIsNone(self.window.current_id)
        self.assertEqual(len(self.db.all()), 1)
        self.assertIn('historia-przed-importem-', info.call_args.args[2])

    def test_update_check_results_and_download_choice(self):
        def response(tag):
            reply = Mock()
            reply.__enter__ = Mock(return_value=reply)
            reply.__exit__ = Mock(return_value=False)
            reply.read.return_value = json.dumps({'tag_name': tag,
                'html_url': 'https://example.com/release'}).encode()
            return reply
        with patch('app.ui.urllib.request.urlopen', return_value=response('v0.12.1')):
            with patch.object(self.window, '_show_update_message') as message:
                self.window._check_for_updates()
                self.assertIn('aktualnej wersji', message.call_args.args[1])
        with patch('app.ui.urllib.request.urlopen', return_value=response('v0.12.2')):
            with patch.object(self.window, '_show_update_message', return_value=True) as message:
                with patch('app.ui.QDesktopServices.openUrl') as open_url:
                    self.window._check_for_updates()
                    self.assertTrue(message.call_args.kwargs['offer_download'])
                    self.assertEqual(open_url.call_args.args[0].toString(), 'https://example.com/release')
        with patch('app.ui.urllib.request.urlopen', side_effect=OSError('brak połączenia')):
            with patch.object(self.window, '_show_update_message') as message:
                self.window._check_for_updates()
                self.assertIn('brak połączenia', message.call_args.args[1])

    def test_print_to_pdf_through_button(self):
        self.fill()
        path = self.root / "print.pdf"

        def pdf_printer(printer, _window):
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(str(path))
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            return Mock(exec=lambda: QPrintDialog.DialogCode.Accepted)

        dialog = Mock(side_effect=pdf_printer, DialogCode=QPrintDialog.DialogCode)
        self.click("Sprawdź wydruk →")
        with patch("app.ui.QPrintDialog", dialog):
            self.click("Drukuj blankiet")
        with pymupdf.open(path) as doc:
            self.assertEqual(len(doc), 1)
            page = doc[0]
            self.assertLess(abs(page.rect.width - 595.28), 1)
            self.assertLess(abs(page.rect.height - 841.89), 1)
            self.assertTrue(page.get_images())

    def test_old_record_keeps_defaults_when_reopened(self):
        self.fill()
        payment = self.window.current_data()
        ident = self.db.save(payment)
        legacy = payment.as_dict()
        for key in ("payment_type", "mark_wp", "amount_prefix_stars", "amount_end_bar"):
            legacy.pop(key)
        with self.db.conn:
            self.db.conn.execute("UPDATE payments SET data_json = ? WHERE id = ?",
                                 (json.dumps(legacy), ident))
        self.window.refresh_history()
        self.window.history.setCurrentRow(0)
        self.assertEqual(self.window.current_data(), payment)
