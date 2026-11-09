# Polecenie przelewu

Aplikacja do wypełniania, zapisywania i drukowania pocztowych blankietów wpłaty gotówkowej (W) i polecenia przelewu (P). Eksportuje pełną stronę A4 z blankietem i danymi do PDF oraz umożliwia podgląd, druk, korzystanie z historii i książki odbiorców.

Autor: Maciej Zdrowowicz · Kontakt: [mzdrowy@gmail.com](mailto:mzdrowy@gmail.com) · Licencja: [MIT](LICENSE)

## Pobieranie i korzystanie

Pakiety publikujemy w [GitHub Releases](https://github.com/MzdrowY/Polecenie-Przelewu/releases). Na macOS otwórz DMG i przeciągnij aplikację do Programów. Aplikacja nie jest podpisana certyfikatem Apple Developer: przy pierwszym uruchomieniu macOS może wymagać zezwolenia w Ustawieniach systemowych → Prywatność i bezpieczeństwo.

Wypełnij formularz, wybierz W lub P i użyj „Sprawdź wydruk →”. Podgląd pokazuje blankiet, a „Eksportuj PDF” i „Drukuj blankiet” tworzą pełną stronę A4. Historię, odbiorców i kopie znajdziesz w aplikacji. Szczegóły: [instrukcja użytkownika](docs/Instrukcja-uzytkownika.md).

Dane formularzy są przechowywane lokalnie. Sprawdzanie aktualizacji w menu Pomoc łączy się z GitHubem tylko po wybraniu tej funkcji. Eksportowana kopia JSON zawiera dane użytkownika i wymaga bezpiecznego przechowywania.

Fizyczny wydruk i przyjęcie wzoru w placówce nie zostały potwierdzone. Zalecamy wydruk próbny w skali 100% na A4. Pakiet Windows wymaga osobnego sprawdzenia na Windows.

## Uruchomienie ze źródeł

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-macos-lock.txt  # macOS arm64; inne systemy: requirements.txt
python main.py
```

## Testy

```bash
PYTHONPATH=tests python -m unittest discover -s tests
```

Kod jest w `app/`, oryginalny blankiet w `assets/template.pdf`, testy w `tests/`, a dokumentacja w `docs/`.

## Wersja

v0.12.1 — informacje o autorze, zabezpieczenie przywracania kopii oraz poprawka kalibracji.
