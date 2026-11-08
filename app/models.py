"""Walidacja i model danych, niezależne od interfejsu Qt."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
import re
from unicodedata import decimal, normalize


@dataclass
class Payment:
    recipient: str = ""
    recipient_address: str = ""
    recipient_account: str = ""
    amount: str = ""
    currency: str = "PLN"
    payer_account: str = ""
    payer: str = ""
    payer_address: str = ""
    title: str = ""
    note: str = ""
    payment_type: str = "W"  # W=wpłata gotówkowa; P=polecenie przelewu
    mark_wp: bool = True  # pole zachowane dla zgodności z historią, nadruk wynika z typu W/P
    amount_prefix_stars: bool = False  # niepotwierdzony wymóg dla zwykłego druku; opcjonalne ** z instrukcji podatkowych
    amount_end_bar: bool = True  # niestandardowe wizualne zabezpieczenie wolnego miejsca po kwocie

    def as_dict(self):
        return asdict(self)


AMOUNT_CELLS = 12
AMOUNT_PREFIX = "**"


class InvalidPayment(ValueError):
    pass


def account_digits(account: str) -> str:
    stripped = re.sub(r"[\s-]+", "", account).upper()
    if stripped.startswith("PL"):
        stripped = stripped[2:]
    if stripped and not stripped.isdecimal():
        raise InvalidPayment("Numer rachunku może zawierać wyłącznie cyfry (opcjonalnie PL).")
    return "".join(str(decimal(char)) for char in stripped)


def valid_nrb(value: str) -> bool:
    """Kontrola NRB / polskiego IBAN przez ISO 13616 mod 97."""
    try:
        digits = account_digits(value)
    except InvalidPayment:
        return False
    if len(digits) != 26:
        return False
    return int(digits[2:] + "2521" + digits[:2]) % 97 == 1


def normalized_amount(value: str) -> str:
    value = value.strip().replace(" ", "").replace("\u00a0", "").replace(".", ",")
    if not re.fullmatch(r"\d+(?:,\d{1,2})?", value):
        raise InvalidPayment("Kwota musi mieć postać np. 125,50.")
    try:
        amount = Decimal(value.replace(",", "."))
    except InvalidOperation as exc:
        raise InvalidPayment("Nieprawidłowa kwota.") from exc
    if not amount.is_finite() or amount <= 0:
        raise InvalidPayment("Kwota musi być większa od zera.")
    normalized = f"{amount:.2f}".replace(".", ",")
    if len(normalized) > AMOUNT_CELLS:
        raise InvalidPayment("Kwota nie mieści się w 12 kratkach blankietu.")
    return normalized


def fit_rows(text: str, rows: int = 1, ideal_columns: int = 27) -> list[str]:
    """Wiersze do nadruku. Długie teksty są składane do szerokości, nie ucinane.

    Przy dwóch wierszach dzielimy na słowach w pobliżu połowy długości.
    Jawne podziały wierszy z formularza są respektowane do liczby `rows`.
    """
    value = normalize("NFC", text).replace("\t", " ").strip().upper()
    lines = [" ".join(line.split()) for line in value.splitlines() if line.strip()]
    if len(lines) > rows:
        raise InvalidPayment(f"Dostępnych jest {rows} wierszy; usuń nadmiarowe ręczne podziały.")
    if not lines:
        return [""] * rows
    if rows == 1 or len(lines) == rows:
        return lines + [""] * (rows - len(lines))
    # Nie dzielimy krótkiego tekstu tylko po to, aby wykorzystać drugi wiersz.
    line = lines[0]
    if len(line) <= ideal_columns:
        return [line, ""]
    words = line.split(" ")
    if len(words) == 1:
        mid = (len(line) + 1) // 2
        return [line[:mid], line[mid:]]
    splits = [(" ".join(words[:i]), " ".join(words[i:])) for i in range(1, len(words))]
    # Każdy wiersz może być dłuższy od liczby kratek: wtedy zostanie ściśnięty.
    return list(min(splits, key=lambda pair: (max(len(pair[0]), len(pair[1])),
                                            abs(len(pair[0])-len(pair[1])))))


def split_grid(text: str, columns: int = 27, rows: int = 2) -> list[str]:
    """Zachowany pomocniczy mechanizm dla pól o sztywnym limicie znaków."""
    result = fit_rows(text, rows=rows, ideal_columns=columns)
    if any(len(line) > columns for line in result):
        raise InvalidPayment(f"Za długi tekst: dostępne są {rows} wiersze po {columns} znaków.")
    return result


def payment_issues(payment: Payment, strict: bool = True) -> list[tuple[str, str]]:
    errors = []
    if payment.payment_type not in ("W", "P"):
        errors.append(("payment_type", "Rodzaj operacji musi być W (wpłata) albo P (przelew)."))
    if payment.payment_type == "P" and (strict or payment.payer_account.strip()):
        if not valid_nrb(payment.payer_account):
            errors.append(("payer_account", "Dla przelewu podaj poprawny rachunek zleceniodawcy (26 cyfr)."))
    for key, label in (
        ("recipient", "Odbiorca"),
        ("recipient_address", "Adres odbiorcy"),
        ("payer", "Wpłacający"),
        ("payer_address", "Adres wpłacającego"),
        ("title", "Tytuł"),
    ):
        value = getattr(payment, key)
        if strict and not value.strip():
            errors.append((key, f"Uzupełnij pole: {label}."))
        try:
            fit_rows(value, rows=2 if key == "title" else 1)
        except InvalidPayment as exc:
            errors.append((key, f"{label}: {exc}"))
    if strict and not payment.recipient_account.strip():
        errors.append(("recipient_account", "Uzupełnij numer rachunku odbiorcy."))
    elif payment.recipient_account.strip() and not valid_nrb(payment.recipient_account):
        errors.append(("recipient_account", "Niepoprawny numer rachunku odbiorcy (26 cyfr / suma kontrolna)."))
    # Dla W w tym miejscu kwota słownie; dla P pełen NRB zleceniodawcy.
    if strict and not payment.amount.strip():
        errors.append(("amount", "Uzupełnij kwotę."))
    elif payment.amount.strip():
        try:
            amount = normalized_amount(payment.amount)
            if payment.amount_prefix_stars and len(AMOUNT_PREFIX + amount) > AMOUNT_CELLS:
                errors.append(("amount", "Kwota z gwiazdkami nie mieści się w 12 kratkach. Wyłącz gwiazdki."))
        except InvalidPayment as exc:
            errors.append(("amount", str(exc)))
    if payment.currency.strip().upper() != "PLN":
        errors.append(("currency", "Ten druk obsługuje wyłącznie kwoty w złotych (PLN)."))
    return errors


def check(payment: Payment, strict: bool = True) -> list[str]:
    return [message for _, message in payment_issues(payment, strict)]
