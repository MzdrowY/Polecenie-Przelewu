"""Zapis polskiej kwoty PLN pełnymi słowami (złote i grosze)."""
from __future__ import annotations
from decimal import Decimal
from .models import normalized_amount

UNITS = ("zero", "jeden", "dwa", "trzy", "cztery", "pięć", "sześć", "siedem", "osiem", "dziewięć")
TEENS = ("dziesięć", "jedenaście", "dwanaście", "trzynaście", "czternaście", "piętnaście", "szesnaście", "siedemnaście", "osiemnaście", "dziewiętnaście")
TENS = ("", "", "dwadzieścia", "trzydzieści", "czterdzieści", "pięćdziesiąt", "sześćdziesiąt", "siedemdziesiąt", "osiemdziesiąt", "dziewięćdziesiąt")
HUNDREDS = ("", "sto", "dwieście", "trzysta", "czterysta", "pięćset", "sześćset", "siedemset", "osiemset", "dziewięćset")


def _triplet(n: int) -> str:
    assert 0 <= n < 1000
    parts = []
    h, r = divmod(n, 100)
    t, u = divmod(r, 10)
    if h:
        parts.append(HUNDREDS[h])
    if t == 1:
        parts.append(TEENS[u])
    else:
        if t:
            parts.append(TENS[t])
        if u:
            parts.append(UNITS[u])
    return " ".join(parts)


def _form(n: int, forms: tuple[str, str, str]) -> str:
    """Poprawna odmiana: 1, 2–4 (z wyjątkiem 12–14), pozostałe."""
    if n == 1:
        return forms[0]
    last2 = n % 100
    if 12 <= last2 <= 14:
        return forms[2]
    if n % 10 in (2, 3, 4):
        return forms[1]
    return forms[2]


def number_words(n: int) -> str:
    if n < 0 or n > 999_999_999:
        raise ValueError("Obsługiwane liczby: 0–999 999 999")
    if n == 0:
        return "zero"
    parts = []
    groups = ((1_000_000, ("milion", "miliony", "milionów")),
              (1000, ("tysiąc", "tysiące", "tysięcy")),
              (1, None))
    for divisor, forms in groups:
        triplet = n // divisor
        n %= divisor
        if not triplet:
            continue
        # Jeden tysiąc / jeden milion są zazwyczaj zapisywane jako "tysiąc" / "milion".
        if forms and triplet == 1:
            parts.append(forms[0])
        else:
            part = _triplet(triplet)
            if forms:
                part += " " + _form(triplet, forms)
            parts.append(part)
    return " ".join(parts)


def amount_in_words(value: str) -> str:
    """Np. '1234,56' -> 'tysiąc dwieście trzydzieści cztery złote pięćdziesiąt sześć groszy'."""
    normalized = normalized_amount(value)
    dec = Decimal(normalized.replace(",", "."))
    zl = int(dec)
    gr = int((dec - zl) * 100)
    return (f"{number_words(zl)} {_form(zl, ('złoty', 'złote', 'złotych'))} "
            f"{number_words(gr)} {_form(gr, ('grosz', 'grosze', 'groszy'))}")
