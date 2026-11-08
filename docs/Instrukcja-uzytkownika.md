# Polecenie przelewu — instrukcja dla użytkownika

## Instalacja (macOS)
1. Pobierz plik `Polecenie-przelewu.dmg` z GitHub Releases.
2. Otwórz `.dmg` i przeciągnij „Polecenie przelewu.app” do folderu Programy (Aplikacje).
3. Pierwsze uruchomienie: macOS Gatekeeper może zablokować aplikację (aplikacja nie jest podpisana certyfikatem Apple).
   - Otwórz Ustawienia systemowe → Prywatność i bezpieczeństwo → zezwól na uruchomienie.
   - Albo w Terminalu: `xattr -dr com.apple.quarantine "/Applications/Polecenie przelewu.app"`.

## Uruchomienie
- Kliknij ikonę aplikacji. Okno główne zawiera formularz W (wpłata gotówkowa) / P (polecenie przelewu).

## Wypełnianie formularza
- Wpisz dane odbiorcy, numer rachunku (NRB/IBAN), kwotę (PLN), dane wpłacającego, tytuł.
- Pola mają limity długości (zgodne z blankietem). Długie nazwy skróć.
- Przełącznik „W / P” zmienia aktywne pola (rachunek zleceniodawcy tylko dla P).

## Podgląd i druk
- „Sprawdź wydruk →” pokazuje podgląd A4.
- „Eksportuj PDF” zapisuje kompletny PDF z podkładem.
- „Drukuj A4” drukuje na drukarce systemowej (sprawdź skalę 100%).

## Historia i odbiorcy
- „Zapisz w historii” zapisuje formularz lokalnie.
- „Historia” pozwala wyszukiwać, otwierać, edytować, usuwać.
- „Odbiorcy” — książka adresowa do szybkiego wstawiania danych.

## Dane i backup
- Dane przechowywane lokalnie: `~/Library/Application Support/Polecenie przelewu/` (lub starszy folder `Druki Pocztowe`).
- Plik `historia.sqlite3` — historia i odbiorcy. Zrób kopię tego pliku, aby zabezpieczyć dane.
- Aplikacja nie synchronizuje danych z internetem.

## Rozwiązywanie problemów
- **Brak polskich znaków w PDF:** ustaw zmienną `DRUKI_FONT` na ścieżkę do czcionki TTF/OTF z polskimi znakami.
- **Marginesy drukarki:** sprawdź wydruk próbny w skali 100% przed użyciem w placówce.
- **Błąd zapisu historii:** sprawdź uprawnienia do folderu danych.