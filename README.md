# Wtyczka IPTV Dream v3.1

<img src="https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/plugin.png" alt="IPTV Dream Logo" width="150"/>

IPTV Dream Plugin (Enigma2)
IPTV Dream to zaawansowana, a zarazem prosta w obsłudze wtyczka do odtwarzania telewizji IPTV na dekoderach z systemem Enigma2. Pozwala na łatwe wczytywanie list M3U, Xtream Codes oraz portali MAC (Stalker) i eksportowanie ich bezpośrednio do bukietów (listy kanałów) dekodera, wraz z obsługą EPG i Picon.

🚀 Szybka Instalacja (Terminal)
Zaloguj się do terminala (SSH/Telnet) swojego dekodera i wklej poniższą komendę:

Bash

wget -q "--no-check-certificate" https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh -O - | /bin/sh
Po instalacji zrestartuj GUI (Interfejs użytkownika).

✨ Główne Funkcje
Wszechstronna obsługa źródeł:

🌐 M3U URL: Wklej link do swojej listy.

📂 Plik M3U: Wczytaj plik lokalny z dysku/USB.

🔐 Xtream Codes: Logowanie za pomocą Hosta, Użytkownika i Hasła.

📺 MAC Portal (Stalker): Obsługa portali MAG/Stalker.

Eksport do Bukietów: Tworzy standardowe listy kanałów Enigma2, dzięki czemu możesz przeglądać IPTV jak zwykłą telewizję satelitarną.

EPG i Picony: Automatyczne przypisywanie EPG (programu TV) oraz logotypów kanałów.

Auto-Aktualizacja: Wbudowany system aktualizacji (OTA) – wtyczka sama sprawdzi, czy jest nowa wersja.

Wielojęzyczność: Dostępny język Polski 🇵🇱 i Angielski 🇬🇧.

🆕 Co nowego w wersji 3.1?
✅ Naprawiono Aktualizator: Rozwiązano problem "Bad archive structure" – aktualizacje pobierają się teraz poprawnie.

✅ Stabilność: Naprawiono błędy importu (vkb_input) oraz problemy przy wyborze plików lokalnych.

✅ Auto-Update: Dodano możliwość włączenia automatycznego sprawdzania aktualizacji przy starcie.

✅ Instalator: Ulepszony skrypt instalacyjny automatycznie naprawia uprawnienia plików.

⚠️ Wymagania i Znane Problemy
Biblioteki Python: Wtyczka wymaga biblioteki python-requests. W większości obrazów (OpenATV, OpenPLi) jest ona standardem. Jeśli masz błąd przy uruchamianiu, zainstaluj ją komendą: opkg install python-requests

Duże listy: Przy bardzo dużych listach (ponad 40-50 tys. kanałów) starsze dekodery mogą potrzebować chwili na przetworzenie danych.

📞 Kontakt i Zgłaszanie Błędów
Jeśli znajdziesz błąd (np. Green Screen), zgłoś go w zakładce "Issues" lub skontaktuj się z autorem. Przy zgłoszeniu podaj:

Model dekodera.

Wersję systemu (np. OpenATV 7.3).

Opis błędu lub log systemowy.

Twórca: Paweł Pawełek Licencja: Freeware
