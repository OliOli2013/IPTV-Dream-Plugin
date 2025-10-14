# Wtyczka IPTV Dream v2.2

![Ikona wtyczki IPTV Dream](plugin.png)

Lekka i szybka wtyczka do list IPTV dla dekoderów z oprogramowaniem Enigma2 (Python 3). Wersja 2.2 wprowadza rewolucyjną obsługę plików konfiguracyjnych, eliminując potrzebę ręcznego wpisywania danych z pilota!

---

## Nowości w v2.2 - Koniec z wpisywaniem!

Od teraz możesz przygotować proste pliki `.json` na komputerze, wgrać je na dekoder i wczytać wszystkie dane jednym kliknięciem.

### 1. Własne M3U (Przycisk 5)
Zapisz swoją kolekcję linków M3U w jednym miejscu.
* **Plik:** `/etc/enigma2/iptvdream_mylinks.json`
* **Format:**
    ```json
    [
      {"name": "Polska HD",  "url": "http://HOST:PORT/get.php?username=XXX&password=YYY&type=m3u_plus&output=ts"},
      {"name": "Sport 4K",   "url": "http://HOST:PORT/sport.m3u"},
      {"name": "VOD Filmy",  "url": "http://HOST:PORT/vod.m3u"}
    ]
    ```

### 2. MAC Portal (Przycisk 4)
Automatyczne wczytywanie danych do portalu MAC.
* **Plik:** `/etc/enigma2/iptvdream_mac.json`
* **Format:**
    ```json
    {
      "host": "http://HOST:PORT",
      "mac":  "00:1A:79:XX:YY:ZZ"
    }
    ```

### 3. Xtream (Przycisk 3)
Błyskawiczne logowanie do konta Xtream bez użycia klawiatury.
* **Plik:** `/etc/enigma2/iptvdream_xtream.json`
* **Format:**
    ```json
    {"host":"http://HOST:PORT","user":"USERNAME","pass":"PASSWORD"}
    ```

### Podsumowanie metod wprowadzania danych

| Przycisk | Nazwa opcji | Plik na STB | Treść / Akcja |
| :---: | :--- | :--- | :--- |
| **5** | Własne M3U | `/etc/enigma2/iptvdream_mylinks.json` | JSON z listą nazw i linków |
| **4** | MAC Portal | `/etc/enigma2/iptvdream_mac.json` | JSON z hostem i adresem MAC |
| **3** | Xtream | `/etc/enigma2/iptvdream_xtream.json` | JSON z hostem, userem i hasłem |
| **2** | M3U plik | Dowolny plik `.m3u` | Wgraj plik i wybierz go z listy |
| **1** | M3U URL | *Brak* | Wklej w oknie wtyczki link M3U lub JSON z listą |

---

## Instalacja / Aktualizacja

Połącz się ze swoim dekoderem przez **Telnet** lub **SSH** i wklej poniższą komendę:

wget -q "--no-check-certificate" https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh -O - | /bin/sh

Po zakończeniu instalacji **zrestartuj GUI (Enigmę2)**.

---

## Kompatybilność

* **Dla kogo?** Dla każdego użytkownika z nowym oprogramowaniem zawierającym Python 3.
* **Architektury:** Działa na ARM, MIPS oraz SH4.
* **Przetestowane na:** OpenPLi, OpenATV, OpenViX, BlackHole, VTi, PurE2.
