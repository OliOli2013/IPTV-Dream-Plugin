# Wtyczka IPTV Dream v4.2

<img src="https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/plugin.png" alt="IPTV Dream Logo" width="150"/>

# IPTV Dream Plugin v4.0 for Enigma2

Zaawansowana wtyczka do obsługi list IPTV (M3U, Xtream, MAC Portal) z nowoczesnym interfejsem, obsługą przez przeglądarkę (WebIF) i generatorem bukietów.

Advanced IPTV plugin (M3U, Xtream, MAC Portal) featuring a modern interface, Web Interface (WebIF) support, and bouquet generation.

## 🚀 Nowości w wersji 4.0 / What's new in v4.0

* **Nowy Interfejs (New GUI):**
    * Całkowicie odświeżony, ciemny motyw (Modern Dark Theme).
    * Przejrzysty układ dwukolumnowy (Clean 2-column layout).
* **Web Interface (WebIF):**
    * Zarządzanie wtyczką przez przeglądarkę na komputerze lub telefonie (Control via PC/Phone browser).
    * Wysyłanie linków M3U, danych Xtream i MAC bezpośrednio do dekodera (Send M3U/Xtream/MAC data directly).
* **QR Code:**
    * Wbudowany kod QR do wsparcia projektu (Built-in QR code for support).

## 🌟 Główne Funkcje / Key Features

* **Źródła / Sources:** M3U URL, M3U File, Xtream Codes, MAC Portal (Stalker/Mag), Custom Links.
* **EPG:** Automatyczne przypisywanie, obsługa wielu krajów (PL, UK, US, DE...), własne źródła XMLTV.
* **Bukiety / Bouquets:** Eksport do list kanałów Enigma2 (Userbouquets) z obsługą Gstreamer (4097) i ExtePlayer3 (5002).
* **Język / Language:** Auto-wykrywanie (PL / EN).

## 📥 Instalacja / Installation

### Metoda 1: Telnet / SSH (Zalecana / Recommended)
Połącz się z dekoderem przez terminal i wklej poniższą komendę:
Connect to your receiver via terminal and paste this command:

```bash
wget -q "--no-check-certificate" [https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh](https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh) -O - | /bin/sh
