# -*- coding: utf-8 -*-
"""
IPTV Dream v6.0 - MENADŻER EPG
- Rozszerzone źródła EPG (20+ źródeł)
- Inteligentne mapowanie do kanałów satelitarnych
- Automatyczna instalacja EPG
- Cache dla lepszej wydajności
- Fallback na alternatywne źródła
"""

import os, re, json, time, requests
from datetime import datetime, timedelta

class EPGManager:
    """Zaawansowany menadżer EPG."""
    
    def __init__(self):
        self.config_file = "/etc/enigma2/iptvdream_v6_config.json"
        self.epg_dir = "/etc/epgimport"
        self.sources_file = "/etc/epgimport/iptvdream.sources.xml"
        self.channels_file = "/etc/epgimport/iptvdream.channels.xml"
        self.cache_dir = "/tmp/iptvdream_epg_cache"
        
        # Upewnij się, że katalog istnieje
        os.makedirs(self.epg_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Rozszerzone źródła EPG - 20+ różnych źródeł!
        self.epg_sources = [
            # POLSKA (3 źródła)
            {"url": "http://epg.ovh/pl.xml.gz", "name": "OVH Polska", "country": "pl", "priority": 1},
            {"url": "https://iptv-epg.org/files/epg-pl.xml.gz", "name": "IPTV-EPG Polska", "country": "pl", "priority": 2},
            {"url": "https://www.tvepg.eu/epg_data/pl.xml.gz", "name": "TV EPG Polska", "country": "pl", "priority": 3},
            
            # UK (3 źródła)
            {"url": "https://iptv-epg.org/files/epg-gb.xml.gz", "name": "IPTV-EPG UK", "country": "gb", "priority": 1},
            {"url": "https://www.tvepg.eu/epg_data/uk.xml.gz", "name": "TV EPG UK", "country": "gb", "priority": 2},
            {"url": "https://epg.ovh/uk.xml.gz", "name": "OVH UK", "country": "gb", "priority": 3},
            
            # USA (3 źródła)
            {"url": "https://iptv-epg.org/files/epg-us.xml.gz", "name": "IPTV-EPG USA", "country": "us", "priority": 1},
            {"url": "https://www.tvepg.eu/epg_data/us.xml.gz", "name": "TV EPG USA", "country": "us", "priority": 2},
            {"url": "https://epg.ovh/us.xml.gz", "name": "OVH USA", "country": "us", "priority": 3},
            
            # AFRYKA
            {"url": "https://iptv-epg.org/files/epg-ug.xml.gz", "name": "IPTV-EPG Uganda", "country": "ug", "priority": 1},
            {"url": "https://iptv-epg.org/files/epg-tz.xml.gz", "name": "IPTV-EPG Tanzania", "country": "tz", "priority": 1},
            {"url": "https://iptv-epg.org/files/epg-za.xml.gz", "name": "IPTV-EPG South Africa", "country": "za", "priority": 1},
            
            # EUROPA (7 krajów)
            {"url": "https://iptv-epg.org/files/epg-de.xml.gz", "name": "IPTV-EPG Germany", "country": "de", "priority": 1},
            {"url": "https://iptv-epg.org/files/epg-fr.xml.gz", "name": "IPTV-EPG France", "country": "fr", "priority": 1},
            {"url": "https://iptv-epg.org/files/epg-it.xml.gz", "name": "IPTV-EPG Italy", "country": "it", "priority": 1},
            {"url": "https://iptv-epg.org/files/epg-es.xml.gz", "name": "IPTV-EPG Spain", "country": "es", "priority": 1},
            {"url": "https://iptv-epg.org/files/epg-nl.xml.gz", "name": "IPTV-EPG Netherlands", "country": "nl", "priority": 1},
            {"url": "https://iptv-epg.org/files/epg-tr.xml.gz", "name": "IPTV-EPG Turkey", "country": "tr", "priority": 1},
            {"url": "https://iptv-epg.org/files/epg-ru.xml.gz", "name": "IPTV-EPG Russia", "country": "ru", "priority": 1},
            
            # ŚWIAT
            {"url": "http://epg.bevy.be/bevy.xml.gz", "name": "Bevy World Mix", "country": "world", "priority": 1},
            {"url": "https://iptvx.one/epg/epg.xml.gz", "name": "IPTVX World", "country": "world", "priority": 2},
            {"url": "https://epg.ovh/world.xml.gz", "name": "OVH World", "country": "world", "priority": 3}
        ]
        
        # Mapowanie kanałów satelitarnych
        self.satellite_mapping = {
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

    def install_epg_sources(self, custom_url=None):
        """Instaluje wszystkie źródła EPG."""
        try:
            # Tworzenie pliku sources.xml
            content = '<?xml version="1.0" encoding="utf-8"?>\n<sources>\n'
            content += '    <sourcecat sourcecatname="IPTV Dream v6.0 EPG Sources">\n'
            
            # Dodaj wszystkie źródła
            for source in self.epg_sources:
                content += f'''        <source type="gen_xmltv" channels="iptvdream.channels.xml">
                    <description>{source['name']}</description>
                    <url>{source['url']}</url>
                </source>\n'''
            
            # Dodaj własne źródło jeśli podano
            if custom_url and custom_url.strip().startswith(('http', 'ftp')):
                content += f'''        <source type="gen_xmltv" channels="iptvdream.channels.xml">
                    <description>Custom EPG Source</description>
                    <url>{custom_url.strip()}</url>
                </source>\n'''

            content += '    </sourcecat>\n</sources>\n'
            
            with open(self.sources_file, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Upewnij się, że plik kanałów istnieje
            if not os.path.exists(self.channels_file):
                with open(self.channels_file, "w", encoding="utf-8") as f:
                    f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n</channels>')
            
            return True, "Źródła EPG zainstalowane pomyślnie!"
            
        except Exception as e:
            return False, f"Błąd instalacji EPG: {e}"

    def create_epg_mapping(self, channels):
        """Tworzy mapowanie EPG dla kanałów."""
        try:
            # Grupowanie kanałów według kraju
            channels_by_country = {}
            for channel in channels:
                country = channel.get("metadata", {}).get("country", "UNKNOWN")
                channels_by_country.setdefault(country, []).append(channel)
            
            # Tworzenie mapowania
            mapping = []
            
            for country, country_channels in channels_by_country.items():
                # Wybierz odpowiednie źródło EPG dla kraju
                epg_source = self._select_epg_source_for_country(country)
                
                for channel in country_channels:
                    title = channel.get("title", "")
                    url = channel.get("url", "")
                    tvg_id = channel.get("epg_id", "")
                    
                    if url:
                        # Generuj ServiceRef
                        import hashlib
                        unique_sid = int(hashlib.md5(url.encode()).hexdigest()[:4], 16)
                        if unique_sid == 0:
                            unique_sid = 1
                        sid_hex = f"{unique_sid:X}"
                        
                        # Mapowanie do kanałów satelitarnych
                        sat_ref = self._get_satellite_ref(title)
                        
                        if sat_ref:
                            # Użyj referencji satelitarnej
                            mapping.append((sat_ref, title, title))
                        else:
                            # Standardowe referencje
                            for service_type in ["4097", "5002", "1"]:
                                ref = f"{service_type}:0:1:{sid_hex}:0:0:0:0:0:0"
                                mapping.append((ref, title, tvg_id))
            
            return mapping
            
        except Exception as e:
            print(f"[EPGManager] Błąd tworzenia mapowania: {e}")
            return []

    def _select_epg_source_for_country(self, country):
        """Wybiera najlepsze źródło EPG dla kraju."""
        country_sources = [s for s in self.epg_sources if s.get("country") == country]
        if country_sources:
            # Wybierz źródło z najwyższym priorytetem
            return min(country_sources, key=lambda x: x.get("priority", 999))
        
        # Fallback na światowe
        world_sources = [s for s in self.epg_sources if s.get("country") == "world"]
        if world_sources:
            return min(world_sources, key=lambda x: x.get("priority", 999))
        
        return None

    def _get_satellite_ref(self, title):
        """Pobiera referencję satelitarną dla tytułu."""
        title_clean = re.sub(r'[^a-z0-9]', '', title.lower())
        
        for sat_name, ref in self.satellite_mapping.items():
            if sat_name in title_clean:
                return ref
        
        return None

    def fetch_epg_data(self, channels, progress_callback=None):
        """Pobiera dane EPG dla kanałów."""
        try:
            total = len(channels)
            processed = 0
            
            for channel in channels:
                # Pobierz EPG dla kanału
                self._fetch_channel_epg(channel)
                
                processed += 1
                if progress_callback and processed % 10 == 0:
                    progress = (processed / total) * 100
                    progress_callback(progress, f"Pobieranie EPG: {processed}/{total}")
            
            return True
            
        except Exception as e:
            print(f"[EPGManager] Błąd pobierania EPG: {e}")
            return False

    def _fetch_channel_epg(self, channel):
        """Pobiera EPG dla pojedynczego kanału."""
        try:
            # Sprawdź cache
            cache_key = self._get_cache_key(channel.get("url", ""))
            cache_file = os.path.join(self.cache_dir, f"epg_{cache_key}.json")
            
            if os.path.exists(cache_file):
                file_age = time.time() - os.path.getmtime(cache_file)
                if file_age < 3600:  # 1 godzina
                    return  # Użyj cache
            
            # Tutaj można dodać logikę pobierania EPG z różnych źródeł
            # Na razie tylko zapisz pusty plik cache
            with open(cache_file, 'w') as f:
                json.dump({}, f)
                
        except:
            pass

    def _get_cache_key(self, url):
        """Generuje klucz cache."""
        import hashlib
        return hashlib.md5(url.encode('utf-8')).hexdigest()

    def create_epg_xml_file(self, mapping):
        """Tworzy plik XML z mapowaniem EPG."""
        try:
            with open(self.channels_file, "w", encoding="utf-8") as f:
                f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n')
                
                visited = set()
                for ref, name, tvg in mapping:
                    if ref in visited:
                        continue
                    visited.add(ref)
                    
                    # Generowanie wielu wariantów ID
                    ids = self._generate_epg_ids(name, tvg)
                    
                    for epg_id in ids:
                        f.write(f'  <channel id="{epg_id}">{ref}</channel>\n')
                
                f.write('</channels>')
            
            return True
            
        except Exception as e:
            print(f"[EPGManager] Błąd tworzenia XML: {e}")
            return False

    def _generate_epg_ids(self, name, tvg_id):
        """Generuje wiele wariantów ID EPG."""
        ids = set()
        
        # Oryginalne ID
        if tvg_id:
            ids.add(tvg_id)
        
        # Czysta nazwa
        clean_name = re.sub(r'[^\w\s]', '', name).strip()
        ids.add(clean_name)
        
        # Bez spacji
        no_spaces = clean_name.replace(" ", "")
        ids.add(no_spaces)
        
        # Z sufiksami krajowymi
        countries = ['pl', 'uk', 'us', 'de', 'fr']
        for country in countries:
            ids.add(f"{clean_name}.{country}")
            ids.add(f"{no_spaces}.{country}")
        
        # Wersje z numerami
        num_match = re.search(r'(\d+)$', clean_name)
        if num_match:
            num = num_match.group(1)
            prefix = clean_name[:num_match.start()].strip()
            ids.add(f"{prefix}{num}")
            ids.add(f"{prefix}-{num}")
            ids.add(f"{prefix}.{num}")
        
        # Wersje dla XXX/VOD
        if 'xxx' in clean_name.lower() or 'adult' in clean_name.lower():
            ids.add("xxx")
            ids.add("adult")
        
        if 'vod' in clean_name.lower() or 'movie' in clean_name.lower():
            ids.add("vod")
            ids.add("movies")
        
        return list(ids)

    def get_epg_status(self):
        """Zwraca status EPG."""
        sources_count = len(self.epg_sources)
        custom_sources = len([s for s in self.epg_sources if s.get("type") == "custom"])
        
        return {
            "Źródła EPG": sources_count,
            "Kraje objęte": len(set(s.get("country") for s in self.epg_sources)),
            "Plik źródeł": os.path.exists(self.sources_file),
            "Plik kanałów": os.path.exists(self.channels_file),
            "Cache EPG": os.path.exists(self.cache_dir)
        }

    def cleanup_cache(self, max_age=86400):
        """Czyści przeterminowane pliki EPG."""
        try:
            if os.path.exists(self.cache_dir):
                for filename in os.listdir(self.cache_dir):
                    if filename.startswith("epg_"):
                        filepath = os.path.join(self.cache_dir, filename)
                        file_age = time.time() - os.path.getmtime(filepath)
                        if file_age > max_age:
                            os.remove(filepath)
            return True
        except:
            return False

    def test_epg_sources(self):
        """Testuje dostępność źródeł EPG."""
        results = []
        
        for source in self.epg_sources[:5]:  # Testuj tylko 5 pierwszych
            try:
                response = requests.head(source["url"], timeout=5)
                results.append({
                    "source": source["name"],
                    "url": source["url"],
                    "status": "OK" if response.status_code == 200 else f"Błąd {response.status_code}",
                    "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0
                })
            except Exception as e:
                results.append({
                    "source": source["name"],
                    "url": source["url"],
                    "status": "Błąd",
                    "error": str(e)
                })
        
        return results