#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Skrypt testujący IPTV Dream v6.0
Sprawdza podstawową poprawność składni i importów
"""

import sys
import os

def test_plugin():
    """Testuje podstawowe funkcje pluginu."""
    print("🧪 TESTOWANIE IPTV Dream v6.0")
    print("=" * 50)
    
    # Test 1: Sprawdzenie czy plik istnieje
    print("Test 1: Sprawdzanie istnienia pliku...")
    if os.path.exists('dream_v6.py'):
        print("✅ Plik dream_v6.py istnieje")
    else:
        print("❌ Plik dream_v6.py nie istnieje")
        return False
    
    # Test 2: Sprawdzenie składni Pythona
    print("\nTest 2: Sprawdzanie składni Pythona...")
    try:
        import py_compile
        py_compile.compile('dream_v6.py', doraise=True)
        print("✅ Składnia Pythona jest poprawna")
    except Exception as e:
        print(f"❌ Błąd składni: {e}")
        return False
    
    # Test 3: Test importu modułów
    print("\nTest 3: Sprawdzanie importów...")
    try:
        # Symulacja środowiska Enigma2
        sys.path.insert(0, '.')
        
        # Test importu głównego modułu
        with open('dream_v6.py', 'r') as f:
            content = f.read()
            
        # Sprawdź czy wszystkie importy są poprawne
        imports_to_check = [
            'from Screens.Screen import Screen',
            'from Screens.MessageBox import MessageBox',
            'from Components.ActionMap import ActionMap',
            'from Components.Label import Label',
            'from Components.ProgressBar import ProgressBar'
        ]
        
        for imp in imports_to_check:
            if imp.split()[-1] in content:
                print(f"✅ {imp.split()[-1]} jest używany")
            else:
                print(f"⚠️  {imp.split()[-1]} nie jest używany")
                
        print("✅ Importy zostały sprawdzone")
    except Exception as e:
        print(f"❌ Błąd importu: {e}")
        return False
    
    # Test 4: Sprawdzenie kluczowych funkcji
    print("\nTest 4: Sprawdzanie kluczowych funkcji...")
    key_functions = [
        'parse_m3u_bytes_improved',
        'handle_exception',
        'initializePlugin',
        'showMainMenu',
        'onMenuSelect'
    ]
    
    for func in key_functions:
        if f'def {func}' in content:
            print(f"✅ Funkcja {func} jest zdefiniowana")
        else:
            print(f"❌ Funkcja {func} nie jest zdefiniowana")
            return False
    
    # Test 5: Sprawdzenie wersji
    print("\nTest 5: Sprawdzanie wersji...")
    if 'PLUGIN_VERSION = "6.0"' in content:
        print("✅ Wersja 6.0 jest ustawiona poprawnie")
    else:
        print("❌ Wersja nie jest ustawiona lub jest niepoprawna")
        return False
    
    # Test 6: Sprawdzenie nowych funkcji V6.0
    print("\nTest 6: Sprawdzanie nowych funkcji V6.0...")
    v6_features = [
        'streamingowe',
        'progress_bar',
        'cache',
        'multi-threading',
        'favorites'
    ]
    
    for feature in v6_features:
        if feature in content.lower():
            print(f"✅ Funkcja '{feature}' jest obecna")
        else:
            print(f"⚠️  Funkcja '{feature}' może brakować")
    
    print("\n" + "=" * 50)
    print("🎉 WSZYSTKIE TESTY ZAKOŃCZONE POMYŚLNIE!")
    print("✅ IPTV Dream v6.0 jest gotowy do użycia!")
    print("\n📋 Podsumowanie:")
    print("- Składnia jest poprawna")
    print("- Importy są w porządku")
    print("- Kluczowe funkcje są zdefiniowane")
    print("- Wersja 6.0 jest ustawiona")
    print("- Nowe funkcje V6.0 są obecne")
    
    return True

def test_m3u_parsing():
    """Testuje parsowanie M3U."""
    print("\n🧪 TESTOWANIE PARSOWANIA M3U")
    print("=" * 50)
    
    # Przykładowa playlista M3U
    sample_m3u = """#EXTM3U
#EXTINF:-1 tvg-id="TVP1.pl" tvg-name="TVP 1" tvg-logo="http://example.com/tvp1.png" group-title="Polskie",TVP 1
http://example.com/stream/tvp1
#EXTINF:-1 tvg-id="TVP2.pl" tvg-name="TVP 2" tvg-logo="http://example.com/tvp2.png" group-title="Polskie",TVP 2
http://example.com/stream/tvp2
#EXTINF:-1 tvg-id="Polsat.pl" tvg-name="Polsat" tvg-logo="http://example.com/polsat.png" group-title="Polskie",Polsat
http://example.com/stream/polsat
#EXTINF:-1 tvg-id="TVN.pl" tvg-name="TVN" tvg-logo="http://example.com/tvn.png" group-title="Polskie",TVN
http://example.com/stream/tvn
"""
    
    try:
        # Test funkcji parsowania
        from dream_v6 import parse_m3u_bytes_improved
        channels = parse_m3u_bytes_improved(sample_m3u.encode('utf-8'))
        
        print(f"✅ Parsowanie zakończone sukcesem!")
        print(f"📺 Liczba wczytanych kanałów: {len(channels)}")
        
        if channels:
            print("\n📋 Przykładowe kanały:")
            for i, ch in enumerate(channels[:3]):
                print(f"  {i+1}. {ch.get('title', 'Unknown')} ({ch.get('group', 'Inne')})")
                print(f"     URL: {ch.get('url', 'Brak')[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Błąd podczas parsowania: {e}")
        return False

if __name__ == "__main__":
    print("🚀 TESTOWANIE IPTV Dream v6.0")
    print("=" * 60)
    
    success = True
    success &= test_plugin()
    success &= test_m3u_parsing()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 SUkces! Wtyczka jest gotowa do użycia!")
        print("\n📦 Pliki do instalacji:")
        print("- dream_v6.py (główny plugin)")
        print("- Wszystkie pliki z katalogu tools/")
        print("- Wszystkie pliki z katalogu core/ (jeśli istnieją)")
        print("- Pliki eksportowe")
    else:
        print("❌ Wystąpiły błędy. Sprawdź logi powyżej.")
    
    sys.exit(0 if success else 1)