"""Nadruk na dostarczonym blankiecie A4; współrzędne względem referencji 110 DPI."""
from __future__ import annotations
import os
from pathlib import Path
import sys
import tempfile
from unicodedata import normalize
import pymupdf as fitz
from .models import Payment, InvalidPayment, check, account_digits, fit_rows, normalized_amount, normalized_address
from .amount_words import amount_in_words

REFERENCE_DPI = 110
PX_PT = 72 / REFERENCE_DPI
MM_PT = 72 / 25.4

# Minimalny efektywny rozmiar litery po dopasowaniu do szerokości pola.
# Poniżej tej granicy napis fizycznie mieści się w wierszu, ale jest już
# praktycznie nieczytelny na wydruku. Przy kroju 9,5 pt i polu 27 kratek
# odpowiada to ok. 150 znakom w jednym wierszu; krótsze wiersze przechodzą.
MIN_EFFECTIVE_PT_PER_CHAR = 4.5

# Kalibracja drukarki (mm) — przesunięcie wszystkich współrzędnych tekstu.
_offset_x_mm: float = 0.0
_offset_y_mm: float = 0.0

def set_calibration(offset_x_mm: float = 0.0, offset_y_mm: float = 0.0) -> None:
    global _offset_x_mm, _offset_y_mm
    _offset_x_mm = float(offset_x_mm)
    _offset_y_mm = float(offset_y_mm)

def _ox() -> float:
    return _offset_x_mm * MM_PT

def _oy() -> float:
    return _offset_y_mm * MM_PT

GRID_X = [154,175,197,219,241,263,285,307,329,351,373,394,416,438,
          460,482,504,526,548,570,592,614,636,658,680,701,723,745]
ACCOUNT_X = GRID_X[:-1]  # 26 białych kratek; ostatnia kolumna siatki nazw jest różowa.
CURRENCY_X = [395,416,438,460]
AMOUNT_X = [483,504,526,548,570,592,614,636,658,680,701,723,745]
LINES_Y = {"recipient": (94, 130), "recipient_account": 166,
           "currency": 204, "amount": 204, "amount_words": 240,
           "payer": (279, 314), "title": (351, 386)}
SECTION_OFFSET_PX = 474
# Korekta po uwadze użytkownika: litery miały zbyt wysokie położenie.
BASELINE_SHIFT_PX = 4
TITLE_EXTRA_SHIFT_PX = 1
# Środki drukowanych liter W i P w oryginalnym wzorze, współrzędne przy 110 DPI.
WP_CENTER_X_PX = {"W": 339, "P": 361}
WP_CENTER_Y_PX = 201


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / relative


def template_path() -> Path:
    return resource_path("assets/template.pdf")


def find_font() -> Path:
    candidates = [os.environ.get("DRUKI_FONT", "")]
    # Dołączony font (assets/fonts) — pierwszy wybór, jeśli istnieje.
    fonts_dir = resource_path("assets/fonts")
    if fonts_dir.is_dir():
        for p in sorted(fonts_dir.glob("*.ttf")) + sorted(fonts_dir.glob("*.otf")):
            candidates.insert(0, str(p))
    candidates += [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica Neue.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise FileNotFoundError("Brak systemowej czcionki TTF/OTF obejmującej polskie znaki.")


def _draw(page: fitz.Page, x: float, y: float, text: str,
          font: fitz.Font, fontsize: float, xscale: float = 1) -> None:
    """Rysuje pojedynczy fragment; używane też przez patche w testach."""
    origin = fitz.Point(x, y)
    morph = (origin, fitz.Matrix(xscale, 0, 0, 1, 0, 0)) if abs(xscale - 1) > 0.00001 else None
    page.insert_text(origin, text, fontsize=fontsize, fontname="DrukiFormFont",
                     color=(0.03, 0.06, 0.12), morph=morph, overlay=True)


class ShapeWriter:
    """Zbiera znaki i zapisuje je jednym Shape.

    PyMuPDF przy każdym `page.insert_text` przelicza balans Q zawartości
    strony. Przy kilkuset znakach wykonujemy to raz, a nie per znak, co
    skraca czas ok. 3–5x. Ścisnięte napisy używają tego samego mechanizmu
    `morph`, więc geometria i wygląd zostają bez zmian.
    """

    def __init__(self, page: fitz.Page, font: fitz.Font):
        self.shape = fitz.Shape(page)
        self.page = page
        self.font = font
        self.color = (0.03, 0.06, 0.12)
        self.count = 0

    def add(self, x: float, y: float, text: str, fontsize: float, xscale: float = 1.0) -> None:
        if not text:
            return
        morph = (fitz.Point(x, y), fitz.Matrix(xscale, 0, 0, 1, 0, 0)) if abs(xscale - 1) > 0.00001 else None
        self.shape.insert_text(fitz.Point(x, y), text, fontsize=fontsize,
                               fontname="DrukiFormFont", color=self.color,
                               morph=morph)
        self.count += 1

    def write(self) -> None:
        if self.count:
            self.shape.commit()


def add_fitted_line(page: fitz.Page, font: fitz.Font, text: str,
                    x_edges: list[int], baseline_px: int, dy_px: int = 0,
                    size: float = 9.5, writer: "ShapeWriter | None" = None) -> None:
    """Zapis ciągły po przekroczeniu liczby kratek.

    Wykorzystuje całą szerokość pola. Jeżeli naturalny napis jest węższy,
    rozkłada znaki równomiernie bez rozciągania liter; dłuższy napis ściska.
    """
    text = " ".join(text.upper().split())
    if not text:
        return
    left = x_edges[0] * PX_PT + 1 + _ox()
    right = x_edges[-1] * PX_PT - 1 + _ox()
    y = (baseline_px + dy_px + BASELINE_SHIFT_PX) * PX_PT + _oy()
    width = font.text_length(text, fontsize=size)
    if width <= 0 or right <= left:
        raise InvalidPayment("Nie można ustalić szerokości nadruku.")
    scale = (right - left) / width
    if scale > 1.0:
        step = (right - left) / len(text)
        for i, char in enumerate(text):
            if char == " ":
                continue
            char_width = font.text_length(char, fontsize=size)
            char_scale = min(1.0, step / char_width) if char_width else 1.0
            x = left + i * step + (step - char_width * char_scale) / 2
            if writer is None:
                _draw(page, x, y, char, font, size, xscale=char_scale)
            else:
                writer.add(x, y, char, size, xscale=char_scale)
        return
    if writer is None:
        _draw(page, left, y, text, font, size, xscale=scale)
    else:
        writer.add(left, y, text, size, xscale=scale)


def add_cells(page: fitz.Page, font: fitz.Font, text: str,
              x_edges: list[int], baseline_px: int, dy_px: int = 0,
              right: bool = False, size: float = 9.5,
              use_full_width: bool = False,
              writer: "ShapeWriter | None" = None) -> None:
    text = text.upper()
    for char in set(text) - {" "}:
        if not font.has_glyph(ord(char), fallback=False):
            raise InvalidPayment(f"Czcionka blankietu nie obsługuje znaku {char!r} (U+{ord(char):04X}).")
    capacity = len(x_edges) - 1
    if len(text) > capacity:
        # Wyłącznie po przekroczeniu pojemności kratek przejdź do trybu
        # ciągłego, dopasowanego napisu. Krótsze teksty zostają w kratkach.
        add_fitted_line(page, font, text, x_edges, baseline_px, dy_px, size=size, writer=writer)
        return
    start = capacity - len(text) if right else 0
    # Dla kwoty słownie nawet przy krótkim tekście wykorzystujemy cały wiersz,
    # ale każda litera pozostaje wyśrodkowana w PRAWDZIWEJ kratce.
    if use_full_width and len(text) > 1:
        # Pełna szerokość, ale nie rozbijamy wyrazów: dodatkowe puste
        # kratki przydzielamy najpierw pomiędzy wyrazy, a nie wewnątrz nich.
        extra = capacity - len(text)
        gap_positions = [i for i, ch in enumerate(text[:-1]) if ch == " "]
        if not gap_positions:
            gap_positions = list(range(len(text) - 1))
        additions = [0] * (len(text) - 1)
        for n in range(extra):
            additions[gap_positions[n % len(gap_positions)]] += 1
        positions = [0]
        for gap in additions:
            positions.append(positions[-1] + 1 + gap)
    else:
        positions = [start + i for i in range(len(text))]
    for i, char in enumerate(text):
        if char == " ":
            continue
        k = positions[i]
        left = x_edges[k] * PX_PT + _ox()
        right_edge = x_edges[k+1] * PX_PT + _ox()
        width = font.text_length(char, fontsize=size)
        x = left + (right_edge - left - width) / 2
        y = (baseline_px + dy_px + BASELINE_SHIFT_PX) * PX_PT + _oy()
        if writer is None:
            _draw(page, x, y, char, font, size)
        else:
            writer.add(x, y, char, size)


def draw_amount_tail_dashes(page: fitz.Page, number_of_characters: int, offset_px: int = 0) -> None:
    """Opcjonalne myślniki w pozostałych kratkach po kwocie.

    NIE jest oficjalnym wymogiem formularza W/P. Występuje tylko na życzenie
    użytkownika i może zostać wyłączone w ustawieniach formularza.
    """
    capacity = len(AMOUNT_X) - 1
    if number_of_characters >= capacity or not number_of_characters:
        return
    y = (LINES_Y["amount"] + offset_px + BASELINE_SHIFT_PX - 5.6) * PX_PT + _oy()
    for index in range(number_of_characters, capacity):
        x1 = (AMOUNT_X[index] + 6.0) * PX_PT + _ox()
        x2 = (AMOUNT_X[index + 1] - 6.0) * PX_PT + _ox()
        if x2 > x1:
            page.draw_line(fitz.Point(x1, y), fitz.Point(x2, y),
                           color=(0.06, 0.08, 0.11), width=1.0, overlay=True)


def draw_wp_cross(page: fitz.Page, payment_type: str, offset_px: int = 0) -> None:
    """Przekreślenie nieużywanej litery: W => P, P => W."""
    unused = "P" if payment_type == "W" else "W"
    x = WP_CENTER_X_PX[unused] * PX_PT + _ox()
    y = (WP_CENTER_Y_PX + offset_px) * PX_PT + _oy()
    dx, dy = 5.7 * PX_PT, 8 * PX_PT
    for p1, p2 in [((x-dx,y-dy),(x+dx,y+dy)), ((x-dx,y+dy),(x+dx,y-dy))]:
        page.draw_line(fitz.Point(*p1), fitz.Point(*p2),
                       color=(0.05,0.05,0.05), width=1.0, overlay=True)


def generate_pdf(data: Payment, target: str | Path, strict: bool = True,
                 offset_x_mm: float = 0.0, offset_y_mm: float = 0.0) -> Path:
    set_calibration(offset_x_mm, offset_y_mm)
    errors = check(data, strict=strict)
    if errors:
        raise InvalidPayment("\n".join(errors))
    return _render_pdf(data, target)


def _person_rows(name: str, address: str) -> list[str]:
    """Nazwa i adres to jedno pole o dwóch wierszach.

    Gdy użytkownik wypełni oba pola, jego podział jest zachowany: nazwa
    zostaje w pierwszym wierszu, adres w drugim. Gdy drugie pole jest puste,
    cały tekst jest składany ciągle: pierwszy wiersz wypełniamy do końca,
    reszta przechodzi do drugiego. Podział jest znakowy, więc może wypaść
    w środku kodu pocztowego. Wiersz jest tylko dopasowywany do szerokości,
    nigdy ucinany.
    """
    capacity = len(GRID_X) - 1
    name_line = " ".join(normalize("NFC", name).split())
    address_line = " ".join(normalize("NFC", normalized_address(address)).split())
    if name_line and address_line:
        return [name_line, address_line]
    combined = name_line or address_line
    if not combined:
        return ["", ""]
    return [combined[:capacity], combined[capacity:]]


def _render_pdf(data: Payment, target: str | Path, *, draft: bool = False) -> Path:
    def field(convert, fallback, *args, **kwargs):
        try:
            return convert(*args, **kwargs)
        except InvalidPayment:
            if not draft:
                raise
            return fallback

    def account(value):
        digits = account_digits(value)
        if draft and len(digits) > len(ACCOUNT_X) - 1:
            return ""
        return digits
    source = template_path()
    if not source.exists():
        raise FileNotFoundError(f"Brak dołączonego szablonu: {source}")
    font_path = find_font()
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(source)
    try:
        if len(doc) != 1 or abs(doc[0].rect.width - 595.22) > 1 or abs(doc[0].rect.height - 842) > 1:
            raise InvalidPayment("Nieoczekiwane wymiary szablonu: wymagany oryginał A4, 1 strona.")
        page = doc[0]
        page.insert_font(fontname="DrukiFormFont", fontfile=str(font_path))
        font = fitz.Font(fontfile=str(font_path))
        recipient = _person_rows(data.recipient, data.recipient_address)
        payer = _person_rows(data.payer, data.payer_address)
        title = field(fit_rows, [""] * 2, data.title, rows=2)
        acc = field(account, "", data.recipient_account)
        amount = field(normalized_amount, "", data.amount) if data.amount.strip() else ""
        words = amount_in_words(amount) if amount else ""
        payer_account = field(account, "", data.payer_account) if data.payment_type == "P" else ""
        numeric_amount = amount
        if draft and len(numeric_amount) >= len(AMOUNT_X):
            numeric_amount = ""
        writer = ShapeWriter(page, font)
        for offset in (0, SECTION_OFFSET_PX):
            field(add_cells, None, page, font, recipient[0], GRID_X, LINES_Y["recipient"][0], offset, writer=writer)
            field(add_cells, None, page, font, recipient[1], GRID_X, LINES_Y["recipient"][1], offset, writer=writer)
            field(add_cells, None, page, font, acc, ACCOUNT_X, LINES_Y["recipient_account"], offset, writer=writer)
            field(add_cells, None, page, font, data.currency.strip(), CURRENCY_X, LINES_Y["currency"], offset, size=9, writer=writer)
            # Standardowy zapis kwoty od lewej, bez rozciągania cyfr.
            field(add_cells, None, page, font, numeric_amount, AMOUNT_X, LINES_Y["amount"], offset, right=False, writer=writer)
            draw_amount_tail_dashes(page, len(numeric_amount), offset)
            # Kwota słownie traktowana jak pole kratkowe: każda litera w kratce,
            # a ścisnięcie dopiero po przekroczeniu liczby kratek.
            if data.payment_type == "W":
                field(add_cells, None, page, font, words,
                      ACCOUNT_X, LINES_Y["amount_words"], offset, size=9.2, writer=writer)
            else:
                field(add_cells, None, page, font, payer_account,
                      ACCOUNT_X, LINES_Y["amount_words"], offset, size=9.2, writer=writer)
            draw_wp_cross(page, data.payment_type, offset)
            field(add_cells, None, page, font, payer[0], GRID_X, LINES_Y["payer"][0], offset, writer=writer)
            field(add_cells, None, page, font, payer[1], GRID_X, LINES_Y["payer"][1], offset, writer=writer)
            field(add_cells, None, page, font, title[0], GRID_X, LINES_Y["title"][0],
                      offset + TITLE_EXTRA_SHIFT_PX, writer=writer)
            field(add_cells, None, page, font, title[1], GRID_X, LINES_Y["title"][1],
                      offset + TITLE_EXTRA_SHIFT_PX, writer=writer)
        writer.write()
        doc.set_metadata({"title":"Polecenie przelewu / wpłata gotówkowa — wypełnione"})
        doc.save(str(path), garbage=4, deflate=True)
    finally:
        doc.close()
    return path


def illegible_fields(data: Payment) -> list[tuple[str, int, float]]:
    """Sprawdza czytelność pól, które mogą zostać nadmiernie ściśnięte."""
    font = fitz.Font(fontfile=str(find_font()))
    result: list[tuple[str, int, float]] = []

    def inspect(label: str, lines: list[str], x_edges: list[int], size: float) -> None:
        capacity = len(x_edges) - 1
        field_width = (x_edges[-1] - x_edges[0]) * PX_PT
        for line in lines:
            text = " ".join(line.upper().split())
            if not text or len(text) <= capacity:
                continue
            natural = font.text_length(text, fontsize=size)
            if natural <= 0 or field_width <= 0:
                continue
            effective = size * field_width / natural
            if effective < MIN_EFFECTIVE_PT_PER_CHAR:
                result.append((label, len(text), effective))

    try:
        inspect("Tytuł płatności", fit_rows(data.title, rows=2), GRID_X, 9.5)
    except InvalidPayment:
        pass
    inspect("Odbiorca (nazwa i adres)",
            _person_rows(data.recipient, data.recipient_address), GRID_X, 9.5)
    inspect("Zleceniodawca (nazwa i adres)",
            _person_rows(data.payer, data.payer_address), GRID_X, 9.5)
    inspect("Kwota słownie",
            fit_rows(amount_in_words(data.amount), rows=1) if data.amount.strip() else [""],
            ACCOUNT_X, 9.2)
    inspect("Rachunek zleceniodawcy",
            fit_rows(data.payer_account, rows=1) if data.payment_type == "P" else [""],
            ACCOUNT_X, 9.2)
    return result


def preview_png(data: Payment, scale: float = 1.25,
                offset_x_mm: float = 0.0, offset_y_mm: float = 0.0, strict: bool = False) -> bytes:
    with tempfile.TemporaryDirectory(prefix="druki_view_") as tmp:
        pdf = generate_pdf(data, Path(tmp) / "preview.pdf", strict=strict, offset_x_mm=offset_x_mm, offset_y_mm=offset_y_mm)
        with fitz.open(pdf) as doc:
            return doc[0].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).tobytes("png")
