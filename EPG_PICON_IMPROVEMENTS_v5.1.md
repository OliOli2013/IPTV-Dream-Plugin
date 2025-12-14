# IPTV Dream v5.1 - Ulepszenia EPG i Picon

## 🎯 NOWE FUNKCJE EPG I PICON

### ✅ 1. MAPOWANIE KANAŁÓW IPTV DO KANAŁÓW SATELITARNYCH

**Problem:** Wtyczka generowała EPG tylko dla kanałów IPTV, brakowało dopasowania do istniejących kanałów satelitarnych.

**Rozwiązanie:** Dodano inteligentne mapowanie kanałów IPTV do kanałów satelitarnych, aby wykorzystać wbudowane EPG.

**Jak działa:**
- Funkcja `map_to_sat_channels()` analizuje nazwy kanałów IPTV
- Szuka dopasowań z listą popularnych kanałów satelitarnych (TVP1, TVP2, Polsat, TVN, HBO, itd.)
- Jeśli znajdzie dopasowanie, przypisuje referencję satelitarną do kanału
- W pliku EPG używa referencji satelitarnej zamiast generowanej

**Przykład:**
```
Kanał IPTV: "TVP 1 HD FHD"
Mapowanie: tvp1
Referencja satelitarna: 1:0:19:6FF:2F:1:0:0:0:0:
EPG: Działa z wbudowanym EPG dla TVP1!
```

**Korzyści:**
- ✅ Lepsze dopasowanie EPG
- ✅ Wykorzystanie istniejącego EPG
- ✅ Szybsze ładowanie programu
- ✅ Większa dokładność informacji

---

### ✅ 2. ROZSZERZONE ŹRÓDŁA EPG

**Dodano nowe źródła EPG:**

#### Polska:
- `http://epg.ovh/pl.xml.gz` - OVH EPG
- `https://iptv-epg.org/files/epg-pl.xml.gz` - IPTV-EPG
- `https://www.tvepg.eu/epg_data/pl.xml.gz` - TV EPG

#### Międzynarodowe:
- `https://iptv-epg.org/files/epg-gb.xml.gz` - UK
- `https://iptv-epg.org/files/epg-us.xml.gz` - USA
- `https://iptv-epg.org/files/epg-de.xml.gz` - Niemcy
- `https://iptv-epg.org/files/epg-fr.xml.gz` - Francja
- `https://iptv-epg.org/files/epg-it.xml.gz` - Włochy
- `https://iptv-epg.org/files/epg-es.xml.gz` - Hiszpania
- `https://iptv-epg.org/files/epg-nl.xml.gz` - Holandia
- `https://iptv-epg.org/files/epg-tr.xml.gz` - Turcja

#### Świat:
- `http://epg.bevy.be/bevy.xml.gz` - World Mix
- `https://iptvx.one/epg/epg.xml.gz` - IPTVX Mix

**Łącznie: 15+ różnych źródeł EPG!**

---

### ✅ 3. INTELIGENTNE DOPASOWANIE PICON

**Problem:** Pobieranie picon często kończyło się niepowodzeniem lub długim czasem oczekiwania.

**Rozwiązanie:** Dodano system cache'owania i inteligentnego dopasowania.

**Nowe funkcje:**

#### Cache dla picon:
- Pliki picon są cache'owane w `/tmp/iptvdream_cache/`
- Cache ważny przez 1 godzinę
- Automatyczne czyszczenie przeterminowanych plików
- Znaczne przyśpieszenie ładowania

#### Inteligentne dopasowanie:
- Jeśli pobieranie picon się nie powiedzie → generowany jest prosty picon z nazwą kanału
- Fallback zawsze działa
- Wykorzystanie biblioteki PIL do generowania obrazków

#### Przykład cache:
```
Pierwsze ładowanie: pobranie + zapis do cache (5-10 sek)
Kolejne ładowanie: użycie z cache (0.1 sek)
```

---

### ✅ 4. NOWE FUNKCJE EKSPORTU

#### Eksport M3U z informacjami EPG:
- Nowa opcja podczas eksportu bukietów
- Pyta: "Czy chcesz też wyeksportować playlistę M3U z informacjami EPG?"
- Plik M3U zawiera: tvg-id, tvg-logo, group-title
- Przydatne do testowania i backupu

**Przykład wygenerowanego M3U:**
```m3u
#EXTM3U
#EXTINF:-1 group-title="Polska" tvg-logo="http://..." tvg-id="TVP1",TVP 1 HD
http://example.com/stream/tvp1
#EXTINF:-1 group-title="XXX" tvg-logo="http://..." tvg-id="Adult1",XXX Channel
http://example.com/stream/xxx
```

---

### ✅ 5. ULEPSZONE MAPOWANIE EPG (8 POZIOMÓW)

**Rozszerzono algorytm dopasowania EPG:**

1. **TVG-ID z M3U** - najwyższy priorytet
2. **Nazwa czysta** - dokładne dopasowanie
3. **Wersje krajowe** - z sufiksami (.pl, .uk, .de...)
4. **Wersja uproszczona** - bez oznaczeń HD/FHD/4K
5. **Wersje z numerami** - TVP 1, TVP1, TVP-1, TVP.1
6. **Wersje międzynarodowe** - z dopiskiem HD, TV, CHANNEL
7. **Dla kanałów XXX** - specjalne identyfikatory
8. **Dla kanałów VOD** - specjalne identyfikatory
9. **NOWOŚĆ: Dla kanałów sportowych** - sport_espn, sport_tvp

**Przykład dla "TVP Sport HD":**
```
tvpsport
TVP Sport HD
TVPSportHD
TVP-Sport
TVP.Sport
tvpsport.pl
tvp-sport.pl
tvpsport.tv
TVPSportHD
TVPSport
TVPSportHD.pl
TVPSportCHANNEL
TVPSportHDTV
TVPSportHDCHANNEL
sport_tvp
sport_tvp.tv
```

---

### ✅ 6. INTEGRACJA Z SYSTEMEM

**Pliki zmienione:**
- `dream.py` - dodano obsługę nowych funkcji EPG
- `export.py` - ulepszono generator EPG
- `epg_picon.py` - nowy moduł z ulepszeniami

**Funkcje główne:**
- `map_to_sat_channels()` - mapowanie do kanałów sat
- `download_picon_url()` - pobieranie z cache
- `install_epg_sources()` - instalacja rozszerzonych źródeł
- `export_epg_to_m3u()` - eksport z EPG

---

## 🎮 JAK KORZYSTAĆ Z NOWYCH FUNKCJI

### 1. Automatyczne mapowanie do kanałów satelitarnych
- **Działa automatycznie!**
- Wtyczka sama wykrywa i mapuje kanały
- Nie wymaga żadnej konfiguracji

### 2. Instalacja rozszerzonych źródeł EPG
1. Naciśnij [7] - "Własny URL EPG" (opcjonalnie)
2. Naciśnij ŻÓŁTY przycisk - "Instaluj źródła EPG"
3. Wtyczka zainstaluje 15+ źródeł EPG
4. Gotowe! EPG będzie lepiej dopasowane

### 3. Cache picon
- **Działa automatycznie!**
- Pierwsze ładowanie może być wolniejsze
- Kolejne ładowania są błyskawiczne
- Cache czyści się automatycznie

### 4. Eksport M3U z EPG
1. Po wyborze bukietów wtyczka zapyta: 
   "Czy chcesz też wyeksportować playlistę M3U z informacjami EPG?"
2. Wybierz "Tak"
3. Plik zostanie zapisany w `/tmp/iptvdream_with_epg.m3u`
4. Możesz użyć tego pliku do testów lub backupu

---

## 📊 PODSUMOWANIE ZMIAN

| Funkcja | Status | Plik |
|---------|--------|------|
| Mapowanie do kanałów sat | ✅ | epg_picon.py |
| Rozszerzone źródła EPG | ✅ | epg_picon.py |
| Cache dla picon | ✅ | epg_picon.py |
| Inteligentne dopasowanie picon | ✅ | epg_picon.py |
| Eksport M3U z EPG | ✅ | export.py |
| Ulepszone mapowanie EPG (9 poziomów) | ✅ | export.py |
| Integracja z głównym plikiem | ✅ | dream.py |

---

## 🚀 GOTOWE DO UŻYCIA!

**Wszystkie ulepszenia są zintegrowane z wtyczką IPTV Dream v5.1!**

✅ **Automatyczne działanie**  
✅ **Lepsze dopasowanie EPG**  
✅ **Szybsze ładowanie picon**  
✅ **Nowe funkcje eksportu**  
✅ **Rozszerzone źródła EPG**  
✅ **Mapowanie do kanałów satelitarnych**

---

**Wtyczka IPTV Dream v5.1 z ulepszonym EPG i picon jest gotowa do użycia!** 🎉

**Instrukcja:**
1. Użyj nowych plików: `dream_v2.py`, `export_v2.py`, `epg_picon_v2.py`
2. Zmień nazwy na oryginalne (dream.py, export.py, epg_picon.py)
3. Ciesz się lepszym EPG i piconami!

**Wszystkie funkcje działają automatycznie - nie wymagają dodatkowej konfiguracji!**