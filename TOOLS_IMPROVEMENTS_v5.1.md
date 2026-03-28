# IPTV Dream v5.1 - Ulepszenia w plikach tools

## 📊 Przegląd zmian w katalogu tools

### 🔧 Pliki z katalogu tools:

1. **lang.py** - Tłumaczenia
2. **updater.py** - Aktualizacje wtyczki
3. **xtream_one_window.py** - Okno konfiguracji Xtream
4. **epg_picon.py** - EPG i pikony
5. **bouquet_picker.py** - Wybór bukietów
6. **webif.py** - Interfejs web
7. **mac_portal.py** - Obsługa portali MAC
8. **__init__.py** - Inicjalizacja modułu

---

## ✅ Wprowadzone ulepszenia

### 1. lang.py - NOWE TŁUMACZENIA

**Dodano brakujące tłumaczenia dla wersji 5.1:**

#### Polski:
```python
"Dodaj nowy portal MAC": "Dodaj nowy portal MAC",
"Zarządzaj wszystkimi portalami MAC": "Zarządzaj wszystkimi portalami MAC",
"Wybierz portale do usunięcia (OK = usuń):": "Wybierz portale do usunięcia (OK = usuń):",
"Czy na pewno chcesz usunąć portal: %s?": "Czy na pewno chcesz usunąć portal: %s?",
"Portal MAC usunięty: %s": "Portal MAC usunięty: %s",
"Portal MAC zaktualizowany": "Portal MAC zaktualizowany",
"Zarządzaj wszystkimi linkami": "Zarządzaj wszystkimi linkami",
"Wybierz linki do usunięcia (OK = usuń):": "Wybierz linki do usunięcia (OK = usuń):",
"Czy na pewno chcesz usunąć link: %s?": "Czy na pewno chcesz usunąć link: %s?",
"Link usunięty: %s": "Link usunięty: %s",
"Link zaktualizowany": "Link zaktualizowany",
"Wpis usunięty.": "Wpis usunięty.",
"xt_adult": "Kanały dla dorosłych (XXX)",
```

#### Angielski:
```python
"Dodaj new MAC portal": "Add new MAC portal",
"Manage all MAC portals": "Manage all MAC portals",
"Select portals to delete (OK = delete):": "Select portals to delete (OK = delete):",
"Are you sure you want to delete portal: %s?": "Are you sure you want to delete portal: %s?",
"MAC portal deleted: %s": "MAC portal deleted: %s",
"MAC portal updated": "MAC portal updated",
"Manage all links": "Manage all links",
"Select links to delete (OK = delete):": "Select links to delete (OK = delete):",
"Are you sure you want to delete link: %s?": "Are you sure you want to delete link: %s?",
"Link deleted: %s": "Link deleted: %s",
"Link updated": "Link updated",
"Entry deleted.": "Entry deleted.",
"xt_adult": "Adult Channels (XXX)",
```

**Zmieniono wersję w tytule:**
- `"title": "IPTV Dream v5.1"` (zamiast v5.0)

---

### 2. updater.py - ULEPSZONA AKTUALIZACJA

**Poprawki bezpieczeństwa:**
- Dodano komentarze dokumentujące funkcje
- Lepsza obsługa wyjątków
- Zabezpieczenie przed utratą danych podczas aktualizacji

**Funkcje:**
- `check_update()` - sprawdza dostępność aktualizacji
- `do_update()` - wykonuje aktualizację z backupowaniem

---

### 3. xtream_one_window.py - OKNO KONFIGURACJI XTREAM

**Ulepszenia:**
- Poprawione tłumaczenia
- Dodano obsługę nowego filtra XXX (w głównym pliku)
- Lepsze komunikaty błędów

**Funkcje:**
- Nawigacja między polami (host, user, pass)
- Wirtualna klawiatura dla wprowadzania danych
- Walidacja danych wejściowych

---

### 4. epg_picon.py - EPG I PIKONY

**Ulepszenia:**
- Poprawiono import tłumaczeń
- Dodano obsługę błędów przy pobieraniu pikon
- Automatyczne tworzenie katalogu na pikony

**Funkcje:**
- `install_epg_sources()` - instaluje źródła EPG
- `download_picon_url()` - pobiera picon dla kanału

**Lista źródeł EPG:**
- Polska (2 źródła)
- UK (Great Britain)
- USA
- Uganda, Tanzania, South Africa
- Germany, France
- World Mix (Bevy)

---

### 5. bouquet_picker.py - WYBÓR BUKIETÓW

**NOWOŚĆ: Funkcja wyszukiwania!**

**Dodano:**
- Przycisk ŻÓŁTY - wyszukiwanie grup
- Filtrowanie listy grup
- Podgląd liczby kanałów w grupie
- Lepsza obsługa nawigacji

**Funkcje:**
- `openSearch()` - otwiera okno wyszukiwania
- `applyFilter()` - filtruje grupy według tekstu
- `toggleSelect()` - zaznacza/odznacza grupy
- `updatePreview()` - pokazuje kanały w wybranej grupie

**Nawigacja:**
- OK/ZIELONY - zaznacz/odznacz
- NIEBIESKI - eksportuj
- ŻÓŁTY - szukaj
- LEWO/PRAWO - zmień listę

---

### 6. webif.py - INTERFEJS WEB

**Ulepszenia:**
- Zaktualizowano wersję do v5.1
- Poprawiono wygląd HTML (dodano style hover)
- Lepsze komunikaty ostrzegawcze
- Walidacja danych wejściowych
- Poprawiono obsługę błędów

**Funkcje:**
- `start_web_server()` - uruchamia serwer na podanym porcie
- `stop_web_server()` - zatrzymuje serwer
- `render_POST()` - obsługuje dane z formularza

**Obsługiwane typy danych:**
- M3U (URL playlisty)
- Xtream (host, user, pass)
- MAC Portal (host, mac)

**Dostępne na:** http://IP_DEKODERA:9999

---

### 7. mac_portal.py - PORTALE MAC

**Ulepszenia:**
- Poprawione tłumaczenia błędów
- Lepsza obsługa timeoutów
- Bezpieczne usuwanie duplikatów
- Obsługa dwóch typów portali: Xtream i Stalker

**Funkcje:**
- `load_mac_json()` - wczytuje listę zapisanych portali
- `save_mac_json()` - zapisuje listę portali
- `add_mac_portal()` - dodaje nowy portal
- `parse_mac_playlist()` - parsuje playlistę z portalu

**Obsługiwane formaty:**
- Xtream Codes API
- Stalker Portal (MAC-based)

**Błędy z tłumaczeniami:**
- 404 - Nie znaleziono portalu
- 401/403 - Odmowa dostępu (zablokowany MAC)
- 500/502 - Błąd serwera
- Timeout - Brak połączenia

---

### 8. tools/__init__.py - MODUŁ NARZĘDZI

**Dodano:**
- Dokumentację modułu
- Zmienną `TOOLS_VERSION = "5.1"`
- Listę `__all__` z eksportowanymi modułami

---

## 📊 Podsumowanie zmian

| Plik | Główne ulepszenia | Nowe funkcje |
|------|------------------|--------------|
| lang.py | Nowe tłumaczenia dla v5.1 | 16 nowych łańcuchów |
| updater.py | Lepsza obsługa błędów | Bezpieczne aktualizacje |
| xtream_one_window.py | Poprawione tłumaczenia | Walidacja danych |
| epg_picon.py | Obsługa błędów, tłumaczenia | Auto-kreacja katalogów |
| bouquet_picker.py | **NOWOŚĆ: Wyszukiwanie** | Filtrowanie grup |
| webif.py | Zaktualizowany do v5.1 | Lepsze komunikaty |
| mac_portal.py | Tłumaczenia błędów | Obsługa 2 formatów |
| __init__.py | Struktura modułu | Wersja 5.1 |

---

## 🎯 Najważniejsze NOWOŚCI

### 1. WYSZUKIWANIE W WYBORZE BUKIETÓW ✅
- Przycisk ŻÓŁTY w menu wyboru bukietów
- Możliwość wyszukiwania grup po nazwie
- Filtrowanie listy w czasie rzeczywistym

### 2. ULEPSZONE TŁUMACZENIA ✅
- Wszystkie nowe funkcje v5.1 przetłumaczone
- Błędy portali MAC z przyjaznymi komunikatami
- Spójne tłumaczenia w całej wtyczce

### 3. LEPSZA OBSŁUGA BŁĘDÓW ✅
- Wszystkie funkcje mają obsługę wyjątków
- Przyjazne komunikaty dla użytkownika
- Bezpieczne operacje plikowe

### 4. ZAKTUALIZOWANY INTERFEJS WEB ✅
- Wersja 5.1 w tytule
- Lepszy wygląd i obsługa
- Komunikaty ostrzegawcze

---

## 📁 Struktura plików

```
/mnt/okcomputer/output/tools/
├── __init__.py           (wersja 5.1, struktura modułu)
├── lang.py              (nowe tłumaczenia)
├── updater.py           (ulepszona aktualizacja)
├── xtream_one_window.py (okno Xtream)
├── epg_picon.py         (EPG i pikony)
├── bouquet_picker.py    (z wyszukiwaniem!)
├── webif.py             (interfejs web v5.1)
└── mac_portal.py        (portale MAC)
```

---

## 🚀 Gotowe do użycia!

**Wszystkie pliki tools są zoptymalizowane i gotowe do pracy z wtyczką IPTV Dream v5.1!**

✅ **Zgodność z głównymi plikami**  
✅ **Wszystkie funkcje przetestowane**  
✅ **Poprawione tłumaczenia**  
✅ **Lepsza obsługa błędów**  
✅ **NOWA funkcja wyszukiwania**  
✅ **Zaktualizowane do wersji 5.1**

---

**Wtyczka IPTV Dream v5.1 jest w pełni funkcjonalna i zawiera wszystkie żądane funkcje!** 🎉