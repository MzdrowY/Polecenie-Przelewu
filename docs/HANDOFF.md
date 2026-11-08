# HANDOFF — Polecenie przelewu (daw. Druki Pocztowe)

**Źródło:** Google Drive `ChatGPT/AGENT-HUB/20-KOD/Druki Pocztowe — aplikacja/HANDOFF.md`  
**Data oryginału:** 2026-11-08  
**Status oryginału:** implementacja źródłowa prototypu, backend PDF i SQLite sprawdzone; GUI i wersje instalacyjne **nieprzetestowane**.

## Zatwierdzone przez użytkownika

- macOS oraz Windows; interfejs po polsku.
- Wybór języka po stronie wykonawcy: Python + PySide6 (Qt).
- Zapisywanie danych tylko na lokalnym komputerze.
- Kompletny wydruk A4 na czystej kartce, wykorzystujący dokładnie dołączony PDF.
- Historia dokumentów i ponowne użycie.

## Co istnieje i działa w testach

- Moduł `app/models.py` — waliduje NRB / PL IBAN, kwotę, rozmiar pól.
- `app/pdfgen.py` — uzupełnia szablon PDF (dwa odcinki) z zachowaniem grafiki, czcionek Unicode i rozmiaru A4.
- `app/database.py` — przechowuje lokalną historię w SQLite; wyszukiwanie, aktualizacja, usuwanie.
- `app/ui.py` — okno Qt z edytorem, listą historii, podglądem, eksportem PDF i poleceniem druku.
- `tests/test_core.py` — testy funkcji backendowych.
- `docs/` — wygenerowany wydruk kontrolny z fikcyjnymi danymi.

## Nieweryfikowane / przed wydaniem

1. **GUI PySide6**: w dostępnym środowisku nie było pakietu PySide6; nie uruchomiono okna na żadnej platformie w tej sesji (obecnie zależności instalowane przez requirements).
2. **Druk fizyczny**: nie sprawdzono realnej drukarki, korekcji marginesów oraz dopuszczenia wydruku w placówce.
3. **Instalator `.app` / `.exe`**: wymagany build na macOS i Windows; **aplikacja nie jest podpisana** certyfikatem Apple Developer.
4. **Dostępność formularza**: źródłowy PDF ma metadane 2013 / 2024; aktualność urzędowa nie jest potwierdzona.
5. **Dodatkowa walidacja**: znaki narodowe i długości są sprawdzane, ale należy przetestować długie dane rzeczywiste i użycie na drukarkach.

## Następne zadania

1. Zainstaluj Python 3.12, `pip install -r requirements-dev.txt` (macOS) / requirements.txt; uruchom testy.
2. Uruchom `python main.py`, przetestuj GUI, zapis lokalny, ponowne wczytanie, eksport i usuwanie.
3. Porównaj PDF z wydrukiem papierowym 100% (A4); skoryguj pozycje w `app/pdfgen.py`, jeśli konieczne.
4. Zbuduj PyInstaller osobno na macOS i Windows, przetestuj na czystym koncie użytkownika.
5. Po faktycznym teście dopisz protokół z datą, nazwą systemu, wynikiem i logiem.

## Zasady danych

Nie zapisuj prawdziwych kont, adresów i historii wpłat w folderze Drive. Współdzielone są wyłącznie kod, pusty blankiet i dokumenty testowe z fikcyjnymi danymi. SQLite przechowuje realne dane wyłącznie lokalnie.