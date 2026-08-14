# IPTV Dream v8.0.0

Duża aktualizacja IPTV Dream dla Enigma2, łącząca poprawki stabilności z audytu 7.0.1 z przebudową nazw kanałów/bukietów i odświeżeniem interfejsu.

## Najważniejsze zmiany

- **Bukiety mają teraz czyste nazwy grup** — np. `MAGENTA HD`, bez nazwy playlisty, loginu czy portalu przed nazwą.
- **Usuwane są techniczne prefiksy krajowe** z kanałów i grup, np.:
  - `|DE| HOPE TV` → `HOPE TV`
  - `[PL] TVP 1 HD` → `TVP 1 HD`
  - `UK - BBC ONE FHD` → `BBC ONE FHD`
- Czyste nazwy poprawiają dopasowanie **EPG i piconów**, a oryginalny `tvg-id` nadal ma pierwszeństwo.
- Widoczne oznaczenia jakości `HD/FHD/UHD/4K` pozostają w nazwach kanałów i bukietów.
- Poprawiono normalizację nazw m.in. dla **CANAL+**, **TV PULS**, **CHANNEL 4** i **KANAL D**.
- Nowa szata graficzna w stylu **AIO Panel**: ciemny granat, cyan/green, nowe logo i czytelniejszy układ.
- Po zaznaczeniu funkcji wtyczka od razu pokazuje **co dana opcja robi i co należy nacisnąć**.
- Podpowiedzi dostępne są w **PL / EN / DE / ES / AR / RU**.
- Ekran główny został uporządkowany: dodano **kod QR i stronę projektu** `https://olioli2013.github.io/aio-iptv-projekt/`.
- Uproszczono pozycję WebIF w menu; pełny adres `IP:9999` jest pokazywany w panelu informacji.
- Naprawiono dodatkowo nawigację w podglądzie grup playlisty.

## Zachowane poprawki audytowe

Wersja 8.0.0 zawiera również poprawki stabilności przygotowane wcześniej: parser M3U, bezpieczne retry i timeouty, właściwy cache, eksport 4097/5002, poprawne kodowanie URL w referencji Enigma2, atomowe zapisy, poprawki WebIF/EPG/statystyk oraz updater z walidacją i rollbackiem.

## Instalacja

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-iptvdream_8.0.0_all.ipk
init 4
sleep 2
init 3
```

Lub bezpośrednio z GitHuba:

```sh
wget -qO - https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh | /bin/sh
```

**Autor:** Paweł Pawełek  
**Strona projektu:** `https://olioli2013.github.io/aio-iptv-projekt/`
