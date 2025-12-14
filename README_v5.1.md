# IPTV Dream - Wtyczka dla Enigma 2 (v5.1)

## 📋 Spis treści
- [Nowości w wersji 5.1](#nowości-w-wersji-51)
- [Instalacja](#instalacja)
- [Obsługa](#obsługa)
- [Funkcje](#funkcje)
- [Rozwiązywanie problemów](#rozwiązywanie-problemów)

## 🎉 Nowości w wersji 5.1

### 1. ✅ Możliwość usuwania danych z pozycji pilota

#### Portale MAC:
- **Menu zarządzania**: Przycisk 4 (MAC Portal) → "Zarządzaj wszystkimi portalami MAC"
- **Usuwanie pojedyncze**: Wybierz portal → "Usuń wpis" → Potwierdź
- **Usuwanie masowe**: Możliwość usuwania wielu portali MAC
- **Edycja**: Możliwość edycji danych istniejącego portalu

#### Własne linki M3U:
- **Menu zarządzania**: Przycisk 5 (Własne) → "Zarządzaj wszystkimi linkami"
- **Usuwanie pojedyncze**: Wybierz link → "Usuń wpis" → Potwierdź
- **Usuwanie masowe**: Możliwość usuwania wielu linków
- **Edycja**: Możliwość edycji nazwy i URL istniejącego linku

### 2. 🔞 Bukiet XXX/VOD dla dorosłych

#### Automatyczne wykrywanie kanałów XXX:
- Wykrywa kanały po słowach kluczowych: `xxx`, `adult`, `porn`, `sex`, `erotic`, `18+`, `mature`
- Automatyczne przypisanie do bukietu **XXX**
- Działa dla wszystkich formatów: M3U, MAC, Xtream

#### Automatyczne wykrywanie VOD:
- Wykrywa filmy i seriale po URL (`/movie/`, `/series/`)
- Wykrywa po rozszerzeniach plików (`.mp4`, `.mkv`, `.avi`, `.vod`)
- Wykrywa po słowach kluczowych w nazwie: `vod`, `movie`, `film`, `video`, `series`, `serial`
- Automatyczne przypisanie do bukietu **VOD**

#### Nowa opcja w Xtream:
- Dodano opcję "Tylko XXX" do filtrowania samych kanałów dla dorosłych

### 3. 📂 Poprawione grupowanie kanałów

#### Dla formatów M3U, MAC, Xtream:
- **Zachowanie oryginalnych grup** z playlisty
- **Automatyczne tworzenie bukietów** według grup tematycznych
- **Grupowanie według państw** (PL, UK, DE, IT, itd.)
- **Grupowanie według jakości** (HD, FHD, 4K)

#### Przykładowe grupy:
- `Polska`, `Polska HD`, `Polska FHD`
- `Niemcy`, `Wielka Brytania`, `USA`
- `Sport`, `Filmy`, `Dokumentalne`
- `XXX`, `VOD`, `Dla dzieci`

### 4. 📺 Ulepszony EPG (maksymalizacja dopasowań)

#### Nowe algorytmy dopasowania:
1. **TVG-ID z M3U** - najwyższy priorytet
2. **Czysta nazwa** - dokładne dopasowanie
3. **Wersje krajowe** - z sufiksami (.pl, .uk, .de, itd.)
4. **Wersja uproszczona** - bez oznaczeń HD/FHD/4K
5. **Wersje z numerami** - TVP 1, TVP1, TVP-1, TVP.1
6. **Wersje międzynarodowe** - z dopiskiem HD, TV, CHANNEL
7. **XXX i VOD** - specjalne identyfikatory dla kanałów dorosłych

#### Przykład dopasowania dla "TVP 1 HD":
```
tvp1hd
TVP 1 HD
TVP1HD
TVP-1
TVP.1
tvp1hd.pl
tvp-1.pl
tvp1.tv
TVP1HD
TVP1
TVP1HD.pl
TVP1CHANNEL
```

#### Lista sufiksów krajowych:
`gb`, `uk`, `pl`, `us`, `de`, `it`, `es`, `fr`, `nl`, `tr`, `ug`, `tz`, `za`

### 5. 🔧 Inne ulepszenia

- **Wersja 5.1** we wszystkich plikach
- **Poprawione tłumaczenia** dla języka polskiego i angielskiego
- **Lepsza obsługa błędów** podczas parsowania plików
- **Optymalizacja wydajności** przy dużych playlistach

## 📥 Instalacja

1. Skopiuj wszystkie pliki do katalogu wtyczki w Enigma 2
2. Nadaj uprawnienia wykonywalne: `chmod +x *.py`
3. Zrestartuj Enigma 2 lub uruchom ponownie GUI
4. Wtyczka będzie dostępna w menu głównym i menu rozszerzeń

## 🎮 Obsługa

### Główne funkcje (przyciski numeryczne):

| Przycisk | Funkcja |
|----------|---------|
| **1** | Wczytaj playlistę M3U z URL |
| **2** | Wczytaj playlistę M3U z pliku |
| **3** | Połącz z serwerem Xtream |
| **4** | Zarządzaj portalami MAC |
| **5** | Zarządzaj własnymi linkami |
| **6** | Zmień język (PL/EN) |
| **7** | Ustaw URL EPG |
| **8** | Włącz/Wyłącz interfejs web |
| **9** | Zmień typ odtwarzacza (4097/5002) |

### Przyciski kolorowe:

| Przycisk | Funkcja |
|----------|---------|
| **CZERWONY** | Wyjście z wtyczki |
| **ZIELONY** | Sprawdź aktualizacje |
| **ŻÓŁTY** | Zainstaluj EPG |
| **NIEBIESKI** | Eksportuj do bukietów |

### Zarządzanie danymi:

#### Portale MAC:
1. Naciśnij **4** (MAC Portal)
2. Wybierz "Zarządzaj wszystkimi portalami MAC"
3. Wybierz portal do usunięcia/edycji
4. Potwierdź operację

#### Własne linki:
1. Naciśnij **5** (Własne)
2. Wybierz "Zarządzaj wszystkimi linkami"
3. Wybierz link do usunięcia/edycji
4. Potwierdź operację

## 🎯 Funkcje

### ✅ Zrobione:
- [x] Wczytywanie playlist M3U z URL i plików
- [x] Obsługa serwerów Xtream
- [x] Obsługa portali MAC
- [x] Automatyczne grupowanie kanałów
- [x] Eksport do bukietów Enigma 2
- [x] Generowanie EPG
- [x] Pobieranie pikon
- [x] Interfejs web
- [x] Zarządzanie własnymi linkami
- [x] **Usuwanie danych z poziomu pilota (NOWOŚĆ)**
- [x] **Wykrywanie kanałów XXX (NOWOŚĆ)**
- [x] **Wykrywanie VOD (NOWOŚĆ)**
- [x] **Ulepszony EPG (NOWOŚĆ)**
- [x] **Poprawione grupowanie (NOWOŚĆ)**

### 🔧 Techniczne:
- Wersja: **5.1**
- Kompatybilność: Enigma 2
- Języki: Polski, Angielski
- Formaty: M3U, M3U8, Xtream, MAC Portal

## ❓ Rozwiązywanie problemów

### Problem: Brak bukietów XXX/VOD
**Rozwiązanie:**
- Upewnij się, że masz wersję 5.1
- Kanały XXX są automatycznie wykrywane po słowach kluczowych
- VOD są wykrywane po URL lub nazwie
- Sprawdź czy playlista zawiera takie kanały

### Problem: Słabe dopasowanie EPG
**Rozwiązanie:**
- Wersja 5.1 ma znacznie ulepszony EPG
- Upewnij się, że masz ustawiony URL EPG (przycisk 7)
- Uruchom instalację EPG (przycisk żółty)
- Wtyczka generuje wiele wariantów ID dla lepszego dopasowania

### Problem: Nie działa usuwanie danych
**Rozwiązanie:**
- Użyj przycisku 4 dla portali MAC
- Wybierz "Zarządzaj wszystkimi portalami MAC"
- Użyj przycisku 5 dla własnych linków
- Wybierz "Zarządzaj wszystkimi linkami"
- Potwierdź usuwanie w oknie dialogowym

### Problem: Grupy są niewłaściwe
**Rozwiązanie:**
- Wersja 5.1 ma poprawione grupowanie
- Grupy są zachowywane z oryginalnej playlisty
- Automatycznie tworzone są grupy XXX i VOD
- Dla M3U/MAC/Xtream działa tak samo

## 📞 Wsparcie

Wtyczka jest w wersji 5.1 i zawiera wszystkie żądane funkcje:
- ✅ Usuwanie danych z pilota
- ✅ Bukiet XXX/VOD
- ✅ Poprawione grupowanie
- ✅ Ulepszony EPG

## 📄 Licencja

Wtyczka jest otwartoźródłowa. Możesz modyfikować i rozpowszechniać zgodnie z licencją Enigma 2.

---

**Wersja: 5.1**  
**Data: 14.12.2024**  
**Autor: Zespół IPTV Dream**