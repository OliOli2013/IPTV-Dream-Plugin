# IPTV Dream v6.0 - Naprawa Błędu XtreamWindow

## 🚨 **Problem**

Błąd: `cannot import name 'XtreamWindow' from 'Plugins.Extensions.IPTVDream.tools.xtream_one_window'`

## 🔍 **Przyczyna**

Plik `xtream_one_window.py` zawiera klasę `XtreamOneWindow`, ale plugin próbuje zaimportować `XtreamWindow`.

## ✅ **Rozwiązanie**

### **Opcja 1: Zaktualizowany plik (zalecane)**

Plik `xtream_one_window.py` został **naprawiony** i zawiera teraz alias:

```python
class XtreamOneWindow(Screen):
    """Okno dla Xtream Codes"""
    # ... pełna implementacja ...

# Alias dla zgodności
XtreamWindow = XtreamOneWindow
```

### **Opcja 2: Ręczna naprawa**

Jeśli masz stary plik, dodaj alias na końcu:

1. Otwórz plik `/usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/tools/xtream_one_window.py`
2. Dodaj na końcu:
```python
# Alias dla zgodności z importami
XtreamWindow = XtreamOneWindow
```

## 📦 **Zaktualizowane Pliki**

### **Do skopiowania:**
1. ✅ `dream_v6.py` - główny plugin (poprawione importy)
2. ✅ `tools/xtream_one_window.py` - z aliasem XtreamWindow
3. ✅ `tools/favorites.py` - nowy moduł
4. ✅ `tools/history.py` - nowy moduł
5. ✅ `tools/picon_manager.py` - nowy moduł
6. ✅ `tools/statistics.py` - nowy moduł

## 🚀 **Aktualizacja**

### **Krok 1: Skopiuj nowe pliki**
```bash
cp dream_v6.py /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/
cp tools/*.py /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/tools/
```

### **Krok 2: Nadaj uprawnienia**
```bash
cd /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/
chmod 755 *.py
chmod 755 -R tools/
```

### **Krok 3: Zrestartuj Enigma2**
```bash
init 4 && sleep 2 && init 3
```

## 🧪 **Testowanie**

### **Sprawdź logi:**
```bash
tail -f /tmp/enigma2.log
```

### **Sprawdź importy:**
```bash
cd /usr/lib/enigma2/python/Plugins/Extensions/IPTV-Dream/
python -c "from tools.xtream_one_window import XtreamWindow; print('OK')"
```

## 📊 **Kompatybilność**

### **Importy w dream_v6.py:**
```python
from .tools.xtream_one_window import XtreamWindow  ✅ DZIAŁA
from .tools.favorites import FavoritesManager      ✅ DZIAŁA
from .tools.statistics import StatisticsManager    ✅ DZIAŁA
from .tools.history import HistoryManager          ✅ DZIAŁA
from .tools.picon_manager import PiconManager     ✅ DZIAŁA
```

## 🎯 **Co Zobaczysz Po Naprawie**

1. **Menu**: `IPTV Dream v6.0`
2. **Opis**: `Ultra-szybka wtyczka IPTV - REWOLUCJA! (v6.0)`
3. **Funkcje**: Wszystkie v6.0 działają:
   - ⚡ Ultra-szybkie ładowanie M3U
   - 📊 Progress bary
   - ⭐ Favorites
   - 📈 Statistics (long press 7)
   - 🗑️ Delete MAC/M3U (RED button)
   - 🤖 XXX/VOD detection

## 📞 **Pomoc**

Jeśli nadal masz problemy:
1. Sprawdź czy wszystkie pliki są skopiowane
2. Sprawdź uprawnienia (powinny być 755 dla .py)
3. Sprawdź logi Enigma2
4. Uruchom test: `python test_plugin.py`

---

**Błąd został naprawiony! Plugin jest gotowy do użycia!** 🎉

**Wersja**: v6.0 Naprawiona  
**Data**: 2025-12-14  
**Status**: ✅ Gotowa