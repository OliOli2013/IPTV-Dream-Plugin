# -*- coding: utf-8 -*-
"""
IPTV Dream v6.0 - MENADŻER KONFIGURACJI
- Inteligentna konfiguracja
- Automatyczne ustawienia
- Profile użytkownika
- Historia operacji
"""

import json, os, time, hashlib
from datetime import datetime

class ConfigManager:
    """Zaawansowany menadżer konfiguracji wtyczki."""
    
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = self.load_config()
        self.ensure_defaults()
    
    def ensure_defaults(self):
        """Upewnia się, że istnieją wszystkie domyślne ustawienia."""
        defaults = {
            "version": "6.4",
            "language": "pl",
            "debug": False,
            "log_file": "/tmp/iptvdream.log",
            "ssl_verify": False,
            "net_timeout_connect": 7,
            "net_timeout_read": 30,
            "net_retries": 2,
            "net_backoff": 0.8,
            "service_type": "4097",
            "auto_update": True,
            "webif_enabled": False,
            "webif_port": 9999,
            "cache_enabled": True,
            "cache_max_age": 3600,
            "streaming_enabled": True,
            "progress_bar": True,
            "performance_monitoring": True,
            "epg_auto_install": True,
            "picon_auto_download": True,
            "favorites_auto_backup": True,
            "last_url": "",
            "last_playlist": None,
            "load_history": [],
            "performance_stats": {
                "total_loads": 0,
                "total_channels": 0,
                "total_time": 0,
                "errors": 0
            },
            "user_preferences": {
                "show_adult_channels": True,
                "show_vod_channels": True,
                "auto_group_channels": True,
                "prefer_hd_quality": True,
                "download_picons": True,
                "epg_sources": []
            },
            "shortcuts": {
                "favorite_url": "",
                "quick_load_url": ""
            },
            "notifications": {
                "show_load_complete": True,
                "show_errors": True,
                "show_updates": True
            }
        }
        
        # Dodaj brakujące ustawienia
        for key, value in defaults.items():
            if key not in self.config:
                self.config[key] = value
        
        self.save_config()
    
    def load_config(self):
        """Wczytuje konfigurację z pliku."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[IPTVDreamV6] Błąd ładowania konfiguracji: {e}")
        
        return {}
    
    def save_config(self):
        """Zapisuje konfigurację do pliku."""
        try:
            # Upewnij się, że katalog istnieje
            config_dir = os.path.dirname(self.config_file)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[IPTVDreamV6] Błąd zapisywania konfiguracji: {e}")
    
    def get(self, key, default=None):
        """Pobiera wartość z konfiguracji."""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Ustawia wartość w konfiguracji."""
        self.config[key] = value
        self.save_config()
    
    def update_performance_stats(self, channel_count, load_time, error=False):
        """Aktualizuje statystyki wydajności."""
        stats = self.get("performance_stats", {})
        stats["total_loads"] = stats.get("total_loads", 0) + 1
        stats["total_channels"] = stats.get("total_channels", 0) + channel_count
        stats["total_time"] = stats.get("total_time", 0) + load_time
        if error:
            stats["errors"] = stats.get("errors", 0) + 1
        
        self.set("performance_stats", stats)
    
    def get_performance_stats(self):
        """Zwraca statystyki wydajności."""
        stats = self.get("performance_stats", {})
        
        total_loads = stats.get("total_loads", 0)
        total_time = stats.get("total_time", 0)
        total_channels = stats.get("total_channels", 0)
        
        if total_loads > 0:
            avg_time = total_time / total_loads
            avg_channels = total_channels / total_loads
            efficiency = total_channels / total_time if total_time > 0 else 0
        else:
            avg_time = avg_channels = efficiency = 0
        
        return {
            "Załadowane playlisty": total_loads,
            "Kanały łącznie": total_channels,
            "Błędy": stats.get("errors", 0),
            "Średni czas": f"{avg_time:.1f}s",
            "Średnio kanałów": f"{avg_channels:.0f}",
            "Wydajność": f"{efficiency:.0f} kan/s" if efficiency > 0 else "N/A"
        }
    
    def add_to_history(self, url, name, channel_count, load_time, success=True):
        """Dodaje wpis do historii ładowania."""
        history = self.get("load_history", [])
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "name": name,
            "channels": channel_count,
            "load_time": round(load_time, 1),
            "success": success
        }
        
        history.insert(0, entry)
        
        # Zachowaj tylko ostatnie 50 wpisów
        history = history[:50]
        
        self.set("load_history", history)
    
    def get_load_history(self):
        """Zwraca historię ładowania."""
        return self.get("load_history", [])
    
    def get_user_preferences(self):
        """Zwraca preferencje użytkownika."""
        return self.get("user_preferences", {})
    
    def set_user_preference(self, key, value):
        """Ustawia preferencję użytkownika."""
        prefs = self.get("user_preferences", {})
        prefs[key] = value
        self.set("user_preferences", prefs)
    
    def get_shortcuts(self):
        """Zwraca skróty użytkownika."""
        return self.get("shortcuts", {})
    
    def set_shortcut(self, key, value):
        """Ustawia skrót."""
        shortcuts = self.get("shortcuts", {})
        shortcuts[key] = value
        self.set("shortcuts", shortcuts)
    
    def get_notifications_settings(self):
        """Zwraca ustawienia powiadomień."""
        return self.get("notifications", {})
    
    def set_notification(self, key, value):
        """Ustawia powiadomienie."""
        notifications = self.get("notifications", {})
        notifications[key] = value
        self.set("notifications", notifications)
    
    def should_show_notification(self, notification_type):
        """Sprawdza czy pokazać powiadomienie."""
        notifications = self.get_notifications_settings()
        return notifications.get(notification_type, True)
    
    def export_config(self, export_file):
        """Eksportuje konfigurację."""
        try:
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except:
            return False
    
    def import_config(self, import_file):
        """Importuje konfigurację."""
        try:
            with open(import_file, 'r', encoding='utf-8') as f:
                new_config = json.load(f)
            
            # Zapisz backup
            backup_file = f"{self.config_file}.backup_{int(time.time())}"
            self.export_config(backup_file)
            
            # Zaimportuj nową konfigurację
            self.config = new_config
            self.save_config()
            
            return True, backup_file
        except Exception as e:
            return False, str(e)
    
    def reset_to_defaults(self):
        """Resetuje konfigurację do domyślnych wartości."""
        # Zapisz backup
        backup_file = f"{self.config_file}.backup_{int(time.time())}"
        self.export_config(backup_file)
        
        # Wyczyść konfigurację
        self.config = {}
        self.ensure_defaults()
        
        return backup_file
    
    def get_cache_info(self):
        """Zwraca informacje o cache."""
        cache_dir = self.get("cache_dir", "/tmp/iptvdream_cache")
        if os.path.exists(cache_dir):
            files = os.listdir(cache_dir)
            total_size = sum(os.path.getsize(os.path.join(cache_dir, f)) for f in files)
            return {
                "Pliki w cache": len(files),
                "Rozmiar cache": f"{total_size / 1024 / 1024:.1f} MB",
                "Ścieżka": cache_dir
            }
        return {"Pliki w cache": 0, "Rozmiar cache": "0 MB", "Ścieżka": cache_dir}
    
    def clear_cache(self):
        """Czyści cache."""
        cache_dir = self.get("cache_dir", "/tmp/iptvdream_cache")
        if os.path.exists(cache_dir):
            import shutil
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir, exist_ok=True)
            return True
        return False

# NOWE: Klasa do zarządzania ulubionymi
class FavoritesManager:
    """Menadżer ulubionych kanałów."""
    
    def __init__(self):
        self.favorites_file = "/etc/enigma2/iptvdream_v6_favorites.json"
        self.favorites = self.load_favorites()
    
    def load_favorites(self):
        """Wczytuje ulubione."""
        try:
            if os.path.exists(self.favorites_file):
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return []
    
    def save_favorites(self):
        """Zapisuje ulubione."""
        try:
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def add_favorite(self, channel):
        """Dodaje kanał do ulubionych."""
        # Sprawdź duplikaty
        for fav in self.favorites:
            if fav.get("url") == channel.get("url"):
                return False
        
        # Dodaj timestamp
        channel["added_timestamp"] = datetime.now().isoformat()
        self.favorites.append(channel)
        self.save_favorites()
        return True
    
    def remove_favorite(self, channel_url):
        """Usuwa kanał z ulubionych."""
        self.favorites = [fav for fav in self.favorites if fav.get("url") != channel_url]
        self.save_favorites()
    
    def get_favorites(self):
        """Zwraca listę ulubionych."""
        return self.favorites
    
    def is_favorite(self, channel_url):
        """Sprawdza czy kanał jest ulubiony."""
        return any(fav.get("url") == channel_url for fav in self.favorites)
    
    def clear_favorites(self):
        """Czyści ulubione."""
        self.favorites = []
        self.save_favorites()
    
    def export_favorites(self, export_file):
        """Eksportuje ulubione."""
        try:
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, indent=2, ensure_ascii=False)
            return True
        except:
            return False
    
    def import_favorites(self, import_file):
        """Importuje ulubione."""
        try:
            with open(import_file, 'r', encoding='utf-8') as f:
                new_favorites = json.load(f)
            
            # Połącz z istniejącymi
            for fav in new_favorites:
                if not self.is_favorite(fav.get("url")):
                    self.favorites.append(fav)
            
            self.save_favorites()
            return True
        except:
            return False