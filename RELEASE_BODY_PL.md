# IPTV Dream v7.0.0 - pełna przebudowa stabilności

Udostępniono nową wersję **IPTV Dream v7.0.0** dla Enigma2.

Wersja 7.0.0 została przygotowana jako większa przebudowa po zgłoszeniach użytkowników dotyczących ładowania list M3U, problemów MAC/Stalker, eksportu bukietów oraz zgodności z różnymi panelami IPTV.

## Główne zmiany

- ✅ **[PRZEBUDOWANO] Loader M3U**  
  Nowy mechanizm pobierania list M3U jest bardziej tolerancyjny dla serwerów, które zwracają błędny `Content-Type`, np. `text/html`, mimo że treść zawiera poprawną playlistę.

- ✅ **[POPRAWIONO] HTTP 884 / text/html**  
  Wtyczka nie odrzuca już automatycznie odpowiedzi tylko dlatego, że serwer podał zły typ danych. Najpierw sprawdzana jest realna zawartość odpowiedzi.

- ✅ **[DODANO] Tryb zgodności z różnymi panelami IPTV**  
  Dodano kontrolowane warianty nagłówków `User-Agent`, podobnie jak robią to inne wtyczki IPTV, aby poprawić zgodność z dostawcami działającymi np. w XStreamity lub eStalker.

- ✅ **[POPRAWIONO] Parser M3U**  
  Poprawiona obsługa `group-title`, `tvg-logo`, `tvg-id`, `EXTGRP`, przecinków w nazwach oraz błędnie sformatowanych list.

- ✅ **[POPRAWIONO] MAC / Stalker / MAG / eStalker**  
  Ograniczono zbyt długie ładowanie i ustawiono bezpieczniejsze limity stron oraz timeoutów.

- ✅ **[POPRAWIONO] Eksport bukietów**  
  Eksport pozostaje szybki i nie wykonuje ciężkich operacji EPG/Picon w tym samym kroku. Poprawiono też stabilność referencji usług IPTV.

- ✅ **[POPRAWIONO] Bezpieczny zapis plików**  
  Pliki bukietów oraz `bouquets.tv` są zapisywane bezpieczniej, z użyciem plików tymczasowych.

- ✅ **[ZACHOWANO] Funkcje wtyczki**  
  M3U URL, M3U z pliku, Xtream Codes, MAC Portal, ulubione, WebIF, EPG, pikony, statystyki, aktualizacje i eksport bukietów.

## Instalacja

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-iptvdream_7.0.0_all.ipk
init 4
sleep 2
init 3
```

## Ważne

Aktualizacja poprawia stabilność i zgodność wtyczki, ale nie naprawi martwych linków, wygasłych kont, błędnych danych logowania ani serwerów zablokowanych po stronie dostawcy.

**IPTV Dream v7.0.0**  
**by Paweł Pawełek**
