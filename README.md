# Wtyczka IPTV Dream v4.2

<img src="https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/plugin.png" alt="IPTV Dream Logo" width="150"/>

# IPTV Dream Plugin v4.2 for Enigma2

Zaawansowana wtyczka do obsługi list IPTV (M3U, Xtream, MAC Portal) z nowoczesnym interfejsem, obsługą przez przeglądarkę (WebIF), generatorem bukietów oraz wyborem odtwarzacza.

Advanced IPTV plugin (M3U, Xtream, MAC Portal) featuring a modern interface, Web Interface (WebIF) support, bouquet generation, and player selection.

## 🚀 Nowości w wersji 4.2 / What's new in v4.2

* **Wybór Odtwarzacza (Player Selector):**
    * Nowa opcja w menu (klawisz 9) pozwalająca na zmianę typu serwisu.
    * Wybór pomiędzy **GStreamer (4097)** a **ExtePlayer3 (5002)**.
    * New menu option (key 9) to switch between GStreamer and ExtePlayer3 service types.
* **Web Interface (WebIF):**
    * Zarządzanie wtyczką przez przeglądarkę na komputerze lub telefonie.
    * Wysyłanie linków M3U, danych Xtream i MAC bezpośrednio do dekodera.
* **Nowy Interfejs (GUI):**
    * Nowoczesny, ciemny motyw i przejrzysty układ.

## 🌟 Główne Funkcje / Key Features

* **Źródła / Sources:** M3U URL, M3U File, Xtream Codes, MAC Portal (Stalker/Mag), Custom Links.
* **Player:** Możliwość wyboru silnika odtwarzania (GStreamer / ExtePlayer3).
* **EPG:** Automatyczne przypisywanie, obsługa wielu krajów (PL, UK, US, DE...), własne źródła XMLTV.
* **Bukiety / Bouquets:** Szybki eksport wybranych grup kanałów do list ulubionych.
* **Język / Language:** Auto-wykrywanie (PL / EN).

## 📥 Instalacja / Installation

### Metoda 1: Telnet / SSH (Zalecana / Recommended)
Połącz się z dekoderem przez terminal i wklej poniższą komendę:
Connect to your receiver via terminal and paste this command:

```bash
wget -q "--no-check-certificate" [https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh](https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh) -O - | /bin/sh
Metoda 2: Ręczna / Manual
Pobierz plik .ipk z zakładki Releases.

Wgraj plik do katalogu /tmp w dekoderze.

Zainstaluj przez menu wtyczek lub komendę: opkg install /tmp/*.ipk.

🌐 Jak używać Web Interface? / How to use WebIF?
Otwórz wtyczkę na dekoderze i wybierz opcję 8 (Web Interfejs).

Na komputerze lub telefonie wpisz w przeglądarce adres widoczny na ekranie TV, np.: http://192.168.1.X:9999

Wybierz zakładkę (M3U / Xtream / MAC), wpisz dane i kliknij Wyślij.

🛠 Changelog v4.2
Player: Dodano przełącznik typu serwisu (4097/5002) pod klawiszem 9.

GUI: Zaktualizowano wygląd menu głównego.

WebIF: Poprawki w interfejsie webowym.

Optymalizacja: Drobne poprawki w kodzie i tłumaczeniach.

Author: Paweł Pawełek (msisystem@t.pl)
