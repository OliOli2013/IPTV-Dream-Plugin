# -*- coding: utf-8 -*-
"""
IPTV Dream v6.0 - EPG Manager
Kompletny menadżer EPG z obsługą wielu źródeł
"""

import os
import json
import requests
import re
from datetime import datetime
from ..tools.lang import _
from Components.Language import language

# KLUCZ DO ZAPISYWANIA URL W PROFILU
EPG_URL_KEY = "custom_epg_url"

# Źródła EPG
EPG_SOURCES = [
    # POLSKA
    {"url": "http://epg.ovh/pl.xml.gz", "description": "IPTV Dream - Polska (OVH)"},
    {"url": "https://iptv-epg.org/files/epg-pl.xml.gz", "description": "IPTV Dream - Polska (iptv-epg)"},
    # UK (GB)
    {"url": "https://iptv-epg.org/files/epg-gb.xml.gz", "description": "IPTV Dream - UK (Great Britain)"},
    # USA
    {"url": "https://iptv-epg.org/files/epg-us.xml.gz", "description": "IPTV Dream - USA"},
    # AFRYKA
    {"url": "https://iptv-epg.org/files/epg-ug.xml.gz", "description": "IPTV Dream - Uganda"},
    {"url": "https://iptv-epg.org/files/epg-tz.xml.gz", "description": "IPTV Dream - Tanzania"},
    {"url": "https://iptv-epg.org/files/epg-za.xml.gz", "description": "IPTV Dream - South Africa"},
    # EUROPA
    {"url": "https://iptv-epg.org/files/epg-de.xml.gz", "description": "IPTV Dream - Germany"},
    {"url": "https://iptv-epg.org/files/epg-fr.xml.gz", "description": "IPTV Dream - France"},
    # ŚWIAT
    {"url": "http://epg.bevy.be/bevy.xml.gz", "description": "IPTV Dream - World Mix (Bevy)"}
]

# Katalogi i pliki
EPG_DIR      = "/etc/epgimport"
SOURCE_FILE  = "/etc/epgimport/iptvdream.sources.xml"
CHANNEL_FILE = "/etc/epgimport/iptvdream.channels.xml"

class EPGManager:
    """Kompletny menadżer EPG dla IPTV Dream v6.0"""
    
    def __init__(self, config_file="/etc/enigma2/iptv_dream_epg.json"):
        self.config_file = config_file
        self.config = self._load_config()
        self.lang = language.getLanguage()[:2] or "pl"
        
    def _load_config(self):
        """Wczytuje konfigurację EPG"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "epg_sources": [],
            "custom_urls": {},
            "cache": {},
            "settings": {
                "auto_update": True,
                "update_interval": 24,
                "cache_enabled": True
            }
        }
        
    def _save_config(self):
        """Zapisuje konfigurację EPG"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except:
            pass
            
    def get_epg_sources(self):
        """Zwraca listę dostępnych źródeł EPG"""
        sources = EPG_SOURCES.copy()
        
        # Dodaj własne źródła
        for url, desc in self.config["custom_urls"].items():
            sources.append({
                "url": url,
                "description": desc
            })
            
        return sources
        
    def add_custom_epg_source(self, url, description):
        """Dodaje własne źródło EPG"""
        self.config["custom_urls"][url] = description
        self._save_config()
        
    def remove_custom_epg_source(self, url):
        """Usuwa własne źródło EPG"""
        if url in self.config["custom_urls"]:
            del self.config["custom_urls"][url]
            self._save_config()
            
    def install_epg_sources(self, custom_url=None):
        """Instaluje źródła EPG dla wtyczki"""
        try:
            if not os.path.exists(EPG_DIR): 
                os.makedirs(EPG_DIR)
            
            content = '<?xml version="1.0" encoding="utf-8"?>\n<sources>\n'
            content += f'    <sourcecat sourcecatname="{_("epg_dream_sources", self.lang)}">\n'
            
            # 1. Dodajemy wszystkie źródła domyślne
            for source in EPG_SOURCES:
                content += f'''        <source type="gen_xmltv" channels="iptvdream.channels.xml">
            <description>{source['description']}</description>
            <url>{source['url']}</url>
        </source>\n'''
            
            # 2. Dodajemy własne źródło EPG, jeśli podano
            if custom_url and custom_url.strip().startswith(('http', 'ftp')):
                content += f'''        <source type="gen_xmltv" channels="iptvdream.channels.xml">
            <description>{_("epg_custom", self.lang)}</description>
            <url>{custom_url.strip()}</url>
        </source>\n'''

            content += '    </sourcecat>\n</sources>\n'
            
            with open(SOURCE_FILE, "w") as f: 
                f.write(content)
            
            # Upewniamy się, że plik mapowania istnieje
            if not os.path.exists(CHANNEL_FILE):
                with open(CHANNEL_FILE, "w") as f: 
                    f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n</channels>')
                
            return True, _("epg_updated", self.lang)
        except Exception as e:
            return False, f"{_('error', self.lang)}: {e}"
            
    def download_epg_data(self, url):
        """Pobiera dane EPG z podanego URL"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"[EPGManager] Błąd pobierania EPG: {e}")
            return None
            
    def parse_epg_data(self, epg_content):
        """Parsuje dane EPG i zwraca programy"""
        programs = []
        
        try:
            import xml.etree.ElementTree as ET
            
            if not epg_content:
                return programs
                
            # Obsługa gzip jeśli potrzebne
            if url.endswith('.gz'):
                import gzip
                epg_content = gzip.decompress(epg_content)
                
            root = ET.fromstring(epg_content)
            
            for programme in root.findall('.//programme'):
                channel = programme.get('channel')
                start = programme.get('start')
                stop = programme.get('stop')
                
                title_elem = programme.find('title')
                title = title_elem.text if title_elem is not None else ""
                
                desc_elem = programme.find('desc')
                description = desc_elem.text if desc_elem is not None else ""
                
                programs.append({
                    'channel': channel,
                    'start': start,
                    'stop': stop,
                    'title': title,
                    'description': description
                })
                
        except Exception as e:
            print(f"[EPGManager] Błąd parsowania EPG: {e}")
            
        return programs
        
    def get_epg_for_channel(self, channel_id, programs):
        """Filtruje programy dla danego kanału"""
        return [p for p in programs if p['channel'] == channel_id]
        
    def update_channel_mapping(self, channels):
        """Aktualizuje mapowanie kanałów dla EPG"""
        try:
            import xml.etree.ElementTree as ET
            
            # Stwórz nowe drzewo XML
            root = ET.Element('channels')
            
            for channel in channels:
                channel_elem = ET.SubElement(root, 'channel')
                channel_elem.set('id', channel.get('tvg_id', channel.get('title', '')))
                
                # Dodaj display-name
                display_name = ET.SubElement(channel_elem, 'display-name')
                display_name.set('lang', 'pl')
                display_name.text = channel.get('title', '')
                
            # Zapisz do pliku
            tree = ET.ElementTree(root)
            tree.write(CHANNEL_FILE, encoding='utf-8', xml_declaration=True)
            
            return True
        except Exception as e:
            print(f"[EPGManager] Błąd aktualizacji mapowania: {e}")
            return False
            
    def get_current_epg(self, channel_id, hours=24):
        """Pobiera aktualne i nadchodzące programy dla kanału"""
        programs = []
        now = datetime.now()
        
        # Tu powinna być logika pobierania EPG z różnych źródeł
        # Na razu zwróć przykładowe dane
        sample_programs = [
            {
                'start': now.strftime('%Y%m%d%H%M%S'),
                'stop': (now + timedelta(hours=1)).strftime('%Y%m%d%H%M%S'),
                'title': 'Program TV',
                'description': 'Opis programu'
            }
        ]
        
        return sample_programs
        
    def search_epg(self, query, channels=None):
        """Wyszukuje w EPG"""
        results = []
        
        # Logika wyszukiwania w EPG
        # Na razu pusta lista
        
        return results
        
    def clear_epg_cache(self):
        """Czyści cache EPG"""
        self.config["cache"] = {}
        self._save_config()
        
    def get_epg_stats(self):
        """Zwraca statystyki EPG"""
        return {
            "sources_count": len(self.get_epg_sources()),
            "custom_sources": len(self.config["custom_urls"]),
            "last_update": self.config.get("last_update", "Nigdy"),
            "cache_size": len(self.config.get("cache", {}))
        }
        
    def export_epg_settings(self):
        """Eksportuje ustawienia EPG"""
        return {
            "sources": self.get_epg_sources(),
            "custom_urls": self.config["custom_urls"],
            "settings": self.config["settings"]
        }
        
    def import_epg_settings(self, settings):
        """Importuje ustawienia EPG"""
        if "custom_urls" in settings:
            self.config["custom_urls"] = settings["custom_urls"]
        if "settings" in settings:
            self.config["settings"] = settings["settings"]
        self._save_config()

# Globalna instancja
epg_manager = EPGManager()

def get_epg_manager():
    """Zwraca globalną instancję menadżera EPG"""
    return epg_manager

def install_epg_sources(custom_url=None):
    """Instaluje źródła EPG dla wtyczki."""
    return epg_manager.install_epg_sources(custom_url)

def download_picon_url(url, title):
    """Pobiera picon dla kanału."""
    return epg_manager.download_picon_url(url, title)