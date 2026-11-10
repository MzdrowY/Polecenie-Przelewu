# Polecenie przelewu — instrukcja użytkownika

## Instalacja i uruchomienie

Pobierz pakiet z [GitHub Releases](https://github.com/MzdrowY/Polecenie-Przelewu/releases). Na macOS otwórz DMG i przeciągnij aplikację do Programów. Aplikacja nie ma podpisu Apple Developer: jeśli system zablokuje pierwsze uruchomienie, zezwól na nie w Ustawieniach systemowych → Prywatność i bezpieczeństwo. Pakiet Windows wymaga sprawdzenia na Windows.

## Formularz i podgląd

Wybierz W (wpłata) albo P (przelew). Dla przelewu podaj również rachunek zleceniodawcy. Wpisz numer rachunku odbiorcy, kwotę oraz pozostałe dane, po czym kliknij „Sprawdź wydruk →”. Program sprawdza numer rachunku i kwotę. Nazwa i adres odbiorcy oraz nazwa i adres zleceniodawcy tworzą na blankiecie jedno pole złożone z dwóch wierszy. Jeśli wpiszesz nazwę w pierwszym polu, a adres w drugim, program zachowa ten podział: nazwa u góry, adres pod spodem. Możesz też wpisać całość w pierwszym polu i zostawić drugie puste — wtedy program podzieli tekst, wypełniając pierwszy wiersz do końca i przenosząc resztę do drugiego (również w środku wyrazu lub kodu pocztowego). Tekst nie jest ucinany; zbyt długi wiersz zostaje ściśnięty, a program ostrzega przed wydrukiem, gdy może być nieczytelny.

Podgląd pokazuje powiększony odcinek albo całą stronę. „Eksportuj PDF” zapisuje pełny blankiet z danymi; „Drukuj blankiet” przekazuje go do drukarki. Kalibracja X/Y przesuwa nadruk względem blankietu. Wybierz A4 i skalę 100%. Wydruk fizyczny i przyjęcie wzoru w placówce nie zostały potwierdzone — sprawdź wydruk próbny przed użyciem.

## Historia, odbiorcy, nadawcy i kopie

„Zapisz w historii” zapisuje formularz na tym komputerze. Przycisk „Historia” pozwala go ponownie otworzyć, edytować lub powielić, a „Odbiorcy” otwiera lokalną książkę odbiorców.

Aby zapisać osobę prywatną lub firmę, wpisz jej dane w polach wpłacającego, otwórz „Nadawcy” i wybierz „Zapamiętaj z formularza”. Przy kolejnym blankiecie wybierz zapis na liście i kliknij „Wstaw do formularza”. W trybie przelewu możesz też zapisać rachunek zleceniodawcy.

W menu Plik możesz wyeksportować kopię historii, odbiorców i nadawców do JSON. Plik zawiera dane osobowe i rachunki: przechowuj go w bezpiecznym miejscu. Import zastępuje obecną historię i odbiorców po potwierdzeniu oraz listę nadawców, jeśli kopia ją zawiera; przed przywróceniem program zapisuje kopię dotychczasowej bazy i pokazuje jej ścieżkę. Baza na macOS znajduje się w katalogu danych aplikacji, w starszych instalacjach w `~/Library/Application Support/Druki Pocztowe/`.

Dane nie są synchronizowane z internetem. Opcja „Sprawdź aktualizacje” w menu Pomoc łączy się z GitHubem po jej wybraniu.

## Informacje i pomoc

Autor: Maciej Zdrowowicz, [mzdrowy@gmail.com](mailto:mzdrowy@gmail.com). Repozytorium: [GitHub](https://github.com/MzdrowY/Polecenie-Przelewu). Licencja MIT. Wersję oraz dane autora znajdziesz również w menu Pomoc → O programie.
