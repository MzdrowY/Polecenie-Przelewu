# Polecenie przelewu

Aplikacja desktopowa (PySide6 + PyMuPDF) do wypełniania i drukowania
pocztowych blankietów wpłaty gotówkowej (W) i polecenia przelewu (P)
na oryginalnym podkładzie A4.

## Uruchomienie ze źródeł

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-macos-lock.txt   # macOS arm64
# lub requirements.txt na innych platformach
python main.py
```

## Testy

```bash
PYTHONPATH=tests python -m unittest tests.test_core tests.test_recipients tests.test_gui_macos
```

## Struktura

```
app/        # kod aplikacji (models, database, pdfgen, ui, amount_words)
assets/     # template.pdf — oryginalny blankiet A4
tests/      # testy jednostkowe i GUI
scripts/    # build_macos.command, build_windows.ps1
docs/       # instrukcja, raport testów, stan projektu
```

## Podpis i dystrybucja

Aplikacja **nie jest podpisana** certyfikatem Apple Developer (unsigned).
Na macOS Gatekeeper może zablokować pierwsze uruchomienie — zezwól w
Ustawienia systemowe → Prywatność i bezpieczeństwo, albo uruchom z terminala:
`xattr -dr com.apple.quarantine "Polecenie przelewu.app"`.

## Licencja

MIT — szczegóły w pliku `LICENSE`.

## Wersja

v0.11 — macOS Apple Silicon (arm64). Windows niezbuwowane.
