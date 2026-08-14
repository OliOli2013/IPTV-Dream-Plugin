# IPTV Dream v8.0.0

**IPTV Dream** to wtyczka IPTV dla odbiorników **Enigma2 / Python 3**. Obsługuje listy M3U/M3U8, Xtream Codes, portale MAC/Stalker/MAG, eksport do bukietów Enigma2, EPGImport, pikony, ulubione, statystyki, WebIF i aktualizacje online.

## Najważniejsze zmiany w 8.0.0

- **Czyste nazwy bukietów** — widoczna nazwa bukietu jest teraz dokładnie nazwą grupy z playlisty, np. `MAGENTA HD`, a nie `MAC-line... - MAGENTA HD`.
- **Usuwanie technicznych przedrostków państw/języków** z nazw grup i kanałów, np. `|DE| HOPE TV` → `HOPE TV`, `[PL] TVP 1 HD` → `TVP 1 HD`, `UK - BBC ONE FHD` → `BBC ONE FHD`.
- Oczyszczone nazwy są używane również przy dopasowaniu **piconów i EPG**, przy zachowaniu oryginalnego `tvg-id`.
- Prefiksy jakości `HD`, `FHD`, `UHD`, `4K` pozostają w **widocznej nazwie kanału/bukietu**; osobne warianty bez jakości są używane tylko pomocniczo przy dopasowaniu EPG/piconów.
- Poprawiono normalizację kanałów takich jak **CANAL+**, **TV PULS**, **CHANNEL 4** i **KANAL D** — słowa będące częścią prawdziwej nazwy kanału nie są już traktowane jako szum.
- Nowa szata graficzna inspirowana **AIO Panel**: ciemny granat, akcenty cyan/green, czytelniejsze sekcje i nowe logo IPTV Dream.
- Po zmianie zaznaczenia w menu panel informacji automatycznie pokazuje **co robi funkcja i co nacisnąć**.
- Kontekstowe podpowiedzi są dostępne w językach: **PL / EN / DE / ES / AR / RU**.
- Z ekranu głównego usunięto poprzedni odnośnik społecznościowy. Dodano **kod QR i adres strony projektu**:
  `https://olioli2013.github.io/aio-iptv-projekt/`
- WebIF pozostaje na porcie **9999**, ale jego pełny adres jest pokazywany w panelu pomocy zamiast zaśmiecać pozycję menu.
- Zachowano wszystkie poprawki stabilności z audytu 7.0.1: parser M3U, retry/timeout, cache, bezpieczny updater, poprawny eksport 4097/5002, kodowanie URL w service reference, atomowe zapisy, poprawki WebIF/EPG/statystyk.

## Funkcje

- M3U/M3U8 z URL
- M3U/M3U8 z pliku
- Xtream Codes: LIVE / VOD / ALL / ADULT
- MAC / Stalker / MAG / eStalker
- grupy i ulubione
- eksport do bukietów Enigma2
- typ serwisu 4097 / 5002
- EPGImport / XMLTV
- pobieranie i mapowanie piconów
- statystyki i historia
- log diagnostyczny i tryb debug
- WebIF `http://IP_TUNERA:9999`
- aktualizacja bezpośrednio z GitHuba z walidacją i rollbackiem

## Instalacja IPK

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-iptvdream_8.0.0_all.ipk
init 4
sleep 2
init 3
```

## Instalacja / aktualizacja bezpośrednio z GitHuba

```sh
wget -qO - https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh | /bin/sh
```

Instalator najpierw pobiera i waliduje źródła. Dopiero po poprawnym sprawdzeniu wykonuje backup i podmianę wtyczki; w razie błędu przywraca poprzednią wersję.

## Strona projektu

`https://olioli2013.github.io/aio-iptv-projekt/`

## Repozytorium

`https://github.com/OliOli2013/IPTV-Dream-Plugin`

## Autor

**Paweł Pawełek**

Licencja: **GPL-3.0**

### Finalna korekta interfejsu 8.0.0

Finalny build 8.0.0 zawiera przebudowany natywny skin Enigma2. Kod QR na ekranie głównym jest skalowany jako całość i prowadzi do `https://olioli2013.github.io/aio-iptv-projekt/`. Klawisz `0` albo pozycja **Strona projektu / QR** otwiera dodatkowy ekran z dużym, czytelnym kodem QR. Nagłówek został uproszczony, a pomoc dla głównych funkcji jest wyświetlana kontekstowo po zmianie zaznaczenia.
