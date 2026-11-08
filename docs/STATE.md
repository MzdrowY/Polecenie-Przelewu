# STAN ŚRODOWISKA — 2026-11-08

## Cel
Trwałe, użyteczne miejsce pracy ChatGPT, możliwe do odnalezienia przez agentów takich jak Codex i OpenCode po przyznaniu im osobnego dostępu do Google Drive.

## Zweryfikowano
- AGENT-HUB działa jako wspólna przestrzeń plików Google Drive; nie jest serwerem ani automatycznym synchronizatorem.
- W `20-KOD` znajduje się projekt [Druki Pocztowe](https://drive.google.com/drive/folders/1WMoPD5DJIY3WLE_FcaJjZqxZ3XKnjefq).
- Aktualna wersja [v0.11](https://drive.google.com/drive/folders/1LqQIN29JXf_2-Qs5dxMCc5fDmVkTyKRk) zawiera pakiet macOS arm64, źródła, instrukcję, raport testów i zrzut formularza. Wersje v0.5 i v0.6 zachowano.
- Aplikację v0.11 uruchomiono na macOS; sprawdzono W/P, pole rachunku i zapis odbiorcy na danych fikcyjnych.

## Ograniczenia
- Nie ma automatycznej synchronizacji z MacBookiem, lokalną wiki, serwerem domowym ani Git.
- Nie uruchomiono CI ani automatycznego wdrażania.
- Fizyczny wydruk oraz Windows pozostają niezweryfikowane; pełnych 36 testów nie powtórzono po końcowej zmianie kosmetycznej.

## Sesja następnego agenta
1. Przeczytaj `AGENTS.md`, `README.md` i `00-START/PROJECTS.json`.
2. Sprawdź folder projektu i jego aktualny dokument statusu bezpośrednio na Drive.
3. Wykonuj pracę tylko w zleconym zakresie i zanotuj istotne zmiany w `90-AUDYT/CHANGELOG.md`.
