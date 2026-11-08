# Raport testów — Druki Pocztowe v0.11

Data: 2026-11-08

## Sprawdzone
- 36 testów jednostkowych i Qt zakończyło się powodzeniem przed końcową, kosmetyczną zmianą koloru tła kart.
- Po tej zmianie przebudowano aplikację i uruchomiono ją natywnie na macOS. Sprawdzono przełącznik W/P, widoczność pola rachunku dla P oraz komunikat po zapisaniu odbiorcy na danych testowych.
- Zweryfikowano podpis pakietu `codesign --verify --deep --strict`, architekturę arm64, poprawność archiwów ZIP i brak zmian oryginalnego PDF blankietu.
- Zrzut formularza wykonano na przykładowych, fikcyjnych danych. Dane testowe nie są prawdziwymi osobami ani rachunkami.

## Niezweryfikowane
- Pełny zestaw 36 testów nie był ponownie uruchamiany po kosmetycznej zmianie tła.
- Druk na papierze i zgodność ustawień konkretnej drukarki nie zostały sprawdzone.
- Wersja Windows nie została zbudowana ani sprawdzona.
