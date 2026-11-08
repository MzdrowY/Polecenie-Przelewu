# Druki Pocztowe v0.11 — instrukcja macOS

## Uruchomienie
1. Pobierz `Druki-Pocztowe-v0.11-macOS-arm64.zip` z folderu v0.11 i rozpakuj archiwum.
2. Przenieś `Druki Pocztowe v0.11.app` do folderu Programy (Aplikacje).
3. Otwórz aplikację dwukrotnym kliknięciem. Przy pierwszym uruchomieniu macOS może wymagać potwierdzenia otwarcia aplikacji pobranej z Internetu.

## Wypełnienie i wydruk
- Wybierz W (wpłata gotówkowa) albo P (polecenie przelewu). Nieaktywna litera jest automatycznie przekreślana na obu odcinkach blankietu.
- Wpisz dane płatnika, odbiorcy, kwotę i tytuł. Książka odbiorców znajduje się pod przyciskiem **Odbiorcy**; **Historia** zawiera zapisane formularze i pozwala ponownie użyć formularza jako szablonu.
- Zaznacz opcjonalnie gwiazdki lub kreskę.
- **Zapisz w historii** zapisuje formularz lokalnie. **Eksportuj PDF** tworzy kompletny dokument A4 z dwoma odcinkami. **Sprawdź wydruk** otwiera powiększony podgląd odcinków i całej strony.
- Drukuj z podglądu lub otwórz wyeksportowany PDF i drukuj w skali 100% / „Rzeczywisty rozmiar”, na papierze A4.

## Dane
Historia i książka odbiorców są przechowywane lokalnie w bazie SQLite pod `~/Library/Application Support/Druki Pocztowe/Druki Pocztowe/historia.sqlite3`. Aplikacja nie synchronizuje tych danych z Google Drive. Eksportowane PDF-y zawierają dane wpisane do formularza.

## Wersja
Pakiet jest zbudowany dla macOS na Apple Silicon (arm64). Aplikacja Windows nie została zbudowana ani sprawdzona. Przed użyciem w placówce sprawdź wydruk na własnej drukarce w skali 100%. Fizyczny wydruk nie został zweryfikowany.
