# Polecenie przelewu — AGENTS

## Co to jest

Aplikacja desktopowa do wypełniania i drukowania pocztowych blankietów
wpłaty gotówkowej (W) i polecenia przelewu (P) na oryginalnym podkładzie A4.
Stack: Python 3.12, PySide6, PyMuPDF, PyInstaller.

## Komendy

```bash
python main.py                                    # uruchomienie
PYTHONPATH=tests python -m unittest tests.test_core tests.test_recipients tests.test_gui_macos
./scripts/build_macos.command                      # build macOS arm64
```

## Struktura

```
app/models.py       # Payment, walidacja, grid helpers
app/amount_words.py # kwota słownie po polsku
app/database.py     # SQLite historia + książka odbiorców
app/pdfgen.py       # generowanie PDF na blankiecie
app/ui.py           # interfejs Qt
assets/template.pdf # oryginalny blankiet A4 (nie modyfikować)
tests/              # testy
docs/               # instrukcja, raporty, stan
```

## Zasady

- `assets/template.pdf` to oryginalny blankiet — nie edytować, nie nadpisywać.
- Dane użytkownika (historia, odbiorcy) w `~/Library/Application Support/Druki Pocztowe/` — nie commitować.
- Testy muszą przechodzić przed zmianą wersji.
- Nie refaktoruj bez potrzeby; najmniejsza zmiana załatwiająca sprawę.
