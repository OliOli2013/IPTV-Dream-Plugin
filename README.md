# IPTV Dream v6.6.2

IPTV Dream to wtyczka Enigma2 do obsługi źródeł IPTV: M3U z URL, M3U z pliku, Xtream Codes oraz MAC Portal.

## Najważniejsze zmiany w v6.6.2

- Hotfix błędów pobierania M3U: `HTTP 884`, `RemoteDisconnected`, zerwane połączenia.
- Lepsze ponawianie pobierania i bezpieczniejszy fallback do cache.
- Czytelniejsze komunikaty błędów dla użytkownika.
- MAC Portal: dodatkowe warianty handshake i sprawdzanie odpowiedzi niebędących JSON.
- Poprawiony numer wersji w nagłówku wtyczki, menu, WebIF, setup.xml i tłumaczeniach.

## Instalacja z `/tmp`

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-iptvdream_6.6.2_all.ipk
init 4
sleep 2
init 3
```

## Uwaga

Poprawka nie naprawia martwych linków IPTV, wygasłych kont, blokad IP ani portali, które nie są zgodne z MAG/Stalker. Poprawia obsługę błędów, komunikaty, ponawianie i cache.
