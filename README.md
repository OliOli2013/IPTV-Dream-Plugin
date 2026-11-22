# IPTV Dream 9.0.0

Wtyczka IPTV dla Enigma2 z Pythonem 3. M3U/M3U8, Xtream i MAC/Stalker, eksport bukietów, EPGImport, pikony i WebIF.

## Co zmieniono

- Lokalne intro IPTV Dream / AIO Hub Enigma 2 z animowanym paskiem (około 2,4 s), pomijane przez OK. EXIT zamyka. W Zarządzaniu można je wyłączyć. Nie przerywa telewizji i nie wymaga dekodera wideo.
- Przeglądarka multimediów: odtwarzanie LIVE i VOD, wyszukiwanie po nazwie i grupie (także bez polskich znaków), filtr Wszystko/LIVE/VOD, strony po 100 pozycji, ulubione i ostatnio uruchamiane pozycje.
- Odtwarzacz korzysta z kontrolek obrazu systemowego (audio, napisy, przewijanie, jeśli strumień to obsługuje). STOP/EXIT wraca do IPTV Dream. Obsłużono różne sygnatury MoviePlayer w OpenATV i OpenPLi.
- Wyniki i postęp należą do konkretnego zadania. Anulowany lub zamknięty ekran nie przyjmuje spóźnionego wyniku. Aktualizacje widżetów odbywają się w głównym wątku.
- Pobieranie i parsowanie Xtream, eksport bukietów oraz instalacja źródeł EPG pracują w tle. Zapisów i podmiany wersji nie przerywa się w połowie.
- Parser zachowuje User-Agent/Referer z EXTVLCOPT i nagłówki KODIPROP, rozpoznaje pojedyncze manifesty HLS i względne adresy strumieni. Odtwarzacz i eksport używają wspólnego budowania referencji.
- Ręczne odświeżenie nie ukrywa awarii źródła starym cache. Zwykłe otwarcie może użyć kopii awaryjnej i pokazuje komunikat.
- Odczyt konfiguracji nie zapisuje jej ponownie. Nowe zapisy ustawień, ulubionych i ostatnich pozycji są atomowe i mają uprawnienia 0600. Dodawanie całej listy do ulubionych wykonuje jeden zapis.
- Główne ekrany dopasowują się do rozdzielczości pulpitu. Dodano diagnostykę Python/GUI/ServiceApp/exteplayer3/EPGImport/WebIF.
- Usunięto 9 nieużywanych, historycznych modułów. IPK, DEB, instalator i updater korzystają ze wspólnego runtime.json. Pliki strony i narzędzia developerskie nie trafiają do tunera.

## Obsługa

Po wczytaniu listy wybierz **Odtwarzacz / Szukaj / LIVE / VOD** albo grupę kanałów.

| Klawisz | Działanie w przeglądarce |
|---|---|
| OK | Odtwarzanie wybranej pozycji |
| Zielony | Wyszukiwanie; puste hasło usuwa wyszukiwanie |
| Żółty | Zmiana filtra Wszystko / LIVE / VOD |
| Niebieski | Dodanie pozycji do ulubionych IPTV Dream |
| Lewo / prawo | Poprzednia / następna strona |
| Czerwony / EXIT | Powrót |

**Zarządzanie** zawiera intro, diagnostykę i ostatnio odtwarzane. Historia zapisuje uruchomione pozycje; nie jest potwierdzeniem, że dostawca dostarczył obraz. Kod nie pobiera zewnętrznych katalogów filmów ani płatnych treści.

Dotychczasowe tłumaczenia: PL/EN/DE/ES/AR/RU. Nowe ekrany mają PL i angielski jako język zastępczy.

## Wymagania

Enigma2 z Pythonem 3 (składnia sprawdzona dla 3.8+), requests oraz twisted-core. WebIF wymaga twisted-web; skalowanie piconów może korzystać z Pillow. EPGImport jest dodatkiem opcjonalnym.

Domyślny typ serwisu **4097** korzysta z odtwarzacza image. **5002** wymaga ServiceApp i exteplayer3. Obsługiwane kodeki, przewijanie i działanie źródła zależą również od systemu, tunera i dostawcy. Enigma2/Python 2 nie jest obsługiwany.

## Instalacja

Wgraj odpowiednią paczkę do `/tmp` tunera.

IPK:
```sh
opkg install /tmp/enigma2-plugin-extensions-iptvdream_9.0.0_all.ipk
```

DEB:
```sh
dpkg -i /tmp/enigma2-plugin-extensions-iptvdream_9.0.0_all.deb
```

Następnie zrestartuj GUI z menu odbiornika. Jeżeli system zgłosi brak zależności, doinstaluj je z jego własnego feedu. Nie wymuszaj ignorowania zależności.

Instalator źródłowy po opublikowaniu zmian:
```sh
wget -qO /tmp/iptvdream-installer.sh https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh
sh /tmp/iptvdream-installer.sh --no-restart
```

Konfiguracja i zapisane portale pozostają w `/etc/enigma2`; paczka nie zawiera ani nie nadpisuje danych użytkownika.

## Budowanie i sprawdzanie

```sh
python3 -m unittest discover -s tests -v
python3 tests/receiver_smoke.py
python3 build_packages.py
```

IPK i DEB zawierają identyczny runtime. Sumy SHA256 znajdują się przy paczkach. Testy komputerowe obejmują logikę, eksport i ekrany z atrapami Enigma2; nie zastępują testu dekodera, pilota ani połączenia z rzeczywistym dostawcą na tunerze.

## Autor i licencja

Paweł Pawełek — GPL-3.0.
Repozytorium: https://github.com/OliOli2013/IPTV-Dream-Plugin
