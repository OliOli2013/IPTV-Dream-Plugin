# -*- coding: utf-8 -*-
"""
IPTV Dream v6.0 - MAPOWANIE KANAŁÓW
- Ultra-szybkie parsowanie
- Inteligentne grupowanie
- Detekcja XXX/VOD
- Mapowanie do kanałów satelitarnych
"""

import re, time
from .config_manager import ConfigManager

class ChannelMapper:
    """Inteligentny mapowacz kanałów."""
    
    def __init__(self):
        self.config = ConfigManager("/etc/enigma2/iptvdream_v6_config.json")
        
        # Skompilowane regexy dla maksymalnej wydajności
        self.patterns = {
            'extinf': re.compile(r'#EXTINF:([^,]*),(.*)', re.IGNORECASE),
            'attrs': re.compile(r'([a-zA-Z0-9_-]+)\s*=\s*("[^"]*"|[^,;\s]+)'),
            'group_bracket': re.compile(r'^\[([^\]]+)\]'),
            'adult': re.compile(r'(xxx|adult|porn|sex|erotic|18\+|mature)', re.IGNORECASE),
            'vod': re.compile(r'(vod|movie|film|video|series|serial)', re.IGNORECASE),
            'quality': re.compile(r'(HD|FHD|UHD|4K|RAW|VIP|PL|UK|US)', re.IGNORECASE),
            'clean_name': re.compile(r'[^\w\s]'),
            'prefix': re.compile(r'^(PL|EN|DE|IT|UK|VIP|RAW|FHD|UHD|HEVC|4K)\s*[|:-]?\s*', re.IGNORECASE),
            'suffix': re.compile(r'\s+[-|]?\s*(HD|FHD|UHD|4K|RAW|VIP|PL|UK|US)$', re.IGNORECASE)
        }
        
        # Mapowanie kanałów satelitarnych
        self.sat_mapping = {
            'tvp1': '1:0:19:6FF:2F:1:0:0:0:0:',
            'tvp2': '1:0:19:700:2F:1:0:0:0:0:',
            'polsat': '1:0:19:1E2C:1:1:0:0:0:0:',
            'tvn': '1:0:19:1E2D:1:1:0:0:0:0:',
            'polsatnews': '1:0:19:1E2E:1:1:0:0:0:0:',
            'tvpsport': '1:0:19:1E2F:1:1:0:0:0:0:',
            'hbo': '1:0:19:1E30:1:1:0:0:0:0:',
            'hbo2': '1:0:19:1E31:1:1:0:0:0:0:',
            'cinemax': '1:0:19:1E32:1:1:0:0:0:0:',
            'axn': '1:0:19:1E33:1:1:0:0:0:0:',
            'fox': '1:0:19:1E34:1:1:0:0:0:0:',
            'discovery': '1:0:19:1E35:1:1:0:0:0:0:',
            'animalplanet': '1:0:19:1E36:1:1:0:0:0:0:',
            'tlc': '1:0:19:1E37:1:1:0:0:0:0:',
            'mtv': '1:0:19:1E38:1:1:0:0:0:0:',
            'cnn': '1:0:19:1E39:1:1:0:0:0:0:',
            'bbc': '1:0:19:1E3A:1:1:0:0:0:0:',
            'deutschland': '1:0:19:1E3B:1:1:0:0:0:0:',
            'rtl': '1:0:19:1E3C:1:1:0:0:0:0:',
            'prosieben': '1:0:19:1E3D:1:1:0:0:0:0:',
            'sky': '1:0:19:1E3E:1:1:0:0:0:0:',
            'eurosport1': '1:0:19:1E3F:1:1:0:0:0:0:',
            'eurosport2': '1:0:19:1E40:1:1:0:0:0:0:',
        }

    def map_channels(self, raw_content):
        """
        Główna funkcja mapowania kanałów.
        Zwraca listę słowników z kanałami.
        """
        start_time = time.time()
        
        try:
            # Dekodowanie z obsługą błędów
            try:
                text = raw_content.decode("utf-8", "ignore")
            except:
                text = str(raw_content)
            
            lines = text.splitlines()
            channels = []
            current_entry = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # EXTINF
                if line.startswith("#EXTINF"):
                    current_entry = self._parse_extinf(line)
                    
                # EXTGRP
                elif line.startswith("#EXTGRP:"):
                    grp_name = line.split(":", 1)[1].strip()
                    if grp_name:
                        current_entry["group"] = grp_name
                        
                # URL
                elif "://" in line and not line.startswith("#"):
                    url = line.strip()
                    
                    if not current_entry:
                        name = url.split('/')[-1]
                        name = re.sub(r'\.(ts|m3u8|mp4|mkv)$', '', name, flags=re.IGNORECASE)
                        current_entry = {"title": name}
                    
                    # Określenie grupy
                    self._determine_group(current_entry, url)
                    
                    # Tworzenie kanału
                    channel = self._create_channel(current_entry, url)
                    channels.append(channel)
                    
                    current_entry = {}
            
            # Mapowanie do kanałów satelitarnych
            channels = self._map_to_satellite_channels(channels)
            
            # Grupowanie jeśli włączone
            if self.config.get("user_preferences", {}).get("auto_group_channels", True):
                channels = self._auto_group_channels(channels)
            
            return channels
            
        except Exception as e:
            print(f"[ChannelMapper] Błąd mapowania: {e}")
            return []
    
    def _parse_extinf(self, line):
        """Parsuje linię EXTINF z maksymalną wydajnością."""
        entry = {}
        
        # Tytuł
        if ',' in line:
            parts = line.split(',', 1)
            meta_part = parts[0]
            entry["title"] = parts[1].strip() if len(parts) > 1 else "No Name"
        else:
            meta_part = line
            entry["title"] = "No Name"

        # Atrybuty
        attrs = self.patterns['attrs'].findall(meta_part)
        for key, val in attrs:
            clean_val = val.replace('"', '').strip()
            key_lower = key.lower()
            
            if key_lower in ["group-title", "group", "category", "cat"]:
                entry["group"] = clean_val
            elif key_lower in ["tvg-logo", "logo"]:
                entry["logo"] = clean_val
            elif key_lower in ["tvg-id", "epg-id", "id"]:
                entry["epg_id"] = clean_val
        
        # Grupa z tytułu
        if "group" not in entry:
            group_match = self.patterns['group_bracket'].match(entry.get("title", ""))
            if group_match:
                entry["group"] = group_match.group(1).strip()
        
        return entry
    
    def _determine_group(self, entry, url):
        """Określa grupę kanału."""
        title_lower = entry.get("title", "").lower()
        
        # Detekcja XXX
        if self.patterns['adult'].search(title_lower):
            entry["group"] = "XXX"
        # Detekcja VOD
        elif self.patterns['vod'].search(title_lower):
            entry["group"] = "VOD"
        elif '/movie/' in url.lower() or '/series/' in url.lower():
            entry["group"] = "VOD"
        # Domyślnie
        else:
            entry["group"] = "Inne"
    
    def _create_channel(self, entry, url):
        """Tworzy obiekt kanału."""
        return {
            "title": entry.get("title", "No Name"),
            "url": url,
            "group": entry.get("group", "Inne"),
            "logo": entry.get("logo", ""),
            "epg_id": entry.get("epg_id", ""),
            "metadata": {
                "quality": self._detect_quality(entry.get("title", "")),
                "country": self._detect_country(entry.get("title", "")),
                "is_adult": entry.get("group") == "XXX",
                "is_vod": entry.get("group") == "VOD"
            }
        }
    
    def _detect_quality(self, title):
        """Wykrywa jakość kanału."""
        quality_match = self.patterns['quality'].search(title)
        if quality_match:
            return quality_match.group(1)
        return "SD"
    
    def _detect_country(self, title):
        """Wykrywa kraj kanału."""
        title_upper = title.upper()
        countries = {
            'PL': ['PL', 'POLSKA', 'POLAND'],
            'UK': ['UK', 'GB', 'ENGLAND'],
            'US': ['US', 'USA', 'AMERICA'],
            'DE': ['DE', 'GERMANY', 'DEUTSCHLAND'],
            'FR': ['FR', 'FRANCE'],
            'IT': ['IT', 'ITALY'],
            'ES': ['ES', 'SPAIN']
        }
        
        for country, keywords in countries.items():
            if any(keyword in title_upper for keyword in keywords):
                return country
        return "UNKNOWN"
    
    def _map_to_satellite_channels(self, channels):
        """Mapuje kanały do kanałów satelitarnych."""
        for channel in channels:
            title = channel.get("title", "").lower()
            title_clean = self.patterns['clean_name'].sub('', title)
            
            # Szukanie dopasowania
            sat_ref = None
            for sat_name, ref in self.sat_mapping.items():
                if sat_name in title_clean:
                    sat_ref = ref
                    break
            
            if sat_ref:
                channel['epg_id'] = sat_ref
                channel['epg_source'] = 'satellite'
        
        return channels
    
    def _auto_group_channels(self, channels):
        """Automatycznie grupuje kanały."""
        # Ta funkcja może być rozszerzona o inteligentne grupowanie
        # Na razie zwraca kanały bez zmian
        return channels
    
    def get_channel_stats(self, channels):
        """Zwraca statystyki kanałów."""
        if not channels:
            return {}
        
        groups = {}
        qualities = {}
        countries = {}
        adult_count = 0
        vod_count = 0
        
        for channel in channels:
            # Grupy
            group = channel.get("group", "Inne")
            groups[group] = groups.get(group, 0) + 1
            
            # Jakość
            quality = channel.get("metadata", {}).get("quality", "SD")
            qualities[quality] = qualities.get(quality, 0) + 1
            
            # Kraj
            country = channel.get("metadata", {}).get("country", "UNKNOWN")
            countries[country] = countries.get(country, 0) + 1
            
            # XXX/VOD
            if channel.get("metadata", {}).get("is_adult", False):
                adult_count += 1
            if channel.get("metadata", {}).get("is_vod", False):
                vod_count += 1
        
        return {
            "Kanałów łącznie": len(channels),
            "Grupy": len(groups),
            "Jakości": len(qualities),
            "Kraje": len(countries),
            "Kanały XXX": adult_count,
            "Kanały VOD": vod_count,
            "Największa grupa": max(groups.items(), key=lambda x: x[1]) if groups else ("Brak", 0)
        }
    
    def filter_channels(self, channels, content_filter='all'):
        """Filtruje kanały zgodnie z preferencjami użytkownika."""
        prefs = self.config.get("user_preferences", {})
        
        filtered = []
        
        for channel in channels:
            # Filtr XXX
            if channel.get("metadata", {}).get("is_adult", False):
                if not prefs.get("show_adult_channels", True) and content_filter != 'adult':
                    continue
                if content_filter == 'live':
                    continue
            
            # Filtr VOD
            if channel.get("metadata", {}).get("is_vod", False):
                if not prefs.get("show_vod_channels", True) and content_filter != 'vod':
                    continue
                if content_filter == 'live':
                    continue
            
            # Filtr jakości
            if prefs.get("prefer_hd_quality", True):
                quality = channel.get("metadata", {}).get("quality", "SD")
                if quality in ["HD", "FHD", "UHD", "4K"]:
                    channel["priority"] = 1
                else:
                    channel["priority"] = 0
            
            filtered.append(channel)
        
        # Sortowanie według priorytetu
        if prefs.get("prefer_hd_quality", True):
            filtered.sort(key=lambda x: x.get("priority", 0), reverse=True)
        
        return filtered