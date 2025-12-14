# IPTV Dream v6.0 - Przewodnik Aktualizacji z v5.1 do v6.0

## 🚨 **Dlaczego Nadal Widzisz v5.1?**

### **Problem**
Jeśli skopiowałeś pliki v6.0 ale nadal widzisz wersję v5.1, to znaczy że:
1. **Stary plugin.py** wczytuje `dream.py` zamiast `dream_v6.py`
2. **Niekompletna instalacja** - brakuje kluczowych plików
3. **Konflikt wersji** - v5.1 nadal obecna w systemie

### **Rozwiązanie** - Kompletna instalacja v6.0

## 📋 **Krok po Kroku - Aktualizacja do v6.0**

### **Krok 1: Usuń Starą Wersję v5.1** (WAŻNE!)

```bash
# Połącz się z boxem przez SSH
ssh root@IP_TWOJEGO_BOXA

# Przejdź do katalogu wtyczek
cd /usr/lib/enigma2/python/Plugins/Extensions/

# USUŃ starą wersję v5.1 (jeśli istnieje)
rm -rf IPTV-Dream/
# LUB jeśli masz inną nazwę:
rm -rf IPTV-Dream-v5.1/
```

### **Krok 2: Skopiuj NOWE pliki v6.0**

Skopiuj **Wszystkie** pliki z pakietu v6.0:

**Lista plików do skopiowania:**
```
IPTV-Dream/
├── dream_v6.py          ✅ (GŁÓWNY PLUGN V6.0)
├── plugin.py            ✅ (ZAKTUALIZOWANY)
├── __init__.py          ✅ (NOWY)
├── setup.xml            ✅ (ZAKTUALIZOWANY)
├── export_v2.py         ✅ (ENHANCED)
├──
├── tools/
│   ├── __init__.py
│   ├── epg_manager_v6.py
│   ├── picon_manager_v6.py
│   ├── favorites_v6.py
│   ├── statistics_v6.py
│   ├── history_v6.py
│   ├── mac_portal_v6.py
│   ├── updater_v6.py
│   ├── lang_v6.py
│   ├── xtream_v6.py
│   ├── bouquet_picker_v6.py
│   └── webif_v6.py
│
└── resources/
    └── images/
        └── (pliki graficzne)
```

### **Krok 3: Nadaj Prawa Dostępu**

```bash
# Nadaj prawa dostępu
cd /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/

chmod 755 *.py
chmod 755 -R tools/
chmod 755 -R resources/
chmod 644 *.xml
chmod 644 __init__.py
```

### **Krok 4: Wyczyść Cache i Konfigurację**

```bash
# Wyczyść stare pliki konfiguracyjne
rm -f /etc/enigma2/iptv_dream_v5.conf
rm -f /etc/enigma2/iptv_dream_v5.1.conf
rm -f /tmp/iptv_dream_v5*
rm -rf /tmp/iptv_dream_v5*

# Wyczyść cache Enigma2
echo "Clearing Enigma2 cache..."
init 4
sleep 2
rm -rf /tmp/*.cache
rm -rf /tmp/enigma2*
init 3
```

### **Krok 5: Zrestartuj Enigma 2**

```bash
# Pełny restart Enigma2
init 4
sleep 3
init 3
```

### **Krok 6: Sprawdź Wersję**

Po restarcie:
1. Wejdź w Menu → Pluginy
2. Szukaj **"IPTV Dream v6.0"**
3. W opisie powinno być **"Ultra-szybka wtyczka IPTV - REWOLUCJA! (v6.0)"**
4. **WERSJA 6.0 JEST GOTOWA!** 🎉

## 🔄 **Alternatywna Metoda - Pełna Reinstalacja**

Jeśli powyższe nie działa:

### **Czysta Instalacja v6.0**

1. **Zapisz swoje playlisty** (jeśli masz jakieś zapisane)
2. **Usuń CAŁKOWICIE starą wersję**:
   ```bash
   rm -rf /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream*
   rm -f /etc/enigma2/iptv_dream_*
   rm -rf /tmp/iptv_dream_*
   ```

3. **Zrestartuj box**:
   ```bash
   reboot
   ```

4. **Zainstaluj v6.0 od nowa** według instrukcji z `COMPLETE_INSTALLATION_v6.0.md`

## 🐛 **Rozwiązywanie Problemów**

### **Problem: Nadal widzę v5.1**

**Rozwiązanie 1:**
```bash
# Sprawdź czy stara wersja gdzieś istnieje
find /usr/lib/enigma2/python/Plugins/Extensions/ -name "*dream*" -type d
find /usr/lib/enigma2/python/Plugins/Extensions/ -name "*dream*" -type f

# Jeśli znajdziesz - usuń
rm -rf /path/to/old/version
```

**Rozwiązanie 2:**
```bash
# Sprawdź czy plugin.py wczytuje właściwy plik
grep -n "from.*dream" /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/plugin.py
# Powinno być: from .dream_v6 import IPTVDreamMain
```

**Rozwiązanie 3:**
```bash
# Sprawdź wersję w plugin.py
grep -n "description.*v5.1" /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/plugin.py
# Jeśli znajdziesz - zamień na v6.0
```

### **Problem: Plugin się nie ładuje**

**Sprawdź logi**:
```bash
tail -f /tmp/enigma2.log
# Lub
tail -f /var/log/enigma2.log
```

**Testuj składnię**:
```bash
cd /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/
python -m py_compile dream_v6.py
```

## 📊 **Weryfikacja Instalacji**

### **Sprawdź czy v6.0 jest zainstalowane:**

1. **W UI Enigma2**:
   - Menu → Pluginy
   - Powinno być: **IPTV Dream v6.0**
   - Opis: **Ultra-szybka wtyczka IPTV - REWOLUCJA! (v6.0)**

2. **W SSH**:
   ```bash
   # Sprawdź czy pliki istnieją
   ls -la /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/dream_v6.py
   ls -la /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/plugin.py
   
   # Sprawdź wersję w plugin.py
   grep "description.*v6.0" /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/plugin.py
   ```

3. **Testuj plugin**:
   ```bash
   cd /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/
   python -c "from dream_v6 import IPTVDreamMain; print('✅ Plugin działa!')"
   ```

## 🎯 **Nowe Funkcje v6.0 Do Przetestowania**

Po poprawnej instalacji przetestuj:

1. **Ultra-szybkie ładowanie M3U** - powinno trwać 3-6 sekund
2. **Progress bary** - podczas ładowania playlist
3. **Favorites** - dodawanie kanałów do ulubionych
4. **Statystyki** - long press 7
5. **Usuwanie danych** - RED button na playliście
6. **XXX/VOD detection** - automatyczne grupowanie

## 📞 **Pomoc**

Jeśli nadal masz problemy:
1. Sprawdź `BUG_FIXES_v6.0.md` - lista napraw
2. Uruchom `test_plugin.py` - testuje plugin
3. Sprawdź logi Enigma2
4. Skontaktuj się ze wsparciem

---

**Po wykonaniu tych kroków będziesz mieć działającą wersję 6.0!** 🎉

**Wersja**: v6.0 Aktualizacja  
**Data**: 2025-12-14  
**Status**: ✅ Gotowa instrukcja