Wprowadzono zbiorczą aktualizację wtyczki IPTV Dream, skupioną na stabilności działania, obsłudze źródeł IPTV oraz szybkim eksporcie bukietów.

### Główne zmiany:

- ✅ **[NAPRAWIONO] Obsługa M3U z URL:** Poprawiono pobieranie list M3U oraz obsługę błędów typu `NET-HTTP-884`, `RemoteDisconnected` i `Connection aborted`.
- ✅ **[NAPRAWIONO] Komunikaty błędów:** Wtyczka lepiej rozpoznaje sytuacje, gdy serwer zwraca HTML, pustą odpowiedź albo nieprawidłowe dane zamiast listy M3U/JSON.
- ⚡ **[ULEPSZONO] MAC / Stalker / MAG / eStalker:** Dodano poprawki zgodności dla portali MAC/Stalker/MAG/eStalker, w tym obsługę ścieżek `/c/` oraz `/stalker_portal/c/`.
- ⚡ **[ULEPSZONO] Timeouty MAC:** Skrócono czas oczekiwania przy portalach, które nie odpowiadają poprawnie, aby wtyczka nie wisiała zbyt długo na ładowaniu.
- ✅ **[NAPRAWIONO] Usuwanie portali MAC:** Usunięte wpisy nie powinny już wracać z kopii `.bak` ani starych plików konfiguracyjnych.
- ✅ **[NAPRAWIONO] Eksport bukietów:** Poprawiono przypadek, w którym eksport wybranych bukietów kończył się wynikiem `0`.
- ⚡ **[PRZYWRÓCONO] Szybki eksport bukietów:** Eksport bukietów znowu działa szybko, bez paska postępu zatrzymującego się na `0%`.
- ✅ **[NAPRAWIONO] Blue Screen / GSOD:** Poprawiono błąd niebieskiego ekranu przy eksporcie lub dodawaniu większej liczby kanałów.
- ⚙️ **[ULEPSZONO] EPG i Picon:** Cięższe operacje EPG/Picon zostały oddzielone od samego eksportu bukietów.
- 📌 **[ZAKTUALIZOWANO] Numer wersji:** Wtyczka wyświetla aktualnie wersję `6.6.7`.

### Instalacja ręczna z pliku IPK:

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-iptvdream_6.6.7_all.ipk
init 4
sleep 2
init 3
```

### Zalecenie po wcześniejszych testach:

Jeżeli była testowana starsza wersja 6.6.x i występują stare wpisy/cache, można wyczyścić stare pliki pomocnicze:

```sh
rm -f /etc/enigma2/iptvdream_mac.json.bak /etc/enigma2/iptvdream_mylinks.json.bak
rm -rf /tmp/iptvdream_cache /tmp/iptvdream_v6_cache /tmp/iptvdream_epg_cache
```

**IPTV Dream v6.6.7**  
**by Paweł Pawełek**
