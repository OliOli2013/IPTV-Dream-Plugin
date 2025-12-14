# -*- coding: utf-8 -*-
"""
IPTV Dream - Picon Manager
Zarządzanie pikonami dla kanałów
"""

import os
import requests
import hashlib
from PIL import Image

class PiconManager:
    """Menadżer pikonów"""
    
    def __init__(self, picon_dir="/usr/share/enigma2/picon/", cache_dir="/tmp/picon_cache/"):
        self.picon_dir = picon_dir
        self.cache_dir = cache_dir
        
        # Stwórz katalogi jeśli nie istnieją
        os.makedirs(self.picon_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def get_picon_path(self, channel_name):
        """
        Zwraca ścieżkę do pikona dla kanału
        
        Args:
            channel_name: Nazwa kanału
            
        Returns:
            Ścieżka do pliku pikona
        """
        # Normalizacja nazwy
        clean_name = self._clean_channel_name(channel_name)
        picon_file = f"{clean_name}.png"
        return os.path.join(self.picon_dir, picon_file)
        
    def _clean_channel_name(self, name):
        """Czyści nazwę kanału dla pikona"""
        # Usuń niepotrzebne znaki
        clean = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_'))
        clean = clean.replace(' ', '_').replace('-', '_')
        return clean.upper()
        
    def download_picon(self, channel_name, url):
        """
        Pobiera pikona z URL
        
        Args:
            channel_name: Nazwa kanału
            url: URL pikona
            
        Returns:
            True jeśli pobranie się udało
        """
        if not url:
            return False
            
        try:
            # Pobierz pikona
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Zapisz pikona
            picon_path = self.get_picon_path(channel_name)
            with open(picon_path, 'wb') as f:
                f.write(response.content)
                
            # Opcjonalnie: przeskaluj pikona
            self._resize_picon(picon_path)
            
            return True
            
        except Exception as e:
            print(f"[PiconManager] Błąd pobierania pikona: {e}")
            return False
            
    def _resize_picon(self, picon_path, size=(220, 132)):
        """Zmienia rozmiar pikona"""
        try:
            with Image.open(picon_path) as img:
                img = img.resize(size, Image.Resampling.LANCZOS)
                img.save(picon_path, "PNG")
        except:
            pass
            
    def generate_picon(self, channel_name, text=None, color="blue"):
        """
        Generuje pikona z tekstem
        
        Args:
            channel_name: Nazwa kanału
            text: Tekst na pikona (opcjonalnie)
            color: Kolor tła
            
        Returns:
            True jeśli generowanie się udało
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Rozmiar pikona
            width, height = 220, 132
            
            # Stwórz obraz
            img = Image.new('RGBA', (width, height), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Tło
            if color == "blue":
                bg_color = (0, 100, 200, 255)
            elif color == "red":
                bg_color = (200, 0, 0, 255)
            elif color == "green":
                bg_color = (0, 150, 0, 255)
            else:
                bg_color = (100, 100, 100, 255)
                
            draw.rectangle([(0, 0), (width, height)], fill=bg_color)
            
            # Tekst
            if text is None:
                text = self._get_initials(channel_name)
                
            # Znajdź czcionkę
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
            except:
                font = ImageFont.load_default()
                
            # Wymiary tekstu
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Centruj tekst
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            # Rysuj tekst
            draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
            
            # Zapisz pikona
            picon_path = self.get_picon_path(channel_name)
            img.save(picon_path, "PNG")
            
            return True
            
        except Exception as e:
            print(f"[PiconManager] Błąd generowania pikona: {e}")
            return False
            
    def _get_initials(self, channel_name):
        """Zwraca inicjały nazwy kanału"""
        words = channel_name.split()
        if len(words) >= 2:
            return "".join(word[0] for word in words[:2]).upper()
        elif len(words) == 1:
            return words[0][:3].upper()
        else:
            return "TV"
            
    def get_picon_url(self, channel_name, tvg_logo=None):
        """
        Zwraca URL pikona dla kanału
        
        Args:
            channel_name: Nazwa kanału
            tvg_logo: URL z M3U (opcjonalnie)
            
        Returns:
            URL pikona lub None
        """
        # Najpierw sprawdź czy jest URL w M3U
        if tvg_logo and tvg_logo.startswith('http'):
            return tvg_logo
            
        # Próbuj znaleźć pikona na serwerach
        picon_servers = [
            "https://picons.eu/logo/",
            "https://picons.me/logo/",
            "https://example.com/picons/"  # Dodaj więcej serwerów
        ]
        
        clean_name = self._clean_channel_name(channel_name)
        
        for server in picon_servers:
            url = f"{server}{clean_name}.png"
            if self._check_url(url):
                return url
                
        return None
        
    def _check_url(self, url):
        """Sprawdza czy URL działa"""
        try:
            response = requests.head(url, timeout=5)
            return response.status_code == 200
        except:
            return False
            
    def cache_picon(self, channel_name, url):
        """
        Cache'uje pikona
        
        Args:
            channel_name: Nazwa kanału
            url: URL pikona
            
        Returns:
            Ścieżka do pikona w cache
        """
        try:
            # Hash URL dla nazwy pliku cache
            url_hash = hashlib.md5(url.encode()).hexdigest()
            cache_file = os.path.join(self.cache_dir, f"{url_hash}.png")
            
            # Sprawdź czy już jest w cache
            if os.path.exists(cache_file):
                return cache_file
                
            # Pobierz i zapisz w cache
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            with open(cache_file, 'wb') as f:
                f.write(response.content)
                
            return cache_file
            
        except Exception as e:
            print(f"[PiconManager] Błąd cache'owania: {e}")
            return None
            
    def has_picon(self, channel_name):
        """
        Sprawdza czy kanał ma pikona
        
        Args:
            channel_name: Nazwa kanału
            
        Returns:
            True jeśli pikona istnieje
        """
        picon_path = self.get_picon_path(channel_name)
        return os.path.exists(picon_path)
        
    def list_picons(self):
        """Zwraca listę wszystkich pikonów"""
        picons = []
        for file in os.listdir(self.picon_dir):
            if file.endswith('.png'):
                picons.append(file[:-4])  # Usuń .png
        return sorted(picons)
        
    def delete_picon(self, channel_name):
        """
        Usuwa pikona
        
        Args:
            channel_name: Nazwa kanału
        """
        picon_path = self.get_picon_path(channel_name)
        if os.path.exists(picon_path):
            os.remove(picon_path)
            
    def cleanup_cache(self, max_age_days=7):
        """
        Czyści stary cache
        
        Args:
            max_age_days: Maksymalny wiek plików w dniach
        """
        try:
            import glob
            cache_files = glob.glob(os.path.join(self.cache_dir, "*.png"))
            
            for file in cache_files:
                file_age = (time.time() - os.path.getmtime(file)) / 86400
                if file_age > max_age_days:
                    os.remove(file)
                    
        except:
            pass
            
# Globalna instancja
picon_manager = PiconManager()

def get_picon_manager():
    """Zwraca globalną instancję menadżera pikonów"""
    return picon_manager