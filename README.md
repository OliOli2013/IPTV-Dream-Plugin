# IPTV Dream v6.6.2

IPTV Dream to wtyczka IPTV dla Enigma2 obsługująca M3U, Xtream Codes, MAC/Stalker, eksport do bukietów, EPG Import, pikony oraz WebIF na porcie 9999.

## Najważniejsze zmiany w v6.6.2

- Hotfix dla błędów pobierania M3U: `NET-HTTP-884`, `RemoteDisconnected`, `Connection aborted`, `Remote end closed connection`.
- Warstwa sieciowa używa bezpieczniejszych nagłówków dla paneli IPTV, między innymi `Connection: close`, aby ograniczyć zrywanie połączeń przez serwer.
- Dodano czytelniejsze komunikaty błędów dla HTTP 884, 401/403, 404, timeoutów, przerwanych połączeń oraz odpowiedzi HTML zamiast M3U.
- Dodano awaryjne użycie starego cache M3U, gdy serwer chwilowo zrywa pobieranie albo zwraca błędną odpowiedź.
- MAC/Stalker: poprawiono obsługę odpowiedzi nie-JSON, HTML/pustych odpowiedzi i zamykania połączenia przez portal.
- MAC/Stalker: handshake próbuje więcej wariantów `JsHttpRequest`: `1-xml`, `1-json` oraz wariant bez tego parametru.
- MAC/Stalker: dodano próby połączenia przez przeciwny schemat HTTP/HTTPS, gdy portal przekierowuje albo odpowiada tylko na drugim wariancie.

## Instalacja IPK

```sh
opkg install /tmp/enigma2-plugin-extensions-iptvdream_6.6.2_all.ipk
init 4
sleep 2
init 3
```

## Odinstalowanie starej wersji i czysta instalacja

```sh
opkg remove enigma2-plugin-extensions-iptvdream
opkg install /tmp/enigma2-plugin-extensions-iptvdream_6.6.2_all.ipk
init 4
sleep 2
init 3
```

## Czyszczenie cache do testów

```sh
rm -rf /tmp/iptvdream_cache /tmp/iptvdream_v6_cache
```

## Autor / wsparcie

Paweł Pawełek  
Kontakt: aio-iptv@wp.pl
