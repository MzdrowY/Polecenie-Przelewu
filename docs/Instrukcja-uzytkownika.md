# Polecenie przelewu — instrukcja użytkownika

## Instalacja i uruchomienie

Pobierz pakiet z [GitHub Releases](https://github.com/MzdrowY/Polecenie-Przelewu/releases). Na macOS otwórz DMG i przeciągnij aplikację do Programów. Aplikacja nie ma podpisu Apple Developer: jeśli system zablokuje pierwsze uruchomienie, zezwól na nie w Ustawieniach systemowych → Prywatność i bezpieczeństwo. Pakiet Windows wymaga sprawdzenia na Windows.

## Formularz i podgląd

Wybierz W (wpłata) albo P (przelew); dla przelewu podaj również rachunek zleceniodawcy. Wpisz numer rachunku odbiorcy, kwotę oraz pozostałe dane, po czym kliknij „Sprawdź wydruk →”. Program sprawdza numer rachunku i kwotę. Dłuższe napisy dopasowuje do dostępnej rubryki.

Podgląd pokazuje powiększony odcinek albo całą stronę. „Eksportuj PDF” zapisuje pełny blankiet z danymi; „Drukuj blankiet” przekazuje go do drukarki. Kalibracja X/Y przesuwa nadruk względem blankietu. Wybierz A4 i skalę 100%. Wydruk fizyczny i przyjęcie wzoru w placówce nie zostały potwierdzone — sprawdź wydruk próbny przed użyciem.

## Historia, odbiorcy i kopie

„Zapisz w historii” zapisuje formularz na tym komputerze. Przycisk „Historia” pozwala go ponownie otworzyć, edytować lub powielić, a „Odbiorcy” otwiera lokalną książkę odbiorców.

W menu Plik możesz wyeksportować kopię historii i odbiorców do JSON. Plik zawiera dane osobowe i rachunki: przechowuj go w bezpiecznym miejscu. Import zastępuje obecną historię i odbiorców po potwierdzeniu; przed przywróceniem program zapisuje kopię dotychczasowej bazy i pokazuje jej ścieżkę. Baza na macOS znajduje się w katalogu danych aplikacji, w starszych instalacjach w `~/Library/Application Support/Druki Pocztowe/`.

Dane nie są synchronizowane z internetem. Opcja „Sprawdź aktualizacje” w menu Pomoc łączy się z GitHubem po jej wybraniu.

## Informacje i pomoc

Autor: Maciej Zdrowowicz, [mzdrowy@gmail.com](mailto:mzdrowy@gmail.com). Repozytorium: [GitHub](https://github.com/MzdrowY/Polecenie-Przelewu). Licencja MIT. Wersję oraz dane autora znajdziesz również w menu Pomoc → O programie.
