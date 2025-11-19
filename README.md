# Wtyczka IPTV Dream v3.0

<img src="https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/plugin.png" alt="IPTV Dream Logo" width="150"/>

Zaawansowana wtyczka do importowania list kanałów IPTV (M3U, Xtream, MAC Portal) i eksportowania ich do bukietów w dekoderach z oprogramowaniem Enigma2.

---

## Główne Funkcje

- **Wsparcie dla wielu źródeł:**
  - Pliki M3U (lokalne)
  - Linki URL do list M3U/M3U8
  - Dane logowania Xtream
  - Dane logowania MAC Portal
- **Inteligentny Parser M3U:** Poprawnie odczytuje grupy kanałów (`group-title`) i logotypy (`tvg-logo`).
- **Wybór Bukietów:** Wygodny interfejs do zaznaczania, które grupy kanałów chcesz zaimportować.
- **Automatyczne EPG i Picony:** Opcjonalna możliwość pobrania EPG i ikon kanałów dla załadowanej listy.
- **Brak "zamrażania" interfejsu:** Wszystkie operacje sieciowe działają w tle, nie blokując pilota.
- **Wielojęzyczność:** Interfejs dostępny w języku polskim i angielskim.
- **System Aktualizacji:** Wbudowana funkcja sprawdzania i instalowania nowszych wersji wtyczki.

---

## Instalacja 🚀

Połącz się ze swoim dekoderem przez terminal (Telnet lub SSH) i wklej poniższą komendę:

```shell
wget -q "--no-check-certificate" https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh -O - | /bin/sh
