# Raport testów — Polecenie przelewu (2026-11-08)

## Środowisko
- macOS arm64 (Apple Silicon)
- Python 3.12.16 (.venv, requirements-macos-lock.txt)
- PySide6 6.12.0, PyMuPDF 1.28.2
- QT_QPA_PLATFORM=offscreen

## Wynik
- `tests.test_core`: OK
- `tests.test_recipients`: OK
- `tests.test_gui_macos`: OK
- **Łącznie: 36 testów, 0 błędów, 0 porażek.**

## Uwagi
- Testy uruchomione po przemianowaniu aplikacji i dodaniu ikony.
- Druk fizyczny na papierze nie był testowany (odłożone).
- Wersja Windows nie była testowana (odłożone).