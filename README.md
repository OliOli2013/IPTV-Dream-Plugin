# IPTV Dream v6.6.7

Hotfix przywracający szybki eksport bukietów po problemach z wersją 6.6.6.

## Zmiany

- szybki eksport bukietów bez ciężkiego generowania EPG/Picon w tym samym kroku,
- brak paska postępu stojącego na 0% przy eksporcie,
- eksport wybranych bukietów zapisuje pliki bukietów i odświeża listę kanałów,
- EPG i pikony pozostają jako osobne funkcje wtyczki,
- zachowana poprawka GSOD przy dodawaniu całości do ulubionych,
- zachowane poprawki MAC/Stalker/eStalker.

## Instalacja

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-iptvdream_6.6.7_all.ipk
init 4
sleep 2
init 3
```

by Paweł Pawełek
