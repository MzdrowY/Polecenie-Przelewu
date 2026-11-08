"""Nadruk na dostarczonym blankiecie A4; współrzędne względem referencji 110 DPI."""
from __future__ import annotations
import os
from pathlib import Path
import sys
import tempfile
import pymupdf as fitz
from .models import AMOUNT_PREFIX, Payment, InvalidPayment, check, account_digits, fit_rows, normalized_amount
from .amount_words import amount_in_words

REFERENCE_DPI = 110
PX_PT = 72 / REFERENCE_DPI
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
    candidates = [
        os.environ.get("DRUKI_FONT", ""),
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
    origin = fitz.Point(x, y)
    morph = (origin, fitz.Matrix(xscale, 0, 0, 1, 0, 0)) if abs(xscale - 1) > 0.00001 else None
    page.insert_text(origin, text, fontsize=fontsize, fontname="DrukiFormFont",
                     color=(0.03, 0.06, 0.12), morph=morph, overlay=True)


def add_fitted_line(page: fitz.Page, font: fitz.Font, text: str,
                    x_edges: list[int], baseline_px: int, dy_px: int = 0,
                    size: float = 9.5) -> None:
    """Zapis ciągły po przekroczeniu liczby kratek.

    Zużywa CAŁĄ dostępną szerokość: krótszy tekst rozciąga poziomo,
    dłuższy ściska. Nie zmienia wysokości glifów i nie ucina końca.
    """
    text = " ".join(text.upper().split())
    if not text:
        return
    left = x_edges[0] * PX_PT + 1
    right = x_edges[-1] * PX_PT - 1
    y = (baseline_px + dy_px + BASELINE_SHIFT_PX) * PX_PT
    width = font.text_length(text, fontsize=size)
    if width <= 0 or right <= left:
        raise InvalidPayment("Nie można ustalić szerokości nadruku.")
    scale = (right - left) / width
    _draw(page, left, y, text, font, size, xscale=scale)


def add_cells(page: fitz.Page, font: fitz.Font, text: str,
              x_edges: list[int], baseline_px: int, dy_px: int = 0,
              right: bool = False, size: float = 9.5,
              use_full_width: bool = False) -> None:
    text = text.upper()
    for char in set(text) - {" "}:
        if not font.has_glyph(ord(char), fallback=False):
            raise InvalidPayment(f"Czcionka blankietu nie obsługuje znaku {char!r} (U+{ord(char):04X}).")
    capacity = len(x_edges) - 1
    if len(text) > capacity:
        # Wyłącznie po przekroczeniu pojemności kratek przejdź do trybu
        # ciągłego, dopasowanego napisu. Krótsze teksty zostają w kratkach.
        add_fitted_line(page, font, text, x_edges, baseline_px, dy_px, size=size)
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
        left = x_edges[k] * PX_PT
        right_edge = x_edges[k+1] * PX_PT
        width = font.text_length(char, fontsize=size)
        x = left + (right_edge - left - width) / 2
        y = (baseline_px + dy_px + BASELINE_SHIFT_PX) * PX_PT
        _draw(page, x, y, char, font, size)


def draw_amount_tail_bar(page: fitz.Page, number_of_characters: int, offset_px: int = 0) -> None:
    """Opcjonalna linia w pozostałych kratkach po kwocie.

    NIE jest oficjalnym wymogiem formularza W/P. Występuje tylko na życzenie
    użytkownika i może zostać wyłączona w ustawieniach formularza.
    """
    capacity = len(AMOUNT_X) - 1
    if number_of_characters >= capacity or not number_of_characters:
        return
    x1 = (AMOUNT_X[number_of_characters] + 3.0) * PX_PT
    x2 = (AMOUNT_X[-1] - 3.0) * PX_PT
    y = (LINES_Y["amount"] + offset_px + BASELINE_SHIFT_PX - 5.6) * PX_PT
    if x2 > x1:
        page.draw_line(fitz.Point(x1, y), fitz.Point(x2, y),
                       color=(0.06, 0.08, 0.11), width=1.0, overlay=True)


def draw_wp_cross(page: fitz.Page, payment_type: str, offset_px: int = 0) -> None:
    """Przekreślenie nieużywanej litery: W => P, P => W."""
    unused = "P" if payment_type == "W" else "W"
    x = WP_CENTER_X_PX[unused] * PX_PT
    y = (WP_CENTER_Y_PX + offset_px) * PX_PT
    dx, dy = 5.7 * PX_PT, 8 * PX_PT
    for p1, p2 in [((x-dx,y-dy),(x+dx,y+dy)), ((x-dx,y+dy),(x+dx,y-dy))]:
        page.draw_line(fitz.Point(*p1), fitz.Point(*p2),
                       color=(0.05,0.05,0.05), width=1.0, overlay=True)


def generate_pdf(data: Payment, target: str | Path, strict: bool = True) -> Path:
    errors = check(data, strict=strict)
    if errors:
        raise InvalidPayment("\n".join(errors))
    return _render_pdf(data, target)


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
        recipient = field(fit_rows, [""] * 1, data.recipient, rows=1)
        recipient_address = field(fit_rows, [""] * 1, data.recipient_address, rows=1)
        payer = field(fit_rows, [""] * 1, data.payer, rows=1)
        payer_address = field(fit_rows, [""] * 1, data.payer_address, rows=1)
        title = field(fit_rows, [""] * 2, data.title, rows=2)
        acc = field(account, "", data.recipient_account)
        amount = field(normalized_amount, "", data.amount) if data.amount.strip() else ""
        words = amount_in_words(amount) if amount else ""
        payer_account = field(account, "", data.payer_account) if data.payment_type == "P" else ""
        numeric_amount = (AMOUNT_PREFIX if data.amount_prefix_stars else "") + amount if amount else ""
        if draft and len(numeric_amount) >= len(AMOUNT_X):
            numeric_amount = ""
        for offset in (0, SECTION_OFFSET_PX):
            field(add_cells, None, page, font, recipient[0], GRID_X, LINES_Y["recipient"][0], offset)
            field(add_cells, None, page, font, recipient_address[0], GRID_X, LINES_Y["recipient"][1], offset)
            field(add_cells, None, page, font, acc, ACCOUNT_X, LINES_Y["recipient_account"], offset)
            field(add_cells, None, page, font, data.currency.strip(), CURRENCY_X, LINES_Y["currency"], offset, size=9)
            # Standardowy zapis kwoty od lewej, bez rozciągania cyfr.
            field(add_cells, None, page, font, numeric_amount, AMOUNT_X, LINES_Y["amount"], offset, right=False)
            if data.amount_end_bar:
                draw_amount_tail_bar(page, len(numeric_amount), offset)
            # Kwota słownie: zawsze wypełnia cały wiersz; do 26 znaków w kratkach,
            # po przekroczeniu pojemności w trybie ciągłym (rozciągana lub ściskana).
            field(add_cells, None, page, font, words if data.payment_type == "W" else payer_account,
                      ACCOUNT_X, LINES_Y["amount_words"], offset, size=9.2,
                      use_full_width=data.payment_type == "W")
            draw_wp_cross(page, data.payment_type, offset)
            field(add_cells, None, page, font, payer[0], GRID_X, LINES_Y["payer"][0], offset)
            field(add_cells, None, page, font, payer_address[0], GRID_X, LINES_Y["payer"][1], offset)
            field(add_cells, None, page, font, title[0], GRID_X, LINES_Y["title"][0],
                      offset + TITLE_EXTRA_SHIFT_PX)
            field(add_cells, None, page, font, title[1], GRID_X, LINES_Y["title"][1],
                      offset + TITLE_EXTRA_SHIFT_PX)
        doc.set_metadata({"title":"Polecenie przelewu / wpłata gotówkowa — wypełnione"})
        doc.save(str(path), garbage=4, deflate=True)
    finally:
        doc.close()
    return path


def preview_png(data: Payment, scale: float = 1.25) -> bytes:
    with tempfile.TemporaryDirectory(prefix="druki_view_") as tmp:
        pdf = generate_pdf(data, Path(tmp) / "preview.pdf")
        with fitz.open(pdf) as doc:
            return doc[0].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).tobytes("png")
