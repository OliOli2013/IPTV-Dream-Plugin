# IPTV Dream v6.6.1

IPTV Dream to wtyczka IPTV dla Enigma2 obsługująca M3U, Xtream Codes, MAC/Stalker, eksport do bukietów, EPG Import, pikony oraz WebIF na porcie 9999.

## Najważniejsze zmiany w v6.6.1

- Nowy mechanizm EPG i piconów oparty na rozwiązaniach zgodnych z TvMad: normalizacja nazw kanałów, aliasy i wiele wariantów identyfikatorów.
- Generowanie plików EPG Import:
  - `/etc/epgimport/iptvdream.channels.xml`
  - `/etc/epgimport/iptvdream.sources.xml`
- Lepsze przypisywanie piconów z katalogów:
  - `/usr/share/enigma2/picon`
  - `/picon`
  - `/picon/logos`
  - `/media/hdd/picon`
  - `/media/usb/picon`
  - `/media/mmc/picon`
  - `/etc/enigma2/picon`
- Dodane języki: Polski, English, Deutsch, Español, العربية.
- Wybór języka z menu wtyczki oraz automatyczne wykrywanie języka systemowego.
- Fallback do języka English, jeśli język systemu nie jest obsługiwany przez wtyczkę.
- Poprawione pobieranie kanałów dla dorosłych z MAC/Stalker: dodano tryb `ADULT / XXX`.
- WebIF obsługuje tryb MAC `ADULT / XXX` oraz nowe języki.
- Dodane logo Paweł Pawełek w ekranie wtyczki i WebIF.

## Instalacja IPK

```sh
opkg install /tmp/enigma2-plugin-extensions-iptvdream_6.6.1_all.ipk
killall -9 enigma2
```

## Odinstalowanie starej wersji i czysta instalacja

```sh
opkg remove enigma2-plugin-extensions-iptvdream
opkg install /tmp/enigma2-plugin-extensions-iptvdream_6.6.1_all.ipk
killall -9 enigma2
```

## Autor / wsparcie

Paweł Pawełek  
Kontakt: aio-iptv@wp.pl
