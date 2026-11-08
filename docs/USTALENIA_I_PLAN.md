# Polecenie przelewu — ustalenia i plan projektu

**Źródło:** Google Drive `ChatGPT/AGENT-HUB/20-KOD/Druki Pocztowe — aplikacja/USTALENIA_I_PLAN.md`  
**Data oryginału:** 2026-11-08

## Zatwierdzone decyzje użytkownika

1. **Platformy:** macOS i Windows.
2. **Język programowania:** wybór należy do wykonawcy; interfejs po polsku.
3. **Dane:** przechowywane lokalnie na urządzeniu; bez synchronizacji w chmurze.
4. **Wydruk:** kompletny druk wraz z podkładem na pustej kartce A4.
5. **Pierwotna potrzeba funkcjonalna:** wypełnianie druku, zapamiętywanie wcześniejszych formularzy, powrót do zapisów, ponowny wydruk.

## Rekomendacja architektury (zrealizowana)

- Python 3 + PySide6 (Qt Widgets) — graficzny interfejs na macOS i Windows z jednej bazy kodu.
- SQLite — lokalna baza zapisanych formularzy oraz opcjonalnego katalogu odbiorców; bez danych w usługach sieciowych.
- PyMuPDF (fitz) — nanoszenie pól na oryginalny podkład PDF i eksport kompletnego PDF.
- PyInstaller — osobne paczki dla macOS i Windows (build na każdym systemie docelowym).

## Kryteria akceptacji wersji 1.0

- Użytkownik wpisuje dane w polskich polach i widzi podgląd gotowej strony.
- Ten sam zestaw danych wypełnia obie części przesłanego druku.
- Program zapisuje rekord lokalnie, można go ponownie otworzyć i edytować.
- Eksportowany PDF zawiera pełną stronę z drukiem i danymi, gotową do wydruku na A4 w skali 100%.
- Nie ma ukrytego przesyłania danych odbiorców/wpłacających do internetu.
- Osobne pakiety dla macOS i Windows, po ich zbudowaniu i przetestowaniu na danych systemach.

## Ważne ograniczenia

- Pole „Nazwa odbiorcy” i „Nazwa odbiorcy cd.” na blankiecie mają po 27 kratek; dane należy skrócić do długości kratki. Analogicznie dla wpłacającego. Tytuł przelewu ma dwa wiersze.
- Program wymaga lokalnie dostępnej czcionki TTF/OTF obejmującej polskie znaki. Zazwyczaj znajdzie Arial na macOS/Windows. Można podać ścieżkę zmienną `DRUKI_FONT`.
- **Przed pierwszym użyciem w placówce** sprawdź wydruk próbny w skali 100%, poziom marginesów drukarki i to, czy poczta/bank akceptuje konkretny wzór. Plik PDF użytkownika ma metadane pierwotnego utworzenia z 2013 r., modyfikacja z 2024 r.; samo pochodzenie/aktualna zgodność druku nie zostały urzędowo potwierdzone.
- SQLite nie jest szyfrowany. Nie zapisuj danych na współdzielonym komputerze bez odpowiednich zabezpieczeń systemu.
- Aplikacja **nie jest podpisana** certyfikatem Apple Developer (unsigned).