# IPTV Dream v6.6.3

IPTV Dream to wtyczka dla Enigma2 do obsługi źródeł M3U, Xtream Codes oraz MAC/Stalker/MAG.

## Najważniejsze zmiany w v6.6.3

- poprawka zgodności z portalami, które działają w eStalker, ale w IPTV Dream zwracały HTML/pustą odpowiedź zamiast JSON,
- dodatkowy warm-up ścieżek `/c/` oraz `/stalker_portal/c/`,
- dodatkowe warianty handshake dla MAC/Stalker/MAG,
- obsługa GET/POST oraz `JsHttpRequest=1-xml`, `1-json` i wariantu bez parametru,
- poprawione nagłówki `Referer`, `Origin`, `Cookie`, MAG250/MAG254,
- fallback LIVE przez `get_ordered_list`, gdy portal nie obsługuje poprawnie `get_all_channels`,
- poprawione komunikaty błędów i numer wersji.

## Ważne

Aktualizacja nie naprawia nieaktywnych kont, martwych linków, błędnego MAC, złego portu ani blokad po stronie dostawcy. Poprawia zgodność sposobu połączenia z wybranymi portalami MAC/Stalker/MAG.

## Instalacja ręczna

Wrzuć plik IPK do `/tmp`, a następnie wykonaj:

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-iptvdream_6.6.3_all.ipk
init 4
sleep 2
init 3
```

## Autor

by Paweł Pawełek
