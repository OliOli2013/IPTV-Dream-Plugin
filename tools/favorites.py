# -*- coding: utf-8 -*-
"""
IPTV Dream - Favorites Manager
Zarządzanie ulubionymi kanałami
"""

import os
import json

class FavoritesManager:
    """Menadżer ulubionych kanałów"""
    
    def __init__(self, config_file="/etc/enigma2/iptv_dream_favorites.json"):
        self.config_file = config_file
        self.favorites = self._load_favorites()
        
    def _load_favorites(self):
        """Wczytuje ulubione z pliku"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"groups": {}, "channels": {}}
        
    def _save_favorites(self):
        """Zapisuje ulubione do pliku"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.favorites, f, indent=2)
        except:
            pass
            
    def add_to_favorites(self, channel, group_name="Ulubione"):
        """
        Dodaje kanał do ulubionych
        
        Args:
            channel: Słownik z danymi kanału
            group_name: Nazwa grupy ulubionych
        """
        if group_name not in self.favorites["groups"]:
            self.favorites["groups"][group_name] = {
                "name": group_name,
                "created": "",
                "channels": []
            }
            
        channel_id = channel.get("url", channel.get("title", ""))
        if channel_id not in self.favorites["channels"]:
            self.favorites["channels"][channel_id] = channel
            
        if channel_id not in self.favorites["groups"][group_name]["channels"]:
            self.favorites["groups"][group_name]["channels"].append(channel_id)
            
        self._save_favorites()
        
    def remove_from_favorites(self, channel_id, group_name=None):
        """
        Usuwa kanał z ulubionych
        
        Args:
            channel_id: ID kanału
            group_name: Nazwa grupy (opcjonalnie)
        """
        if group_name and group_name in self.favorites["groups"]:
            if channel_id in self.favorites["groups"][group_name]["channels"]:
                self.favorites["groups"][group_name]["channels"].remove(channel_id)
                
        # Usuń kanał z globalnej listy jeśli nie ma go w żadnej grupie
        channel_in_groups = False
        for group in self.favorites["groups"].values():
            if channel_id in group["channels"]:
                channel_in_groups = True
                break
                
        if not channel_in_groups and channel_id in self.favorites["channels"]:
            del self.favorites["channels"][channel_id]
            
        self._save_favorites()
        
    def get_favorite_groups(self):
        """Zwraca listę grup ulubionych"""
        return list(self.favorites["groups"].keys())
        
    def get_favorites_in_group(self, group_name):
        """
        Zwraca kanały z danej grupy
        
        Args:
            group_name: Nazwa grupy
            
        Returns:
            Lista kanałów
        """
        if group_name not in self.favorites["groups"]:
            return []
            
        channels = []
        for channel_id in self.favorites["groups"][group_name]["channels"]:
            if channel_id in self.favorites["channels"]:
                channels.append(self.favorites["channels"][channel_id])
                
        return channels
        
    def is_favorite(self, channel_id):
        """
        Sprawdza czy kanał jest w ulubionych
        
        Args:
            channel_id: ID kanału
            
        Returns:
            True jeśli kanał jest ulubiony
        """
        return channel_id in self.favorites["channels"]
        
    def create_group(self, group_name):
        """
        Tworzy nową grupę ulubionych
        
        Args:
            group_name: Nazwa grupy
        """
        if group_name not in self.favorites["groups"]:
            self.favorites["groups"][group_name] = {
                "name": group_name,
                "created": "",
                "channels": []
            }
            self._save_favorites()
            
    def delete_group(self, group_name):
        """
        Usuwa grupę ulubionych
        
        Args:
            group_name: Nazwa grupy
        """
        if group_name in self.favorites["groups"]:
            # Usuń kanały które są tylko w tej grupie
            channels_to_check = self.favorites["groups"][group_name]["channels"][:]
            
            for channel_id in channels_to_check:
                self.remove_from_favorites(channel_id, group_name)
                
            # Usuń grupę
            del self.favorites["groups"][group_name]
            self._save_favorites()
            
    def export_favorites(self, format="json"):
        """
        Eksportuje ulubione
        
        Args:
            format: Format eksportu (json/m3u)
            
        Returns:
            Dane do eksportu
        """
        if format == "json":
            return self.favorites
        elif format == "m3u":
            m3u_content = "#EXTM3U\n"
            for channel in self.favorites["channels"].values():
                title = channel.get("title", "Unknown")
                url = channel.get("url", "")
                group = channel.get("group", "Ulubione")
                tvg_id = channel.get("tvg_id", "")
                tvg_name = channel.get("tvg_name", title)
                tvg_logo = channel.get("tvg_logo", "")
                
                extinf = f'#EXTINF:-1'
                if tvg_id:
                    extinf += f' tvg-id="{tvg_id}"'
                if tvg_name:
                    extinf += f' tvg-name="{tvg_name}"'
                if tvg_logo:
                    extinf += f' tvg-logo="{tvg_logo}"'
                if group:
                    extinf += f' group-title="{group}"'
                
                extinf += f',{title}\n'
                m3u_content += extinf + url + "\n"
                
            return m3u_content
            
    def import_favorites(self, data, format="json"):
        """
        Importuje ulubione
        
        Args:
            data: Dane do importu
            format: Format danych (json/m3u)
        """
        if format == "json":
            if "groups" in data and "channels" in data:
                self.favorites = data
                self._save_favorites()
        elif format == "m3u":
            # Import z M3U - uproszczona wersja
            pass

# Globalna instancja
favorites_manager = FavoritesManager()

def get_favorites_manager():
    """Zwraca globalną instancję menadżera ulubionych"""
    return favorites_manager