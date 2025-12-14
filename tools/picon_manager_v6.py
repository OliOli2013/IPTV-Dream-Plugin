# -*- coding: utf-8 -*-
"""
IPTV Dream v6.0 - MENADŻER PICON
- Ultra-szybkie pobieranie picon
- Inteligentne cache'owanie
- Fallback na generowane pikony
- Automatyczne skalowanie
- Wielojęzyczne nazwy
"""

import os, re, requests, time, hashlib, json
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

class PiconManager:
    """Zaawansowany menadżer picon."""
    
    def __init__(self):
        self.picon_dir = "/usr/share/enigma2/picon"
        self.cache_dir = "/tmp/iptvdream_picon_cache"
        self.temp_dir = "/tmp/iptvdream_temp"
        self.config_file = "/etc/enigma2/iptvdream_v6_picon_config.json"
        
        # Upewnij się, że katalogi istnieją
        os.makedirs(self.picon_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Konfiguracja
        self.config = self.load_config()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/*',
            'Accept-Encoding': 'gzip, deflate'
        })
        
        # Rozmiary picon
        self.picon_sizes = {
            'small': (100, 60),
            'normal': (220, 132),
            'large': (400, 240)
        }
        
        # Kolory dla generowanych picon
        self.colors = [
            ('#FF6B6B', '#FFFFFF'),  # Czerwony + Biały
            ('#4ECDC4', '#FFFFFF'),  # Turkusowy + Biały
            ('#45B7D1', '#FFFFFF'),  # Niebieski + Biały
            ('#96CEB4', '#FFFFFF'),  # Zielony + Biały
            ('#FFEAA7', '#2D3436'),  # Żółty + Czarny
            ('#DDA0DD', '#FFFFFF'),  # Fioletowy + Biały
            ('#98D8C8', '#FFFFFF'),  # Miętowy + Biały
            ('#F7DC6F', '#2D3436'),  # Złoty + Czarny
        ]

    def load_config(self):
        """Wczytuje konfigurację picon."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        
        # Domyślna konfiguracja
        return {
            "auto_download": True,
            "preferred_size": "normal",
            "generate_fallback": True,
            "cache_enabled": True,
            "cache_max_age": 86400,
            "download_timeout": 10,
            "max_concurrent_downloads": 5,
            "fallback_colors": True,
            "quality_preference": "high",
            "language_preference": "auto"
        }

    def save_config(self):
        """Zapisuje konfigurację picon."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except:
            pass

    def get_cache_key(self, url):
        """Generuje klucz cache."""
        return hashlib.md5(url.encode('utf-8')).hexdigest()

    def is_cache_valid(self, cache_file, max_age=None):
        """Sprawdza czy cache jest ważny."""
        if not max_age:
            max_age = self.config.get("cache_max_age", 86400)
        
        if not os.path.exists(cache_file):
            return False
        return (time.time() - os.path.getmtime(cache_file)) < max_age

    def download_picon(self, url, channel_name, progress_callback=None):
        """
        Pobiera picon dla kanału.
        Zwraca ścieżkę do pobranego picona lub None.
        """
        if not url or not channel_name:
            return None
        
        # Sprawdź cache
        if self.config.get("cache_enabled", True):
            cache_key = self.get_cache_key(url)
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.png")
            
            if self.is_cache_valid(cache_file):
                return cache_file
        
        # Bezpieczna nazwa pliku
        safe_name = re.sub(r'[^\w]', '_', channel_name).strip().lower()
        picon_file = os.path.join(self.picon_dir, f"{safe_name}.png")
        
        # Jeśli plik już istnieje
        if os.path.exists(picon_file):
            if self.config.get("cache_enabled", True):
                # Kopiuj do cache
                import shutil
                shutil.copy2(picon_file, cache_file)
            return picon_file
        
        try:
            # Pobieranie z timeout
            timeout = self.config.get("download_timeout", 10)
            response = self.session.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            # Sprawdź czy to obraz
            content_type = response.headers.get('content-type', '').lower()
            if 'image' not in content_type:
                raise Exception("Nieprawidłowy typ zawartości")
            
            # Zapisz plik tymczasowy
            temp_file = os.path.join(self.temp_dir, f"temp_{cache_key}.png")
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Przetwórz obraz
            processed_file = self._process_picon(temp_file, channel_name)
            
            if processed_file:
                # Przenieś do katalogu picon
                os.rename(processed_file, picon_file)
                
                # Cache
                if self.config.get("cache_enabled", True):
                    import shutil
                    shutil.copy2(picon_file, cache_file)
                
                # Wyczyść tymczasowy
                os.remove(temp_file)
                
                return picon_file
            
        except Exception as e:
            print(f"[PiconManager] Błąd pobierania picon dla {channel_name}: {e}")
            
            # Fallback na generowany picon
            if self.config.get("generate_fallback", True):
                return self.generate_picon(channel_name)
        
        return None

    def _process_picon(self, image_file, channel_name):
        """Przetwarza pobrany obraz picon."""
        try:
            # Otwórz obraz
            img = Image.open(image_file)
            
            # Konwersja do RGB jeśli potrzebne
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Skalowanie
            size_name = self.config.get("preferred_size", "normal")
            target_size = self.picon_sizes.get(size_name, (220, 132))
            
            img = img.resize(target_size, Image.Resampling.LANCZOS)
            
            # Opcjonalne: dodaj obramowanie
            if self.config.get("add_border", False):
                img = self._add_border(img)
            
            # Zapisz przetworzony obraz
            processed_file = os.path.join(self.temp_dir, f"processed_{hashlib.md5(channel_name.encode()).hexdigest()}.png")
            img.save(processed_file, "PNG", optimize=True)
            
            return processed_file
            
        except Exception as e:
            print(f"[PiconManager] Błąd przetwarzania picon: {e}")
            return None

    def generate_picon(self, channel_name, color_scheme=None):
        """Generuje picon z nazwą kanału."""
        try:
            if not color_scheme:
                color_scheme = self._select_color_scheme(channel_name)
            
            bg_color, text_color = color_scheme
            
            # Rozmiar
            size_name = self.config.get("preferred_size", "normal")
            width, height = self.picon_sizes.get(size_name, (220, 132))
            
            # Tworzenie obrazu
            img = Image.new('RGB', (width, height), color=bg_color)
            draw = ImageDraw.Draw(img)
            
            # Prostokąt tła (opcjonalnie)
            margin = 10
            draw.rectangle([margin, margin, width-margin, height-margin], 
                          outline=text_color, width=2)
            
            # Tekst
            font_size = min(width // 10, height // 6)
            
            # Spróbuj użyć wbudowanej czcionki
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            # Czyszczenie i skracanie nazwy
            display_name = self._prepare_channel_name(channel_name)
            
            # Centrowanie tekstu
            bbox = draw.textbbox((0, 0), display_name, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            # Rysowanie tekstu
            draw.text((x, y), display_name, fill=text_color, font=font, align='center')
            
            # Zapisz
            safe_name = re.sub(r'[^\w]', '_', channel_name).strip().lower()
            picon_file = os.path.join(self.picon_dir, f"{safe_name}.png")
            img.save(picon_file, "PNG", optimize=True)
            
            return picon_file
            
        except Exception as e:
            print(f"[PiconManager] Błąd generowania picon: {e}")
            return None

    def _select_color_scheme(self, channel_name):
        """Wybiera schemat kolorów dla kanału."""
        if not self.config.get("fallback_colors", True):
            return ('#000000', '#FFFFFF')
        
        # Hash nazwy kanału do wyboru koloru
        import hashlib
        hash_val = int(hashlib.md5(channel_name.encode()).hexdigest()[:8], 16)
        color_index = hash_val % len(self.colors)
        
        return self.colors[color_index]

    def _prepare_channel_name(self, channel_name):
        """Przygotowuje nazwę kanału do wyświetlenia."""
        # Czyszczenie
        clean_name = re.sub(r'[^\w\s]', '', channel_name).strip()
        
        # Skracanie jeśli za długie
        max_length = 15
        if len(clean_name) > max_length:
            words = clean_name.split()
            if len(words) > 1:
                # Skróć do inicjałów
                initials = ''.join([word[0] for word in words[:3]])
                clean_name = f"{initials}..."
            else:
                clean_name = clean_name[:max_length-3] + "..."
        
        return clean_name

    def _add_border(self, img):
        """Dodaje obramowanie do obrazu."""
        width, height = img.size
        border_width = 2
        
        # Nowy obraz z miejscem na obramowanie
        new_img = Image.new('RGB', (width + border_width*2, height + border_width*2), '#FFFFFF')
        new_img.paste(img, (border_width, border_width))
        
        # Rysowanie obramowania
        draw = ImageDraw.Draw(new_img)
        draw.rectangle([0, 0, width + border_width*2 - 1, height + border_width*2 - 1], 
                      outline='#FFFFFF', width=border_width)
        
        return new_img

    def download_picons_batch(self, channels, progress_callback=None):
        """Pobiera pikony dla listy kanałów."""
        total = len(channels)
        downloaded = 0
        failed = 0
        
        for i, channel in enumerate(channels):
            logo_url = channel.get("logo", "")
            channel_name = channel.get("title", "")
            
            if logo_url:
                try:
                    result = self.download_picon(logo_url, channel_name)
                    if result:
                        downloaded += 1
                    else:
                        failed += 1
                except:
                    failed += 1
            
            # Progress callback
            if progress_callback and i % 5 == 0:
                progress = (i / total) * 100
                progress_callback(progress, f"Pobieranie picon: {i}/{total}")
        
        return {
            "total": total,
            "downloaded": downloaded,
            "failed": failed,
            "success_rate": (downloaded / total * 100) if total > 0 else 0
        }

    def cleanup_cache(self, max_age=86400):
        """Czyści przeterminowane pliki picon."""
        try:
            if os.path.exists(self.cache_dir):
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.png'):
                        filepath = os.path.join(self.cache_dir, filename)
                        file_age = time.time() - os.path.getmtime(filepath)
                        if file_age > max_age:
                            os.remove(filepath)
            return True
        except:
            return False

    def get_picon_stats(self):
        """Zwraca statystyki picon."""
        try:
            picon_files = [f for f in os.listdir(self.picon_dir) if f.endswith('.png')]
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.png')]
            
            total_size = sum(os.path.getsize(os.path.join(self.picon_dir, f)) for f in picon_files)
            cache_size = sum(os.path.getsize(os.path.join(self.cache_dir, f)) for f in cache_files)
            
            return {
                "Pikony": len(picon_files),
                "Cache": len(cache_files),
                "Rozmiar picon": f"{total_size / 1024 / 1024:.1f} MB",
                "Rozmiar cache": f"{cache_size / 1024 / 1024:.1f} MB",
                "Auto-download": self.config.get("auto_download", True),
                "Fallback": self.config.get("generate_fallback", True)
            }
        except:
            return {"Pikony": 0, "Cache": 0, "Błąd": "Nie można odczytać statystyk"}

    def test_picon_url(self, url):
        """Testuje dostępność URL picon."""
        try:
            response = requests.head(url, timeout=5)
            return {
                "url": url,
                "status": response.status_code,
                "content_type": response.headers.get('content-type', 'unknown'),
                "size": int(response.headers.get('content-length', 0))
            }
        except Exception as e:
            return {
                "url": url,
                "status": 0,
                "error": str(e)
            }