"""Graficzny interfejs Qt; nie używa internetu ani zewnętrznych kont."""
from __future__ import annotations
from pathlib import Path
import json
import tempfile
import urllib.request

import pymupdf as fitz
from PySide6.QtCore import Qt, QByteArray, QStandardPaths, QEvent, QRect, QRectF, QUrl, QSettings
from PySide6.QtGui import QPixmap, QImage, QPainter, QPageSize, QPageLayout, QFontDatabase, QKeySequence, QShortcut, QColor, QIcon, QAction, QDesktopServices
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QButtonGroup, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QStackedWidget,
    QScrollArea, QListWidget, QListWidgetItem, QFileDialog, QMessageBox,
    QFrame, QGraphicsDropShadowEffect, QDoubleSpinBox,
)

from .models import Payment, InvalidPayment, account_digits, valid_nrb, normalized_amount, payment_issues
from .amount_words import amount_in_words
from .pdfgen import generate_pdf, preview_png, PX_PT, SECTION_OFFSET_PX
from .database import Database


STYLE = """
QMainWindow, QWidget#workspace, QScrollArea#editor, QWidget#formBody {
    background: #f3f2ee;
}
QWidget { color: #141413; font-size: 13px; }
QLabel { background: transparent; }
QLabel#appTitle { font-size: 18px; font-weight: 700; }
QLabel#heading { font-size: 15px; font-weight: 700; }
QLabel#muted, QStatusBar { color: #57534e; }
QLabel#footerStatus { color: #78756e; font-size: 12px; }
QLabel#issue { color: #a62f25; font-weight: 600; }
QLabel#valid { color: #15803d; background: #dcfce7; border-radius: 6px;
    padding: 2px 8px; font-size: 11px; font-weight: 700; }
QLabel#caption { color: #78756e; font-size: 11px; font-weight: 700; }
QLabel#count { color: #746f67; font-size: 11px; }
QWidget#toolbar, QWidget#actions, QStatusBar { background: #f3f2ee; }
QFrame#BentoCard, QWidget#historyPanel { background: #ffffff; border: 1px solid #e4e2dd;
    border-radius: 12px; }
QFrame#Hairline { background: #efece6; border: none; }
QFrame#CardStrip { background: #f3f2ee; border-bottom-left-radius: 11px;
    border-bottom-right-radius: 11px; }
QFrame#SegmentTrack { background: #e5e3dc; border-radius: 9px; }
QLineEdit, QPlainTextEdit {
    border: 1px solid #e4e2dd; background: #faf9f6; color: #141413; padding: 4px 6px;
    border-radius: 8px; selection-background-color: #18181b; selection-color: #ffffff;
    placeholder-text-color: #77736c;
}
QLineEdit:focus, QPlainTextEdit:focus { background: #ffffff; border: 1.5px solid #18181b; }
QPlainTextEdit#note { background: #faf9f6; border: 1px dashed #d6d3cd; }
QPlainTextEdit#note:focus { background: #ffffff; border: 1.5px solid #18181b; }
QLineEdit[invalid="true"], QPlainTextEdit[invalid="true"] { background: #fcecea; border: 1.5px solid #DC2626; }
QLineEdit#account { font-size: 20px; font-weight: 700; }
QLineEdit#amount { font-size: 22px; font-weight: 700; }
QLineEdit#personName { font-size: 15px; font-weight: 500; }
QLineEdit#personAddress { font-size: 14px; color: #3f3d39; }
QLabel#amountWords { color: #57534e; font-size: 12px; padding: 0 10px 0 0; }
QLineEdit[searchField="true"] { background: white; border: 1px solid #e4e2dd; padding: 7px 9px; }
QLineEdit[searchField="true"]:focus { border-color: #78756e; }
QPushButton { border: 1px solid #d6d3cd; border-radius: 8px; padding: 6px 11px;
    background: #ffffff; font-weight: 600; }
QPushButton:hover { background: #faf9f5; }
QPushButton:focus { border-color: #78756e; }
QPushButton#quiet { background: #EAE7DF; color: #18181B; border: none;
    border-radius: 7px; padding: 5px 10px; font-weight: 500; }
QPushButton#quiet:hover { background: #DEDAD0; }
QPushButton#quiet:focus { border-color: #78756e; }
QPushButton#segment { border: 1px solid transparent; background: transparent;
    border-radius: 7px; color: #68655e; font-weight: 500; padding: 4px 10px; }
QPushButton#segment:checked { background: #ffffff; border-color: #d6d3cd;
    color: #141413; font-weight: 600; }
QPushButton#segment:focus, QPushButton#chip:focus { border-color: #78756e; }
QPushButton#chip { background: #f3f2ee; color: #57534e; border: 1px solid #d6d3cd;
    border-radius: 6px; padding: 3px 10px; font-size: 12px; font-weight: 500; }
QPushButton#chip:checked { background: #18181b; color: #ffffff; border: 1px solid #18181b; }
QPushButton#primary, QPushButton#printAction { color: #ffffff; padding: 8px 16px; }
QPushButton#primary { background: #18181b; border: none; font-weight: 600; }
QPushButton#primary:hover { background: #27272a; }
QPushButton#printAction { background: #c8382b; border-color: #c8382b; }
QPushButton#printAction:hover { background: #aa3025; }
QPushButton#primary:focus, QPushButton#printAction:focus { border-color: #78756e; }
QPushButton#primary:disabled { background: #e4e2dd; border-color: #e4e2dd; color: #57534e; }
QPushButton#danger { color: #a62f25; }
QListWidget { background: white; border: 1px solid #e4e2dd; border-radius: 8px; }
QListWidget::item { margin: 2px; padding: 8px; border-radius: 6px; }
QListWidget::item:hover { background: #faf9f6; }
QListWidget::item:selected { background: #eae8e1; color: #141413; }
QScrollArea#paperCanvas { background: #e5e3dc; border: none; }
QDoubleSpinBox { background: #FFFFFF; color: #18181B; border: 1px solid #D6D3CD;
    border-radius: 6px; padding: 3px 8px; font-size: 12px; font-weight: 500; min-width: 78px; }
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { background: #F3F2EE; border: none; width: 14px; }
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover { background: #DEDAD0; }
"""


PREVIEW_SCALE = 4
# Granice drukowanego odcinka w oryginalnym PDF, w punktach.
FIRST_RECEIPT = QRectF(72, 33, 449, 313)


class Window(QMainWindow):
    def __init__(self, database: Database):
        super().__init__()
        self.db = database
        self.current_id: int | None = None
        self._preview_pixmap = QPixmap()
        self._issue_labels = {}
        self._form_focus = None
        self._active_person = ""
        self._fields: dict[str,QLineEdit|QPlainTextEdit] = {}
        self.setWindowTitle("Polecenie przelewu — wpłata / przelew")
        self._make_menu()
        self.resize(850, 540)
        self.setMinimumSize(760, 490)
        self._make_ui()
        self.new_document()
        self.refresh_history()
        self.statusBar().clearMessage()

    def _make_menu(self):
        file_menu = self.menuBar().addMenu("Plik")
        export_action = QAction("Eksportuj kopię zapasową (JSON)…", self)
        export_action.triggered.connect(self.export_backup)
        file_menu.addAction(export_action)
        import_action = QAction("Importuj kopię zapasową (JSON)…", self)
        import_action.triggered.connect(self.import_backup)
        file_menu.addAction(import_action)
        help_menu = self.menuBar().addMenu("Pomoc")
        action = QAction("Sprawdź aktualizacje", self)
        action.triggered.connect(self._check_for_updates)
        help_menu.addAction(action)
        about = QAction("O programie", self)
        about.triggered.connect(self._show_about)
        help_menu.addAction(about)

    def _check_for_updates(self):
        from app import __version__
        url = "https://api.github.com/repos/MzdrowY/Polecenie-Przelewu/releases/latest"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PoleceniePrzelewu"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            tag = data.get("tag_name", "").lstrip("v")
            html_url = data.get("html_url", "")

            def _vt(s):
                parts = []
                for p in str(s).split("."):
                    digits = "".join(c for c in p if c.isdigit())
                    parts.append(int(digits) if digits else 0)
                while len(parts) < 3:
                    parts.append(0)
                return tuple(parts[:3])

            if tag and _vt(tag) > _vt(__version__):
                reply = QMessageBox.question(
                    self, "Aktualizacja",
                    f"Dostępna jest nowa wersja: {tag} (obecna: {__version__}).\nOtworzyć stronę pobierania?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes and html_url:
                    QDesktopServices.openUrl(QUrl(html_url))
            else:
                QMessageBox.information(self, "Aktualizacje", f"Używasz aktualnej wersji ({__version__}).")
        except Exception as exc:
            QMessageBox.warning(self, "Aktualizacje", f"Nie udało się sprawdzić aktualizacji:\n{exc}")

    def _show_about(self):
        from app import __version__
        QMessageBox.about(
            self, "O programie",
            f'<h3>Polecenie przelewu</h3><p>Wersja {__version__}</p>'
            '<p>Wypełnianie i drukowanie blankietów wpłaty gotówkowej i polecenia przelewu.</p>'
            '<p>Autor: Maciej Zdrowowicz<br>Kontakt: <a href="mailto:mzdrowy@gmail.com">mzdrowy@gmail.com</a><br>'
            'Licencja: MIT<br><a href="https://github.com/MzdrowY/Polecenie-Przelewu">Repozytorium GitHub</a></p>'
            '<p>Aplikacja nie jest podpisana certyfikatem Apple Developer.</p>',
        )

    def export_backup(self):
        path, _ = QFileDialog.getSaveFileName(self, "Eksportuj kopię zapasową", str(Path.home() / "Documents" / "polecenie-przelewu-backup.json"), "JSON (*.json)")
        if not path:
            return
        try:
            self.db.export_backup(Path(path))
            self.statusBar().showMessage("Wyeksportowano kopię zapasową: " + path)
        except Exception as exc:
            QMessageBox.critical(self, "Błąd eksportu", str(exc))

    def import_backup(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importuj kopię zapasową", str(Path.home() / "Documents"), "JSON (*.json)")
        if not path:
            return
        if QMessageBox.question(self, "Przywróć kopię zapasową",
                "Import zastąpi całą obecną historię i książkę odbiorców. "
                "Przed zmianą zostanie zachowana kopia obecnej bazy. Kontynuować?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        try:
            saved_backup = self.db.import_backup(Path(path))
            self.new_document()
            self.refresh_history()
            QMessageBox.information(self, "Kopia przywrócona", f"Przywrócono dane. Kopia poprzedniej bazy:\n{saved_backup}")
        except Exception as exc:
            QMessageBox.critical(self, "Błąd importu", str(exc))

    def _toggle_grid_text(self, visible):
        self.grid_toggle.setText("Ukryj siatkę blankietu" if visible else "Pokaż siatkę blankietu")
        self._resize_preview()

    def _settings(self):
        return QSettings("PoleceniePrzelewu", "PoleceniePrzelewu")

    def _load_offset(self, axis):
        return float(self._settings().value(f"calib_{axis}", 0.0))

    def _save_offset_x(self, value):
        self._settings().setValue("calib_x", float(value))
        self._on_offset_changed()

    def _save_offset_y(self, value):
        self._settings().setValue("calib_y", float(value))
        self._on_offset_changed()

    def _on_offset_changed(self):
        if hasattr(self, "_preview_pixmap") and not self._preview_pixmap.isNull():
            self.show_preview() if False else None
            # regeneruj podgląd z nową kalibracją
            try:
                data = self.validated()
            except Exception:
                data = None
            if data is not None:
                png = preview_png(data, scale=PREVIEW_SCALE, offset_x_mm=self.offset_x_spin.value(), offset_y_mm=self.offset_y_spin.value())
                pixmap = QPixmap()
                if pixmap.loadFromData(QByteArray(png), "PNG"):
                    self._preview_pixmap = pixmap
                    self.preview_modes.button(0).setChecked(True)
                    self._change_preview_mode()

    def _make_ui(self):
        self.setStyleSheet(STYLE)
        workspace = QWidget()
        workspace.setObjectName("workspace")
        root = QVBoxLayout(workspace)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(workspace)

        self.pages = QStackedWidget()
        root.addWidget(self.pages)
        self.form_page = QWidget()
        self.pages.addWidget(self.form_page)
        form_layout = QVBoxLayout(self.form_page)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(0)
        header = self._bar(form_layout, "toolbar")
        self._button(header, "Odbiorcy", self.show_recipients, style="quiet")
        self.history_toggle = self._button(header, "Historia", style="quiet")
        self.history_toggle.setCheckable(True)
        header.addStretch()
        self.payment_types = self._segments(header, ("W · Wpłata gotówkowa", "P · Przelew"))
        self.payment_types.idToggled.connect(self._payment_type_toggled)
        header.addStretch()
        self._button(header, "+ Nowy", self.new_document, style="quiet")

        body = QHBoxLayout()
        body.setContentsMargins(16, 10, 16, 10)
        body.setSpacing(10)
        form_layout.addLayout(body, 1)

        # HISTORIA
        left = QWidget(self.form_page)
        self.history_panel = left
        left.setObjectName("historyPanel")
        left.setFixedWidth(280)
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(13, 18, 9, 12)
        head = QLabel("Historia")
        head.setObjectName("heading")
        left_l.addWidget(head)
        info = QLabel("Zapisane blankiety")
        info.setObjectName("muted")
        left_l.addWidget(info)
        self.search = QLineEdit()
        self.search.setProperty("searchField", True)
        self.search.setPlaceholderText("Szukaj odbiorcy, konta, kwoty...")
        self.search.textChanged.connect(self.refresh_history)
        left_l.addWidget(self.search)
        self.search.setClearButtonEnabled(True)
        self.history = QListWidget()
        self.history.setWordWrap(True)
        self.history.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.history.currentItemChanged.connect(self.open_history)
        self.history.itemActivated.connect(lambda: self.history_toggle.setChecked(False))
        left_l.addWidget(self.history, 1)
        self._button(left_l, "Wczytaj do edycji", lambda: self.open_history(self.history.currentItem()), style="primary")
        self._button(left_l, "Użyj jako szablonu", self.duplicate_history_item, style="quiet")
        bdelete = QPushButton("Usuń")
        bdelete.setObjectName("danger")
        bdelete.clicked.connect(self.delete_document)
        left_l.addWidget(bdelete)
        left.hide()
        self.history_toggle.toggled.connect(self._toggle_history)

        editor = QScrollArea()
        editor.setObjectName("editor")
        self.editor = editor
        editor.setFrameShape(QFrame.Shape.NoFrame)
        editor.setWidgetResizable(True)
        editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body.addWidget(editor, 1)
        form = QWidget()
        form.setObjectName("formBody")
        editor.setWidget(form)
        grid = QGridLayout(form)
        grid.setContentsMargins(1, 0, 1, 1)
        grid.setSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setRowStretch(4, 1)
        grid.addWidget(self._payment_card(), 0, 0)
        grid.addWidget(self._people_card(), 1, 0)
        grid.addWidget(self._details_card(), 2, 0)
        currency = self._field("currency", "PLN")
        currency.setReadOnly(True)
        currency.hide()

        self.message = QLabel()
        self.message.setObjectName("issue")
        self.message.setWordWrap(True)
        self.message.hide()
        grid.addWidget(self.message, 3, 0)
        fields = self._fields
        order = [fields[k] for k in (
            "recipient_account", "amount", "payer_account", "recipient", "recipient_address",
            "payer", "payer_address", "title", "note",
        )]
        for previous, following in zip(order, order[1:]):
            QWidget.setTabOrder(previous, following)
        # Przyciski pomocnicze nie zabierają focusu przy Tab.
        self.amount_stars_box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.amount_bar_box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if hasattr(self, "_remember_recipient_button"):
            self._remember_recipient_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        footer = self._bar(form_layout, "actions")
        self.footer_status = QLabel()
        self.footer_status.setObjectName("footerStatus")
        self.footer_status.setWordWrap(False)
        self.footer_status.setMaximumWidth(250)
        footer.addWidget(self.footer_status, 1)
        self.statusBar().messageChanged.connect(self.footer_status.setText)
        self.statusBar().hide()
        self._button(footer, "Zapisz w historii", self.save_document, style="quiet")
        self._button(footer, "Eksportuj PDF", self.export_document)
        review = self._button(footer, "Sprawdź wydruk →", self.show_preview, style="primary")
        self._build_preview()
        self._build_recipients()
        self.form_page.installEventFilter(self)

        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self.form_page)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(review.click)
        shortcut2 = QShortcut(QKeySequence("Meta+Return"), self.form_page)
        shortcut2.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut2.activated.connect(review.click)
        new_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        new_shortcut.activated.connect(self.new_document)
        new_shortcut2 = QShortcut(QKeySequence("Meta+N"), self)
        new_shortcut2.activated.connect(self.new_document)
        back_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self.preview_page)
        back_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        back_shortcut.activated.connect(self.back_to_form)
        close_catalog = QShortcut(QKeySequence(Qt.Key.Key_Escape), self.recipients_page)
        close_catalog.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        close_catalog.activated.connect(self.back_to_form)

    def _bar(self, parent, name):
        widget = QWidget()
        widget.setObjectName(name)
        widget.setMinimumHeight(48 if name == "toolbar" else 56)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(7)
        parent.addWidget(widget)
        return layout

    def _button(self, layout, label, handler=None, *, style=""):
        button = QPushButton(label)
        if handler is not None:
            button.clicked.connect(handler)
        if style:
            button.setObjectName(style)
        layout.addWidget(button)
        return button

    def _segments(self, parent, labels):
        track = QFrame()
        track.setObjectName("SegmentTrack")
        layout = QHBoxLayout(track)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(0)
        group = QButtonGroup(self)
        for index, label in enumerate(labels):
            button = self._button(layout, label, style="segment")
            button.setCheckable(True)
            group.addButton(button, index)
        parent.addWidget(track)
        return group

    @staticmethod
    def _card():
        card = QFrame()
        card.setObjectName("BentoCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        return card, layout

    @staticmethod
    def _hairline(vertical=False):
        line = QFrame()
        line.setObjectName("Hairline")
        if vertical:
            line.setFixedWidth(1)
        else:
            line.setFixedHeight(1)
        return line

    @staticmethod
    def _caption(text):
        label = QLabel(text)
        label.setObjectName("caption")
        return label

    def _payment_card(self):
        card, layout = self._card()
        top = QHBoxLayout()
        top.setContentsMargins(14, 9, 14, 7)
        top.setSpacing(12)
        layout.addLayout(top)
        account = QVBoxLayout()
        account.setSpacing(2)
        account_heading = QHBoxLayout()
        label = self._caption("RACHUNEK ODBIORCY")
        account_heading.addWidget(label)
        account_heading.addStretch()
        self.account_status = QLabel()
        self.account_status.setObjectName("muted")
        account_heading.addWidget(self.account_status)
        account.addLayout(account_heading)
        account_field = self._field("recipient_account", "26 cyfr, opcjonalnie PL")
        account_field.setAccessibleName("Rachunek odbiorcy")
        label.setBuddy(account_field)
        account.addWidget(account_field)
        account.addWidget(self._issue_label("recipient_account"))
        top.addLayout(account, 65)
        top.addWidget(self._hairline(vertical=True))

        amount = QVBoxLayout()
        amount.setSpacing(2)
        amount_heading = QHBoxLayout()
        amount_label = self._caption("KWOTA (PLN)")
        amount_heading.addWidget(amount_label)
        amount_heading.addStretch()
        amount_heading.setSpacing(8)
        self.amount_stars_box = self._button(amount_heading, "* Gwiazdki", style="chip")
        self.amount_bar_box = self._button(amount_heading, "‒ Kreska", style="chip")
        for button, text in ((self.amount_stars_box, "Gwiazdki przed kwotą"),
                             (self.amount_bar_box, "Kreska po kwocie")):
            button.setCheckable(True)
            button.setAccessibleName(text)
            button.setToolTip(text)
        self.amount_stars_box.toggled.connect(self._clear_error)
        amount.addLayout(amount_heading)
        amount_field = self._field("amount", "np. 1250,50")
        amount_field.setAccessibleName("Kwota (PLN)")
        amount_label.setBuddy(amount_field)
        amount.addWidget(amount_field)
        amount.addWidget(self._issue_label("amount"))
        top.addLayout(amount, 35)
        layout.addWidget(self._hairline())

        strip = QFrame()
        strip.setObjectName("CardStrip")
        self.shared_strip = strip
        row = QHBoxLayout(strip)
        row.setContentsMargins(14, 0, 14, 0)
        row.setSpacing(8)
        self.shared_label = self._caption("")
        row.addWidget(self.shared_label)
        self.shared_fields = QStackedWidget()
        self.words_preview = QLabel()
        self.words_preview.setObjectName("amountWords")
        self.words_preview.setMinimumHeight(30)
        self.words_preview.setAccessibleName("Kwota słownie")
        self.shared_fields.addWidget(self.words_preview)
        self.payer_account_field = self._field("payer_account", "26 cyfr, opcjonalnie PL")
        self.payer_account_field.setAccessibleName("Rachunek zleceniodawcy")
        self.shared_fields.addWidget(self.payer_account_field)
        row.addWidget(self.shared_fields, 1)
        self.payer_account_status = QLabel()
        self.payer_account_status.setObjectName("muted")
        row.addWidget(self.payer_account_status)
        self.payer_account_status.hide()
        layout.addWidget(strip)
        layout.addWidget(self._issue_label("payer_account"))
        return card

    def _people_card(self):
        card, outer = self._card()
        row = QHBoxLayout()
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(10)
        outer.addLayout(row)
        row.addLayout(self._person_section(recipient=True), 1)
        row.addLayout(self._person_section(recipient=False), 1)
        return card

    def _person_section(self, *, recipient):
        section = QVBoxLayout()
        section.setSpacing(6)
        heading = QHBoxLayout()
        heading.addWidget(self._caption("ODBIORCA" if recipient else "WPŁACAJĄCY / ZLECENIODAWCA"))
        heading.addStretch()
        count_label = QLabel("0/27 zn.")
        count_label.setObjectName("count")
        if recipient:
            self.recipient_char_count = count_label
            self._remember_recipient_button = self._button(heading, "Zapamiętaj odbiorcę", self.remember_current_recipient, style="quiet")
            self._remember_recipient_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        else:
            self.payer_char_count = count_label
        heading.addWidget(count_label)
        section.addLayout(heading)
        prefix = "recipient" if recipient else "payer"
        for key, placeholder, accessible in (
            (prefix, "Nazwa lub imię i nazwisko (do 27 znaków)",
             "Nazwa odbiorcy" if recipient else "Nazwa wpłacającego"),
            (prefix + "_address", "Ulica, numer, kod i miejscowość (do 27 znaków)",
             "Adres odbiorcy" if recipient else "Adres wpłacającego"),
        ):
            field = self._field(key, placeholder)
            field.setAccessibleName(accessible)
            section.addWidget(field)
            section.addWidget(self._issue_label(key))
        return section

    def _details_card(self):
        card, outer = self._card()
        columns = QHBoxLayout()
        columns.setContentsMargins(14, 10, 14, 10)
        columns.setSpacing(10)
        outer.addLayout(columns)
        for key, caption, placeholder in (
            ("title", "TYTUŁEM", "Tytuł płatności"),
            ("note", "NOTATKA DO HISTORII", "Widoczna tylko w historii"),
        ):
            cell = QVBoxLayout()
            cell.setSpacing(6)
            head = QHBoxLayout()
            head.addWidget(self._caption(caption))
            head.addStretch()
            if key == "title":
                self.title_char_count = QLabel("0/27 zn.")
                self.title_char_count.setObjectName("count")
                head.addWidget(self.title_char_count)
            cell.addLayout(head)
            field = self._field(key, placeholder, multi=True)
            field.setAccessibleName("Tytuł płatności" if key == "title" else "Notatka do historii")
            cell.addWidget(field)
            if key == "title":
                cell.addWidget(self._issue_label(key))
            columns.addLayout(cell, 1)
        return card

    def _issue_label(self, key):
        label = QLabel()
        label.setObjectName("issue")
        label.setWordWrap(True)
        label.hide()
        self._issue_labels[key] = label
        return label

    def _toggle_history(self, opened):
        if opened:
            self._position_history()
            self.history_panel.raise_()
            self.history_panel.show()
            self.search.setFocus()
        else:
            self.history_panel.hide()

    def _position_history(self):
        geometry = self.editor.geometry()
        self.history_panel.setGeometry(geometry.x(), geometry.y(), self.history_panel.width(), geometry.height())

    def _field(self, key, placeholder, multi=False):
        field = QPlainTextEdit() if multi else QLineEdit()
        field.setPlaceholderText(placeholder)
        if multi:
            field.setFixedHeight(58)
        else:
            field.setMinimumHeight(34)
        if key in ("recipient_account", "payer_account", "amount"):
            field.setObjectName("amount" if key == "amount" else "account")
            field.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
            field.setMinimumHeight(42)
        if key == "note":
            field.setObjectName("note")
        field.textChanged.connect(self._clear_error)
        field.textChanged.connect(self._update_char_counts)
        field.installEventFilter(self)
        self._fields[key] = field
        if key == "amount":
            field.textChanged.connect(self._update_words)
            field.editingFinished.connect(self._format_amount)
        if key in ("recipient_account", "payer_account"):
            field.editingFinished.connect(lambda: self._format_account(field))
        if key == "recipient_account":
            field.textChanged.connect(self._update_account_status)
        if key == "payer_account":
            field.textChanged.connect(self._update_payer_account_status)
        return field

    def _build_preview(self):
        self.preview_page = QWidget()
        self.pages.addWidget(self.preview_page)
        layout = QVBoxLayout(self.preview_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = self._bar(layout, "toolbar")
        self.back_button = self._button(header, "← Wróć do edycji (Esc)", self.back_to_form, style="quiet")
        header.addStretch()
        self.preview_modes = self._segments(header, ("Powiększony odcinek", "Cała strona A4"))
        self.preview_modes.button(0).setChecked(True)
        self.preview_modes.idClicked.connect(self._change_preview_mode)
        header.addStretch()
        self.grid_toggle = self._button(header, "Ukryj siatkę blankietu", style="chip")
        self.grid_toggle.setCheckable(True)
        self.grid_toggle.setChecked(True)
        self.grid_toggle.toggled.connect(self._toggle_grid_text)

        self.preview_label = QLabel()
        self.preview_label.setAccessibleName("Wypełniony blankiet W/P")
        shadow = QGraphicsDropShadowEffect(self.preview_label)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 22))
        self.preview_label.setGraphicsEffect(shadow)
        self.preview_area = QScrollArea()
        self.preview_area.setObjectName("paperCanvas")
        self.preview_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_area.setWidget(self.preview_label)
        self.preview_area.viewport().installEventFilter(self)
        layout.addWidget(self.preview_area, 1)

        footer = self._bar(layout, "actions")
        self.print_mode_label = QLabel("Druk: pełny blankiet z danymi")
        self.print_mode_label.setObjectName("muted")
        footer.addWidget(self.print_mode_label)
        footer.addSpacing(8)
        calib_label = QLabel("Kalibracja:")
        calib_label.setObjectName("muted")
        footer.addWidget(calib_label)
        self.offset_x_spin = QDoubleSpinBox()
        self.offset_x_spin.setRange(-15.0, 15.0)
        self.offset_x_spin.setSingleStep(0.5)
        self.offset_x_spin.setSuffix(" mm X")
        self.offset_x_spin.setValue(self._load_offset("x"))
        self.offset_x_spin.valueChanged.connect(self._on_offset_changed)
        footer.addWidget(self.offset_x_spin)
        self.offset_y_spin = QDoubleSpinBox()
        self.offset_y_spin.setRange(-15.0, 15.0)
        self.offset_y_spin.setSingleStep(0.5)
        self.offset_y_spin.setSuffix(" mm Y")
        self.offset_y_spin.setValue(self._load_offset("y"))
        self.offset_y_spin.valueChanged.connect(self._on_offset_changed)
        footer.addWidget(self.offset_y_spin)
        footer.addStretch()
        self._button(footer, "Eksportuj PDF", self.export_document)
        print_button = self._button(footer, "Drukuj blankiet", self.print_document, style="printAction")
        print_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self.preview_page)
        print_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        print_shortcut.activated.connect(print_button.click)
        print_shortcut2 = QShortcut(QKeySequence(Qt.Key.Key_Enter), self.preview_page)
        print_shortcut2.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        print_shortcut2.activated.connect(print_button.click)

    def _build_recipients(self):
        self.recipients_page = QWidget()
        self.pages.addWidget(self.recipients_page)
        layout = QVBoxLayout(self.recipients_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = self._bar(layout, "toolbar")
        title = QLabel("Odbiorcy")
        title.setObjectName("appTitle")
        header.addWidget(title)
        header.addStretch()
        self._button(header, "Wróć do formularza", self.back_to_form)

        content = QVBoxLayout()
        content.setContentsMargins(16, 14, 16, 14)
        content.setSpacing(9)
        layout.addLayout(content, 1)
        self.recipient_search = QLineEdit()
        self.recipient_search.setProperty("searchField", True)
        self.recipient_search.setPlaceholderText("Szukaj po nazwisku, nazwie, adresie lub rachunku")
        self.recipient_search.setAccessibleName("Szukaj odbiorcy")
        self.recipient_search.setClearButtonEnabled(True)
        self.recipient_search.textChanged.connect(self._refresh_recipients)
        content.addWidget(self.recipient_search)
        self.recipient_info = QLabel()
        self.recipient_info.setObjectName("muted")
        self.recipient_info.setWordWrap(True)
        content.addWidget(self.recipient_info)
        self.recipient_list = QListWidget()
        self.recipient_list.setAccessibleName("Zapisani odbiorcy")
        self.recipient_list.setWordWrap(True)
        self.recipient_list.itemActivated.connect(self.use_recipient)
        content.addWidget(self.recipient_list, 1)

        footer = self._bar(layout, "actions")
        footer.addStretch()
        self.use_recipient_button = self._button(
            footer, "Wstaw do formularza", self.use_recipient, style="primary",
        )
        self.recipient_list.currentItemChanged.connect(
            lambda item, _: self.use_recipient_button.setEnabled(item is not None),
        )

    def show_recipients(self):
        self.history_toggle.setChecked(False)
        self._form_focus = self.focusWidget()
        self.recipient_search.clear()
        self._refresh_recipients()
        self.pages.setCurrentWidget(self.recipients_page)
        self.recipient_search.setFocus()

    def _refresh_recipients(self):
        self.recipient_list.clear()
        matches = self.db.recipients(self.recipient_search.text())
        for row in matches:
            details = "  ·  ".join(filter(None, (self._group_account(row["account"]), row["address"])))
            item = QListWidgetItem(f'{row["name"]}\n{details}')
            item.setData(Qt.ItemDataRole.UserRole, row)
            self.recipient_list.addItem(item)
        self.recipient_list.setCurrentRow(0 if matches else -1)
        self.use_recipient_button.setEnabled(bool(matches))
        if matches:
            self.recipient_info.setText(f"Wyniki: {len(matches)}")
        elif self.recipient_search.text().strip():
            self.recipient_info.setText("Brak pasujących odbiorców.")
        else:
            self.recipient_info.setText(
                "Baza jest pusta. W formularzu kliknij Zapamiętaj odbiorcę albo zapisz pierwszy druk.",
            )

    def use_recipient(self):
        item = self.recipient_list.currentItem()
        if item is None:
            return
        row = item.data(Qt.ItemDataRole.UserRole)
        for key, value in (
            ("recipient", row["name"]),
            ("recipient_address", row["address"]),
            ("recipient_account", self._group_account(row["account"])),
        ):
            self._fields[key].setText(value)
        self.duplicate_document()
        self.back_to_form()
        self._fields["amount"].setFocus()
        self.statusBar().showMessage(f'Wstawiono odbiorcę: {row["name"]}.')

    def remember_current_recipient(self):
        data = self.current_data()
        if not data.recipient.strip():
            key, text = "recipient", "Podaj nazwę lub nazwisko odbiorcy."
        elif not valid_nrb(data.recipient_account):
            key, text = "recipient_account", "Podaj poprawny 26-cyfrowy rachunek."
        else:
            self._clear_error()
            try:
                self.db.remember_recipient(data)
            except Exception as exc:
                QMessageBox.critical(self, "Błąd zapisu odbiorcy", str(exc))
                return
            self.statusBar().showMessage(f"Zapamiętano odbiorcę: {data.recipient.strip()}.")
            return
        self._clear_error()
        field = self._fields[key]
        self._set_invalid(field, True)
        field.setFocus()
        self._issue_labels[key].setText(text)
        self._issue_labels[key].show()

    def show_preview(self):
        data = self.validated()
        if data is None:
            return
        try:
            png = preview_png(data, scale=PREVIEW_SCALE, offset_x_mm=self.offset_x_spin.value(), offset_y_mm=self.offset_y_spin.value())
            pixmap = QPixmap()
            if not pixmap.loadFromData(QByteArray(png), "PNG"):
                raise RuntimeError("Nie można odczytać obrazu PDF.")
        except Exception as exc:
            QMessageBox.critical(self, "Nie można otworzyć podglądu", str(exc))
            return
        self._preview_pixmap = pixmap
        self._form_focus = self.focusWidget()
        self.preview_modes.button(0).setChecked(True)
        self.pages.setCurrentWidget(self.preview_page)
        self._change_preview_mode()
        self.back_button.setFocus()

    def back_to_form(self):
        self.pages.setCurrentWidget(self.form_page)
        if self._form_focus is not None:
            self._form_focus.setFocus()

    def _change_preview_mode(self, *_):
        self._resize_preview()
        self.preview_area.horizontalScrollBar().setValue(0)
        self.preview_area.verticalScrollBar().setValue(0)

    def _resize_preview(self):
        if self._preview_pixmap.isNull():
            return
        pixmap = self._preview_pixmap
        mode = self.preview_modes.checkedId()
        if mode == 0:
            region = FIRST_RECEIPT.translated(0, 0)
            pixmap = pixmap.copy(QRect(
                round(region.x() * PREVIEW_SCALE), round(region.y() * PREVIEW_SCALE),
                round(region.width() * PREVIEW_SCALE), round(region.height() * PREVIEW_SCALE),
            ))
        # Używamy szerokości obszaru zewnętrznego, aby paski przewijania
        # nie zmieniały naprzemiennie dostępnej szerokości widoku.
        width = max(1, self.preview_area.width() - 28)
        dpr = self.devicePixelRatioF()
        image = pixmap.scaledToWidth(round(width * dpr), Qt.TransformationMode.SmoothTransformation)
        image.setDevicePixelRatio(dpr)
        if getattr(self, "grid_toggle", None) is not None and self.grid_toggle.isChecked():
            painter = QPainter(image)
            painter.setPen(QColor(180, 180, 180, 120))
            step = round(20 * dpr)
            for x in range(0, image.width(), step):
                painter.drawLine(x, 0, x, image.height())
            for y in range(0, image.height(), step):
                painter.drawLine(0, y, image.width(), y)
            painter.end()
        self.preview_label.setPixmap(image)
        self.preview_label.resize(image.deviceIndependentSize().toSize())
    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.FocusIn:
            if watched in (self._fields.get("recipient"), self._fields.get("recipient_address")):
                self._active_person = "recipient"
            elif watched in (self._fields.get("payer"), self._fields.get("payer_address")):
                self._active_person = "payer"
            elif watched in (self._fields.get("title"),):
                self._active_person = "title"
            self._update_char_counts()
        if event.type() == QEvent.Type.Resize:
            if watched is self.preview_area.viewport():
                self._resize_preview()
            elif watched is self.form_page and self.history_toggle.isChecked():
                self._position_history()
        return super().eventFilter(watched, event)

    def _update_char_counts(self):
        # Tytuł: licznik dla aktywnej linii (cały tytuł, limit 27 na wiersz, ale pokazujemy długość)
        if hasattr(self, "recipient_char_count"):
            if getattr(self, "_active_person", "") == "recipient":
                field = self._fields["recipient"] if self._fields["recipient"].hasFocus() else self._fields["recipient_address"]
                self.recipient_char_count.setText(f"{len(field.text())}/27 zn.")
        if hasattr(self, "payer_char_count"):
            if getattr(self, "_active_person", "") == "payer":
                field = self._fields["payer"] if self._fields["payer"].hasFocus() else self._fields["payer_address"]
                self.payer_char_count.setText(f"{len(field.text())}/27 zn.")
        if hasattr(self, "title_char_count"):
            if self._fields["title"].hasFocus():
                # licznik dla aktywnej linii (ostatnia linia)
                text = self._fields["title"].toPlainText()
                lines = text.split("\n")
                last = lines[-1] if lines else ""
                self.title_char_count.setText(f"{len(last)}/27 zn.")
    def _format_account(self, field):
        try:
            digits = account_digits(field.text())
        except InvalidPayment:
            return
        if len(digits) == 26:
            field.setText(self._group_account(digits))

    @staticmethod
    def _group_account(digits):
        return " ".join([digits[:2], *(digits[i:i + 4] for i in range(2, 26, 4))])

    def _format_amount(self):
        field = self._fields["amount"]
        try:
            field.setText(normalized_amount(field.text()))
        except InvalidPayment:
            return

    def _update_account_status(self):
        raw = self._fields["recipient_account"].text()
        try:
            count = len(account_digits(raw))
        except InvalidPayment:
            self._account_status("Rachunek może zawierać cyfry i prefiks PL", "issue")
            return
        if count == 26:
            valid = valid_nrb(raw)
            self._account_status(
                "✓ 26/26 • Poprawny NRB" if valid else "✕ Błędny numer rachunku",
                "valid" if valid else "issue",
            )
        else:
            self._account_status(f"{count}/26 cyfr", "issue" if count > 26 else "muted")

    def _account_status(self, text, style):
        self.account_status.setText(text)
        if self.account_status.objectName() != style:
            self.account_status.setObjectName(style)
            self.account_status.style().unpolish(self.account_status)
            self.account_status.style().polish(self.account_status)

    def _update_payer_account_status(self):
        raw = self._fields["payer_account"].text()
        try:
            count = len(account_digits(raw))
        except InvalidPayment:
            self._payer_account_status("Rachunek może zawierać cyfry i prefiks PL", "issue")
            return
        if not raw.strip():
            self._payer_account_status("0/26 cyfr", "muted")
            return
        if count == 26:
            valid = valid_nrb(raw)
            self._payer_account_status(
                "✓ 26/26 • Poprawny NRB" if valid else "✕ Błędny numer rachunku",
                "valid" if valid else "issue",
            )
        else:
            self._payer_account_status(f"{count}/26 cyfr", "issue" if count > 26 else "muted")

    def _payer_account_status(self, text, style):
        self.payer_account_status.setText(text)
        if self.payer_account_status.objectName() != style:
            self.payer_account_status.setObjectName(style)
            self.payer_account_status.style().unpolish(self.payer_account_status)
            self.payer_account_status.style().polish(self.payer_account_status)

    def _clear_error(self):
        self.message.hide()
        for label in self._issue_labels.values():
            label.hide()
        for field in self._fields.values():
            if field.property("invalid"):
                self._set_invalid(field, False)

    @staticmethod
    def _set_invalid(field, invalid):
        field.setProperty("invalid", invalid)
        field.style().unpolish(field)
        field.style().polish(field)

    def current_data(self) -> Payment:
        data = {}
        for key, widget in self._fields.items():
            data[key] = widget.toPlainText() if isinstance(widget, QPlainTextEdit) else widget.text()
        data["payment_type"] = "P" if self.payment_types.checkedId() == 1 else "W"
        data["amount_prefix_stars"] = self.amount_stars_box.isChecked()
        data["amount_end_bar"] = self.amount_bar_box.isChecked()
        return Payment(**data)

    def _payment_type_toggled(self, _id, checked):
        if checked:
            self._on_payment_type_changed()

    def _on_payment_type_changed(self, *_):
        is_transfer = self.payment_types.checkedId() == 1
        self.shared_label.setText("RACHUNEK ZLECENIODAWCY" if is_transfer else "")
        self.payer_account_field.setEnabled(is_transfer)
        self.words_preview.setEnabled(not is_transfer)
        self.shared_fields.setCurrentIndex(int(is_transfer))
        self.shared_strip.setFixedHeight(46 if is_transfer else 30)
        if is_transfer:
            self.payer_account_status.show()
            self._update_payer_account_status()
        else:
            self.payer_account_status.hide()
        self._update_words()
        self._clear_error()

    def set_data(self, payment: Payment):
        for key, widget in self._fields.items():
            text = getattr(payment,key)
            if isinstance(widget,QPlainTextEdit):
                widget.setPlainText(text)
            else:
                widget.setText(text)
        self.payment_types.button(int(payment.payment_type == "P")).setChecked(True)
        self.amount_stars_box.setChecked(payment.amount_prefix_stars)
        self.amount_bar_box.setChecked(payment.amount_end_bar)
        self._on_payment_type_changed()
        self._update_account_status()

    def _update_words(self):
        amount = self._fields["amount"].text()
        try:
            self.words_preview.setText("Słownie: " + amount_in_words(amount) if amount.strip() else "Słownie: —")
        except InvalidPayment:
            self.words_preview.setText("Słownie: —")

    def refresh_history(self):
        selected = self.current_id
        self.history.blockSignals(True)
        self.history.clear()
        for row in self.db.all(self.search.text()):
            date = row["updated_at"][:10]
            item = QListWidgetItem(f'{row["recipient"] or "(bez odbiorcy)"}\n{row["amount"]} PLN   •   {date}')
            item.setData(Qt.ItemDataRole.UserRole,row["id"])
            self.history.addItem(item)
            if row["id"] == selected:
                self.history.setCurrentItem(item)
        self.history.blockSignals(False)

    def open_history(self, item, _previous=None):
        if item is None:
            return
        payment_id = item.data(Qt.ItemDataRole.UserRole)
        try:
            self.set_data(self.db.get(payment_id))
            self.current_id = payment_id
            self.statusBar().showMessage(f"Wczytano zapis nr {payment_id}.")
        except Exception as exc:
            QMessageBox.critical(self,"Nie można wczytać",str(exc))

    def new_document(self):
        self.current_id = None
        self.set_data(Payment())
        if hasattr(self,"history"):
            self.history.setCurrentItem(None)
        self.statusBar().showMessage("Nowy, niezapisany formularz.")

    def load_last_as_template(self):
        rows = self.db.all()
        if not rows:
            self.statusBar().showMessage("Historia jest jeszcze pusta.", 5000)
            return
        try:
            self.set_data(self.db.get(rows[0]["id"]))
        except Exception as exc:
            QMessageBox.critical(self, "Nie można wczytać ostatniego formularza", str(exc))
            return
        self.duplicate_document()
        self.history_toggle.setChecked(False)
        self._fields["amount"].setFocus()

    def duplicate_history_item(self):
        item = self.history.currentItem()
        if item is None:
            self.statusBar().showMessage("Wybierz formularz z historii.")
            return
        try:
            self.set_data(self.db.get(item.data(Qt.ItemDataRole.UserRole)))
        except Exception as exc:
            QMessageBox.critical(self, "Nie można powielić formularza", str(exc))
            return
        self.duplicate_document()
        self.history_toggle.setChecked(False)
        self._fields["amount"].setFocus()

    def duplicate_document(self):
        self.current_id = None
        self.history.setCurrentItem(None)
        self.statusBar().showMessage("Utworzono nowy formularz z dotychczasowymi danymi. Zapisz jako nowy wpis.")

    def validated(self) -> Payment | None:
        data = self.current_data()
        issues = payment_issues(data)
        if issues:
            self._clear_error()
            if self.pages.currentWidget() is self.preview_page:
                self.back_to_form()
            key, message = issues[0]
            field = self._fields.get(key)
            if field is not None:
                self._set_invalid(field, True)
                field.setFocus()
            label = self._issue_labels.get(key, self.message)
            label.setText(message)
            label.show()
            return None
        self._clear_error()
        return data

    def save_document(self):
        data = self.validated()
        if data is None: return
        try:
            self.current_id = self.db.save(data,self.current_id)
            self.refresh_history()
            self.statusBar().showMessage(f"Zapisano formularz nr {self.current_id} w lokalnej bazie.")
        except Exception as exc:
            QMessageBox.critical(self,"Błąd zapisu",str(exc))

    def _prepared_pdf(self,data:Payment,target:Path):
        try:
            return generate_pdf(data,target,strict=True,offset_x_mm=self.offset_x_spin.value(),offset_y_mm=self.offset_y_spin.value())
        except Exception as exc:
            QMessageBox.critical(self,"Nie można wygenerować PDF",str(exc))
            return None

    def export_document(self):
        data = self.validated()
        if data is None: return
        path, _ = QFileDialog.getSaveFileName(self,"Zapisz gotowy druk",
                    str(Path.home()/"Documents"/("wplata-gotowkowa.pdf" if data.payment_type=="W" else "polecenie-przelewu.pdf")),"Plik PDF (*.pdf)")
        if not path: return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        if self._prepared_pdf(data,Path(path)):
            self.statusBar().showMessage("Wyeksportowano gotowy druk: "+path)
            self._remember_after_output(data)

    def print_document(self):
        data = self.validated()
        if data is None: return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setFullPage(True)
        dialog = QPrintDialog(printer,self)
        dialog.setWindowTitle("Drukuj blankiet A4 (100%)")
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return
        if (printer.pageLayout().pageSize().id() != QPageSize.PageSizeId.A4
                or printer.pageLayout().orientation() != QPageLayout.Orientation.Portrait):
            QMessageBox.warning(self, "Format wydruku", "Wybierz format A4 i orientację pionową.")
            return
        try:
            printer.setFullPage(True)
            print_a4(data, printer, self.offset_x_spin.value(), self.offset_y_spin.value())
            self.statusBar().showMessage("Przekazano druk A4 do systemowego sterownika drukarki.")
            self._remember_after_output(data)
        except Exception as exc:
            QMessageBox.critical(self, "Błąd drukowania", str(exc))

    def _remember_after_output(self, data):
        try:
            self.db.remember_recipient(data)
        except Exception as exc:
            QMessageBox.warning(self, "Druk gotowy, odbiorca niezapisany", str(exc))

    def delete_document(self):
        payment_id = self.current_id
        if payment_id is None:
            QMessageBox.information(self,"Usuń","Najpierw wybierz wpis z historii.")
            return
        response = QMessageBox.question(self,"Potwierdź usunięcie",
             f"Usunąć formularz nr {payment_id} z lokalnej historii? Operacji nie można cofnąć.",
             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
             QMessageBox.StandardButton.No)
        if response == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete(payment_id)
            except Exception as exc:
                QMessageBox.critical(self, "Błąd usuwania", str(exc))
                return
            self.new_document()
            self.refresh_history()
            self.statusBar().showMessage("Usunięto wpis z historii.")

    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)


def print_a4(data: Payment, printer: QPrinter, offset_x_mm: float = 0.0, offset_y_mm: float = 0.0):
    with tempfile.TemporaryDirectory(prefix="druki_print_") as tmp:
        file = generate_pdf(data, Path(tmp) / "druk.pdf", offset_x_mm=offset_x_mm, offset_y_mm=offset_y_mm)
        with fitz.open(file) as doc:
            dpi = min(printer.resolution(), 600)
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
            image = QImage.fromData(QByteArray(pix.tobytes("png")), "PNG")
            if image.isNull():
                raise RuntimeError("Nie można utworzyć obrazu strony PDF.")
            painter = QPainter(printer)
            if not painter.isActive():
                raise RuntimeError("Nie można rozpocząć drukowania.")
            painter.drawImage(QRectF(0, 0, printer.width(), printer.height()), image)
            if not painter.end() or printer.printerState() == QPrinter.PrinterState.Error:
                raise RuntimeError("Sterownik zgłosił błąd zapisu wydruku.")


def run():
    import sys
    app = QApplication.instance() or QApplication([])
    app.setOrganizationName("Polecenie przelewu")
    app.setApplicationName("Polecenie przelewu")
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    import platform
    if platform.system() == "Windows":
        icon_path = base / "assets" / "icon.ico"
    else:
        icon_path = base / "assets" / "icon.icns"
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    new_folder = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
    legacy_folder = Path.home() / "Library" / "Application Support" / "Druki Pocztowe"
    folder = legacy_folder if legacy_folder.exists() else new_folder
    db = Database(folder/"historia.sqlite3")
    window = Window(db)
    window.show()
    raise SystemExit(app.exec())
