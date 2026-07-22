# IPTV Dream v7.0.0

Pełna przebudowa stabilności wtyczki IPTV Dream dla Enigma2.

Wersja 7.0.0 zachowuje aktualne funkcje wtyczki: M3U z URL, M3U z pliku, Xtream Codes, MAC/Stalker/MAG/eStalker, ulubione, WebIF, EPG, pikony, statystyki, aktualizacje oraz eksport do bukietów.

## Najważniejsze zmiany

- przebudowany loader M3U z trybem zgodności z serwerami, które zwracają błędny `Content-Type`,
- poprawiona obsługa odpowiedzi `text/html` — prawidłowa lista M3U nie jest odrzucana tylko przez nagłówek,
- dodatkowe, kontrolowane warianty nagłówków `User-Agent` dla problematycznych paneli IPTV,
- lepsza obsługa `HTTP 884`, `RemoteDisconnected`, timeoutów i zerwanych połączeń,
- awaryjne użycie starego cache tylko wtedy, gdy serwer chwilowo nie odpowiada,
- odświeżony parser M3U: poprawna obsługa `group-title`, `tvg-logo`, `tvg-id`, `EXTGRP` i przecinków w cudzysłowach,
- eksport bukietów pozostaje szybki i nie wykonuje ciężkich operacji EPG/Picon w tym samym kroku,
- stabilniejsze referencje usług IPTV dla EPG i picon,
- bardziej bezpieczny zapis plików bukietów oraz `bouquets.tv`,
- ograniczone timeouty MAC, aby wtyczka nie wisiała godzinami przy źle odpowiadającym portalu,
- utrzymany WebIF na porcie `9999`.

## Instalacja

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-iptvdream_7.0.0_all.ipk
init 4
sleep 2
init 3
```

## Autor

by Paweł Pawełek
