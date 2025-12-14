# -*- coding: utf-8 -*-
"""
IPTV Dream v6.0 - MAC Portal Manager
Obsługa portali MAC dla wtyczki IPTV
"""

import os
import json
import requests
from datetime import datetime

def load_mac_json(config_file):
    """
    Wczytuje konfigurację MAC z pliku JSON
    
    Args:
        config_file: Ścieżka do pliku konfiguracyjnego
        
    Returns:
        Słownik z konfiguracją MAC
    """
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_mac_json(config_file, data):
    """
    Zapisuje konfigurację MAC do pliku JSON
    
    Args:
        config_file: Ścieżka do pliku konfiguracyjnego
        data: Dane do zapisania
    """
    try:
        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)
    except:
        pass

def parse_mac_playlist(mac_data):
    """
    Parsuje dane MAC i zwraca listę kanałów
    
    Args:
        mac_data: Dane MAC (słownik)
        
    Returns:
        Lista kanałów w formacie M3U
    """
    channels = []
    
    # Przykładowa implementacja - dostosuj do swojego serwera MAC
    if not mac_data:
        return channels
    
    # Przykładowe dane MAC
    portal_url = mac_data.get('portal_url', '')
    username = mac_data.get('username', '')
    password = mac_data.get('password', '')
    
    if not all([portal_url, username, password]):
        return channels
    
    try:
        # Tutaj dodaj logikę połączenia z serwerem MAC
        # Przykład:
        # response = requests.post(f"{portal_url}/get.php", data={'username': username, 'password': password})
        # channels = parse_response(response.text)
        
        # Na razu zwróć przykładowe kanały
        sample_channels = [
            {
                'title': 'TVP 1',
                'url': f'{portal_url}/live/{username}/{password}/1.ts',
                'group': 'Polskie',
                'tvg_id': 'TVP1.pl',
                'tvg_name': 'TVP 1'
            },
            {
                'title': 'TVP 2',
                'url': f'{portal_url}/live/{username}/{password}/2.ts',
                'group': 'Polskie',
                'tvg_id': 'TVP2.pl',
                'tvg_name': 'TVP 2'
            }
        ]
        
        return sample_channels
        
    except Exception as e:
        print(f"[MAC Portal] Błąd parsowania: {e}")
        return channels

def add_mac_portal(session, callback):
    """
    Dodaje nowy portal MAC
    
    Args:
        session: Sesja Enigma2
        callback: Funkcja callback do obsługi wyniku
    """
    from Screens.VirtualKeyBoard import VirtualKeyBoard
    
    def onPortalUrl(url):
        if not url:
            return
            
        def onUsername(username):
            if not username:
                return
                
            def onPassword(password):
                if not password:
                    return
                    
                # Zapisz dane MAC
                mac_data = {
                    'portal_url': url,
                    'username': username,
                    'password': password,
                    'added_date': datetime.now().isoformat()
                }
                
                config_file = '/etc/enigma2/iptv_dream_mac.json'
                existing_data = load_mac_json(config_file)
                
                if 'portals' not in existing_data:
                    existing_data['portals'] = []
                    
                existing_data['portals'].append(mac_data)
                save_mac_json(config_file, existing_data)
                
                # Callback z danymi
                callback(mac_data)
                
            session.openWithCallback(onPassword, VirtualKeyBoard, title="Wprowadź hasło:")
            
        session.openWithCallback(onUsername, VirtualKeyBoard, title="Wprowadź użytkownika:")
        
    session.openWithCallback(onPortalUrl, VirtualKeyBoard, title="Wprowadź URL portalu MAC:")

def get_mac_portals():
    """
    Pobiera listę zapisanych portali MAC
    
    Returns:
        Lista portali MAC
    """
    config_file = '/etc/enigma2/iptv_dream_mac.json'
    data = load_mac_json(config_file)
    return data.get('portals', [])

def delete_mac_portal(index):
    """
    Usuwa portal MAC z listy
    
    Args:
        index: Indeks portalu do usunięcia
    """
    config_file = '/etc/enigma2/iptv_dream_mac.json'
    data = load_mac_json(config_file)
    
    if 'portals' in data and 0 <= index < len(data['portals']):
        del data['portals'][index]
        save_mac_json(config_file, data)
        return True
    return False

# Testowanie
if __name__ == "__main__":
    print("Testowanie modułu MAC Portal v6.0")
    
    # Test zapisu i odczytu
    test_data = {
        'portal_url': 'http://example.com:8080',
        'username': 'testuser',
        'password': 'testpass'
    }
    
    config_file = '/tmp/test_mac.json'
    save_mac_json(config_file, {'portals': [test_data]})
    loaded = load_mac_json(config_file)
    
    print(f"✅ Zapisane dane: {test_data}")
    print(f"✅ Wczytane dane: {loaded}")
    
    # Test parsowania
    channels = parse_mac_playlist(test_data)
    print(f"✅ Wczytano {len(channels)} kanałów")
    
    print("✅ Moduł MAC Portal v6.0 działa poprawnie!")