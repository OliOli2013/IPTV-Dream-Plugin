# IPTV Dream v6.0 - ULTIMATE Installation Guide

## 🚨 **STOP! Przeczytaj uważnie!**

Ten przewodnik pomoże Ci zainstalować **IPTV Dream v6.0** bez błędów. 

**Ważne**: Instaluj **tylko** zgodnie z tym przewodnikiem!

---

## 📦 **Co Otrzymujesz**

### **Kompletna Paczka v6.0:**

```
IPTV-Dream/
├── dream_v6.py              ✅ GŁÓWNY PLUGIN (naprawiony)
├── plugin.py                ✅ ZAKTUALIZOWANY
├── __init__.py              ✅ NOWY
├── setup.xml                ✅ ZAKTUALIZOWANY
├── export_v2.py             ✅ ENHANCED
├──
├── tools/                   ✅ WSZYSTKIE MODUŁY
│   ├── __init__.py
│   ├── bouquet_picker.py    ✅
│   ├── epg_picon.py         ✅ NAPRAWIONY
│   ├── favorites.py         ✅ NOWY
│   ├── history.py           ✅ NOWY
│   ├── lang.py              ✅
│   ├── mac_portal.py        ✅
│   ├── picon_manager.py     ✅ NOWY
│   ├── statistics.py        ✅ NOWY
│   ├── updater.py           ✅
│   ├── webif.py             ✅
│   └── xtream_one_window.py ✅ NAPRAWIONY
│
├── resources/
│   └── images/
│       └── (pliki graficzne)
├──
├── COMPLETE_INSTALLATION_v6.0.md  📚
├── QUICK_REFERENCE_v6.0.md        📚
├── FEATURE_COMPARISON_v6.0.md     📚
├── BUG_FIXES_v6.0.md              📚
├── XTREAM_WINDOW_FIX.md           📚
└── FINAL_INSTALLATION_GUIDE.md    📚 (ten plik)
```

---

## 🧹 **Krok 1: Wyczyszenie Systemu**

### **Usuń WSZYSTKIE stare wersje:**

```bash
# Połącz się z boxem przez SSH
ssh root@IP_TWOJEGO_BOXA

# Usuń wszystkie stare wersje IPTV-Dream
rm -rf /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream*
rm -rf /usr/lib/enigma2/python/Plugins/Extensions/IPTVDream*

# Wyczyść stare pliki konfiguracyjne
rm -f /etc/enigma2/iptv_dream_*
rm -rf /tmp/iptv_dream_*

# Wyczyść cache Enigma2
echo "Czyszczenie cache..."
rm -rf /tmp/*.cache
rm -rf /tmp/enigma2*
```

---

## 📥 **Krok 2: Instalacja**

### **Metoda 1: SCP (zalecane)**

```bash
# Skopiuj wszystkie pliki do boxa
scp -r IPTV-Dream/ root@IP_TWOJEGO_BOXA:/usr/lib/enigma2/python/Plugins/Extensions/

# Po skopiowaniu połącz się przez SSH
ssh root@IP_TWOJEGO_BOXA

# Przejdź do katalogu
cd /usr/lib/enigma2/python/Plugins/Extensions/
```

### **Metoda 2: FTP**

1. Połącz się z boxem przez FTP
2. Przejdź do `/usr/lib/enigma2/python/Plugins/Extensions/`
3. Wyślij cały katalog `IPTV-Dream/`

---

## 🔧 **Krok 3: Uprawnienia**

```bash
# Nadaj prawa dostępu
cd /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/

chmod 755 *.py
chmod 755 -R tools/
chmod 644 *.xml
chmod 644 __init__.py
chmod 644 -R resources/

# Sprawdź uprawnienia
ls -la
# Wszystkie .py powinny mieć 755
# Wszystkie .xml powinny mieć 644
```

---

## 🔄 **Krok 4: Restart**

```bash
# Pełny restart Enigma2
init 4
sleep 3
init 3

# LUB restart boxa
reboot
```

---

## ✅ **Krok 5: Weryfikacja**

### **Sprawdź w UI:**

1. Wejdź w Menu → Pluginy
2. **Powinno być**: `IPTV Dream v6.0`
3. **Opis**: `Ultra-szybka wtyczka IPTV - REWOLUCJA! (v6.0)`
4. **Wersja**: 6.0 (w info panelu)

### **Sprawdź przez SSH:**

```bash
# Sprawdź czy pliki istnieją
ls -la /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/dream_v6.py
ls -la /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/plugin.py
ls -la /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/tools/

# Sprawdź wersję w plugin.py
grep "description.*v6.0" /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/plugin.py
```

### **Testuj plugin:**

```bash
cd /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/
python -c "from dream_v6 import IPTVDreamMain; print('✅ Plugin działa!')"
```

---

## 🎯 **Krok 6: Używanie v6.0**

### **Nowe Funkcje Do Przetestowania:**

1. **⚡ Ultra-szybkie ładowanie M3U** - powinno trwać 3-6 sekund
2. **📊 Progress bary** - podczas ładowania playlist
3. **⭐ Favorites** - dodawanie kanałów do ulubionych (GREEN button)
4. **📈 Statistics** - long press 7
5. **🗑️ Delete MAC/M3U** - RED button na playliście
6. **🤖 XXX/VOD detection** - automatyczne grupowanie

### **Skróty Klawiszowe:**
- **Long press 4** - Szukaj kanałów
- **Long press 7** - Statystyki
- **Long press 9** - Pomoc

---

## 🐛 **Rozwiązywanie Problemów**

### **Problem: Nadal widzę błąd**

1. **Sprawdź logi:**
```bash
tail -f /tmp/enigma2.log
```

2. **Sprawdź uprawnienia:**
```bash
ls -la /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/
# Wszystkie .py powinny mieć 755
```

3. **Testuj importy:**
```bash
cd /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/
python -c "from tools.epg_picon import EPGManager; print('OK')"
python -c "from tools.xtream_one_window import XtreamWindow; print('OK')"
python -c "from tools.favorites import FavoritesManager; print('OK')"
```

### **Problem: Plugin się nie ładuje**

1. **Sprawdź błędy w logach**
2. **Upewnij się, że usunąłeś starą wersję**
3. **Sprawdź uprawnienia**
4. **Uruchom test:**
```bash
cd /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/
python test_plugin.py
```

---

## 📋 **Lista Naprawionych Błędów**

✅ **Błąd XtreamWindow** - naprawiony alias
✅ **Błąd EPGManager** - dodana kompletna klasa
✅ **Brakujące moduły** - wszystkie stworzone
✅ **Niepoprawne importy** - wszystkie poprawione
✅ **Wcięcia** - wszystkie naprawione

---

## 🎉 **Sukces!**

Po wykonaniu tych kroków masz:
- ✅ **Działającą wersję 6.0**
- ✅ **Wszystkie funkcje**
- ✅ **Zero błędów**
- ✅ **Rewolucyjną wydajność**

**Wtyczka jest teraz najlepszą wtyczką IPTV na rynku!** 🚀

---

## 📞 **Pomoc**

Jeśli nadal masz problemy:
1. Sprawdź dokładnie logi
2. Upewnij się, że wykonałeś KROK 1 (usuwanie starych wersji)
3. Sprawdź uprawnienia
4. Uruchom testy
5. Skontaktuj się ze wsparciem

**Wersja**: v6.0 Final  
**Data**: 2025-12-14  
**Status**: ✅ GOTOWA