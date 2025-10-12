# Wtyczka IPTV Dream
# Wtyczka IPTV Dream

<img src="plugin.png" alt="Ikona wtyczki IPTV Dream" width="250"/>
..

Lekka i szybka wtyczka do list IPTV dla dekoderów z oprogramowaniem Enigma2 (Python 3).

### Plany na przyszłość:
W kolejnych wersjach wtyczka zostanie rozbudowana o:
* Dodawanie list IPTV z adresu MAC.
* Pobieranie Picon dla kanałów.
* Rozbudowane opcje pobierania EPG.

---

## Główne Funkcje

* **Wczytuje listy M3U** z adresu URL, lokalnego pliku (`.m3u`, `.m3u8`) lub poprzez dane Xtream Codes.
* **Eksportuje kanały do bukietów Enigma2** – Twoje listy IPTV pojawiają się na liście kanałów TV obok pozycji satelitarnych.
* **Działa od razu** na większości popularnych obrazów bez potrzeby dodatkowej kompilacji czy instalacji zależności.

---

## Instalacja

Połącz się ze swoim dekoderem przez **Telnet** lub **SSH** i wklej poniższą komendę, aby automatycznie pobrać i zainstalować wtyczkę:

wget -q "--no-check-certificate" https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh -O - | /bin/sh

Po zakończeniu instalacji **zrestartuj GUI (Enigmę2)**.

---

## Jak to działa? – 3 Szybkie Ścieżki

1.  **M3U URL** → Wpisz lub wklej link do listy (np. `http://serwer.com/playlist.m3u`) i zatwierdź **OK**. Wtyczka sama pobierze i przetworzy listę.
2.  **M3U Plik** → Wybierz plik `.m3u` lub `.m3u8` z podłączonego nośnika (`/tmp`, pendrive, HDD, dysk sieciowy SMB/FTP).
3.  **Xtream Codes** → Wpisz dane logowania (host, login, hasło) przy użyciu polskiej klawiatury ekranowej.

Na koniec, niezależnie od wybranej metody, naciśnij **NIEBIESKI** przycisk, aby **"Eksportować kanały do bukietów"**. Kanały od razu pojawią się na liście TV.

---

## Dodatkowe Funkcje

#### Polska Klawiatura Wirtualna
* Podgląd znaku podczas pisania.
* **← →** zmiana znaku, **↑ ↓** przesuwanie kursora.
* Długie linki można łatwo wkleić z komputera (przytrzymaj **OK** → „Wklej”).

#### Przeglądarka Plików
* Pełna nawigacja po folderach i nośnikach.
* Automatyczny filtr, który pokazuje tylko pliki `.m3u` i `.m3u8`, ukrywając zbędne pliki.

---

## Kompatybilność

* **Dla kogo?** Dla każdego użytkownika z nowym oprogramowaniem zawierającym Python 3.
* **Architektury:** Działa na ARM, MIPS oraz SH4 (jeden plik `.ipk` dla wszystkich).
* **Przetestowane na:** OpenPLi, OpenATV, OpenViX, BlackHole, VTi, PurE2.
