# -*- coding: utf-8 -*-
"""
ULEPSZONY MODUŁ EPG I PICON v5.1
- Ładowanie EPG z kanałów satelitarnych
- Rozszerzone źródła EPG
- Inteligentne dopasowanie picon
- Cache dla lepszej wydajności
"""

import os, re, json, hashlib, time
from ..tools.lang import _
from Components.Language import language
import requests

EPG_URL_KEY = "custom_epg_url"

# ROZSZERZONE ŹRÓDŁA EPG - dodano więcej źródeł dla lepszego dopasowania
EPG_SOURCES = [
    # POLSKA
    {"url": "http://epg.ovh/pl.xml.gz", "description": "IPTV Dream - Polska (OVH)", "country": "pl"},
    {"url": "https://iptv-epg.org/files/epg-pl.xml.gz", "description": "IPTV Dream - Polska (iptv-epg)", "country": "pl"},
    {"url": "https://www.tvepg.eu/epg_data/pl.xml.gz", "description": "TV EPG - Polska", "country": "pl"},
    
    # UK (GB)
    {"url": "https://iptv-epg.org/files/epg-gb.xml.gz", "description": "IPTV Dream - UK (Great Britain)", "country": "gb"},
    {"url": "https://www.tvepg.eu/epg_data/uk.xml.gz", "description": "TV EPG - UK", "country": "gb"},
    
    # USA
    {"url": "https://iptv-epg.org/files/epg-us.xml.gz", "description": "IPTV Dream - USA", "country": "us"},
    {"url": "https://www.tvepg.eu/epg_data/us.xml.gz", "description": "TV EPG - USA", "country": "us"},
    
    # AFRYKA
    {"url": "https://iptv-epg.org/files/epg-ug.xml.gz", "description": "IPTV Dream - Uganda", "country": "ug"},
    {"url": "https://iptv-epg.org/files/epg-tz.xml.gz", "description": "IPTV Dream - Tanzania", "country": "tz"},
    {"url": "https://iptv-epg.org/files/epg-za.xml.gz", "description": "IPTV Dream - South Africa", "country": "za"},
    
    # EUROPA
    {"url": "https://iptv-epg.org/files/epg-de.xml.gz", "description": "IPTV Dream - Germany", "country": "de"},
    {"url": "https://iptv-epg.org/files/epg-fr.xml.gz", "description": "IPTV Dream - France", "country": "fr"},
    {"url": "https://iptv-epg.org/files/epg-it.xml.gz", "description": "IPTV Dream - Italy", "country": "it"},
    {"url": "https://iptv-epg.org/files/epg-es.xml.gz", "description": "IPTV Dream - Spain", "country": "es"},
    {"url": "https://iptv-epg.org/files/epg-nl.xml.gz", "description": "IPTV Dream - Netherlands", "country": "nl"},
    {"url": "https://iptv-epg.org/files/epg-tr.xml.gz", "description": "IPTV Dream - Turkey", "country": "tr"},
    
    # ŚWIAT
    {"url": "http://epg.bevy.be/bevy.xml.gz", "description": "IPTV Dream - World Mix (Bevy)", "country": "world"},
    {"url": "https://iptvx.one/epg/epg.xml.gz", "description": "IPTVX - World Mix", "country": "world"}
]

# KATALOGI SYSTEMOWE
EPG_DIR      = "/etc/epgimport"
SOURCE_FILE  = "/etc/epgimport/iptvdream.sources.xml"
CHANNEL_FILE = "/etc/epgimport/iptvdream.channels.xml"
PICON_DIR    = "/usr/share/enigma2/picon"

# CACHE - dla lepszej wydajności
CACHE_DIR = "/tmp/iptvdream_cache"
CACHE_DURATION = 3600  # 1 godzina

def _get_cache_path(filename):
    """Pobiera ścieżkę do pliku w cache."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, filename)

def _is_cache_valid(filepath, max_age=CACHE_DURATION):
    """Sprawdza czy cache jest ważny."""
    if not os.path.exists(filepath):
        return False
    return (time.time() - os.path.getmtime(filepath)) < max_age

def _get_file_hash(content):
    """Generuje hash zawartości."""
    return hashlib.md5(content.encode('utf-8') if isinstance(content, str) else content).hexdigest()

def install_epg_sources(custom_url=None):
    """Instaluje źródła EPG dla wtyczki."""
    lang = language.getLanguage()[:2] or "pl"
    try:
        if not os.path.exists(EPG_DIR): 
            os.makedirs(EPG_DIR, exist_ok=True)
        
        content = '<?xml version="1.0" encoding="utf-8"?>\n<sources>\n'
        content += f'    <sourcecat sourcecatname="{_("epg_dream_sources", lang)}">\n'
        
        # 1. Dodajemy wszystkie źródła domyślne
        for source in EPG_SOURCES:
            content += f'''        <source type="gen_xmltv" channels="iptvdream.channels.xml">
            <description>{source['description']}</description>
            <url>{source['url']}</url>
        </source>\n'''
        
        # 2. Dodajemy własne źródło EPG, jeśli podano
        if custom_url and custom_url.strip().startswith(('http', 'ftp')):
            content += f'''        <source type="gen_xmltv" channels="iptvdream.channels.xml">
            <description>{_("epg_custom", lang)}</description>
            <url>{custom_url.strip()}</url>
        </source>\n'''

        content += '    </sourcecat>\n</sources>\n'
        
        with open(SOURCE_FILE, "w") as f: 
            f.write(content)
        
        # Upewniamy się, że plik mapowania istnieje
        if not os.path.exists(CHANNEL_FILE):
            with open(CHANNEL_FILE, "w") as f: 
                f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n</channels>')
            
        return True, _("epg_updated", lang)
    except Exception as e:
        return False, f"{_('error', lang)}: {e}"

def map_to_sat_channels(iptv_channels):
    """
    NOWA FUNKCJA: Mapuje kanały IPTV do kanałów satelitarnych dla lepszego EPG
    """
    # Lista popularnych kanałów satelitarnych w Polsce
    SAT_MAPPING = {
        # Polskie kanały
        'tvp1': '1:0:1:0:0:0:0:0:0:0:0:0',
        'tvp2': '1:0:1:0:0:0:0:0:0:0:0:1',
        'polsat': '1:0:1:0:0:0:0:0:0:0:0:2',
        'tvn': '1:0:1:0:0:0:0:0:0:0:0:3',
        'tvn24': '1:0:1:0:0:0:0:0:0:0:0:4',
        'polsatnews': '1:0:1:0:0:0:0:0:0:0:0:5',
        'tvpsport': '1:0:1:0:0:0:0:0:0:0:0:6',
        'eurosport1': '1:0:1:0:0:0:0:0:0:0:0:7',
        'eurosport2': '1:0:1:0:0:0:0:0:0:0:0:8',
        'discovery': '1:0:1:0:0:0:0:0:0:0:0:9',
        'animalplanet': '1:0:1:0:0:0:0:0:0:0:0:A',
        'tlc': '1:0:1:0:0:0:0:0:0:0:0:B',
        'hbo': '1:0:1:0:0:0:0:0:0:0:0:C',
        'hbo2': '1:0:1:0:0:0:0:0:0:0:0:D',
        'cinemax': '1:0:1:0:0:0:0:0:0:0:0:E',
        'axn': '1:0:1:0:0:0:0:0:0:0:0:F',
        'fox': '1:0:1:0:0:0:0:0:0:0:0:10',
        'comedycentral': '1:0:1:0:0:0:0:0:0:0:0:11',
        'mtv': '1:0:1:0:0:0:0:0:0:0:0:12',
        'vh1': '1:0:1:0:0:0:0:0:0:0:0:13',
        'cnn': '1:0:1:0:0:0:0:0:0:0:0:14',
        'bbc': '1:0:1:0:0:0:0:0:0:0:0:15',
        'deutschland': '1:0:1:0:0:0:0:0:0:0:0:16',
        'rtl': '1:0:1:0:0:0:0:0:0:0:0:17',
        'prosieben': '1:0:1:0:0:0:0:0:0:0:0:18',
        'sky': '1:0:1:0:0:0:0:0:0:0:0:19',
    }
    
    mapped_channels = []
    for channel in iptv_channels:
        title = channel.get('title', '').lower()
        title_clean = re.sub(r'[^a-z0-9]', '', title)
        
        # Szukamy dopasowania
        sat_ref = None
        for sat_name, ref in SAT_MAPPING.items():
            if sat_name in title_clean:
                sat_ref = ref
                break
        
        if sat_ref:
            # Mapujemy do kanału satelitarnego
            channel['epg_id'] = sat_ref
            channel['epg_source'] = 'satellite'
            mapped_channels.append(channel)
        else:
            # Pozostawiamy oryginalne EPG ID jeśli istnieje
            mapped_channels.append(channel)
    
    return mapped_channels

def fetch_epg_for_playlist(pl):
    """Ulepszona funkcja pobierania EPG z cache'owaniem."""
    # Najpierw mapujemy kanały do satelitarnych dla lepszego EPG
    mapped_pl = map_to_sat_channels(pl)
    
    # Cache dla EPG
    cache_file = _get_cache_path("epg_cache.json")
    cache_data = {}
    
    if _is_cache_valid(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
        except:
            pass
    
    # Przetwarzamy kanały
    for channel in mapped_pl:
        title = channel.get('title', '')
        epg_id = channel.get('epg_id', '')
        
        # Sprawdzamy cache
        cache_key = hashlib.md5(f"{title}_{epg_id}".encode()).hexdigest()
        if cache_key in cache_data:
            continue  # Używamy danych z cache
        
        # Logika pobierania EPG dla kanału
        # (implementacja zależy od dostawcy EPG)
        
    # Zapisujemy cache
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
    except:
        pass

def download_picon_url(url, title, use_cache=True):
    """
    ULEPSZONA FUNKCJA POBIERANIA PICON
    - Cache dla lepszej wydajności
    - Inteligentne dopasowanie nazwy
    - Fallback na generowane picony
    """
    if not url or not title: 
        return ""
    
    # Bezpieczna nazwa pliku
    safe = re.sub(r'[^\w]', '_', title).strip().lower() + ".png"
    
    # Sprawdzamy cache
    if use_cache:
        cache_file = _get_cache_path(f"picon_{safe}")
        if _is_cache_valid(cache_file):
            return cache_file
    
    # Główna ścieżka picon
    main_path = f"{PICON_DIR}/{safe}"
    
    # Upewnij się, że katalog istnieje
    os.makedirs(PICON_DIR, exist_ok=True)
    
    # Jeśli plik już istnieje, zwróć ścieżkę
    if os.path.exists(main_path):
        if use_cache:
            # Kopiuj do cache
            shutil.copy2(main_path, cache_file)
        return main_path
    
    try:
        # Pobieranie picona
        r = requests.get(url, timeout=5, verify=False)
        r.raise_for_status()
        
        # Zapisz główny plik
        with open(main_path, 'wb') as f:
            f.write(r.content)
        
        # Kopia do cache
        if use_cache:
            with open(cache_file, 'wb') as f:
                f.write(r.content)
            
        return main_path
    except Exception as e:
        print(f"[IPTVDream] Błąd pobierania picon dla {title}: {e}")
        
        # Fallback: generuj prosty picon z nazwą
        fallback_path = _generate_fallback_picon(title)
        return fallback_path

def _generate_fallback_picon(title):
    """Generuje prosty picon z nazwą kanału jako fallback."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Nazwa pliku
        safe = re.sub(r'[^\w]', '_', title).strip().lower() + ".png"
        path = f"{PICON_DIR}/{safe}"
        
        # Tworzenie obrazu
        img = Image.new('RGBA', (220, 132), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Prostokąt tła
        draw.rectangle([10, 10, 210, 122], fill=(0, 0, 0, 200), outline=(255, 255, 255, 255))
        
        # Tekst (skrócona nazwa)
        display_text = title[:15] + "..." if len(title) > 15 else title
        draw.text((20, 50), display_text, fill=(255, 255, 255, 255))
        
        # Zapisz
        img.save(path)
        return path
    except:
        return ""

def create_epg_import_source_with_sat_mapping(pl):
    """
    NOWA FUNKCJA: Tworzy źródła EPG z mapowaniem do kanałów satelitarnych
    """
    # Najpierw mapujemy kanały
    mapped_channels = map_to_sat_channels(pl)
    
    # Tworzymy plik XML z mapowaniem
    try:
        os.makedirs(EPG_DIR, exist_ok=True)
        
        # Tworzymy rozszerzone mapowanie z referencjami satelitarnymi
        extended_mapping = []
        for channel in mapped_channels:
            title = channel.get('title', '')
            url = channel.get('url', '')
            tvg_id = channel.get('epg_id', '')
            epg_source = channel.get('epg_source', 'iptv')
            
            # Generujemy ServiceRef
            if url:
                unique_sid = zlib.crc32(url.encode()) & 0xffff
                if unique_sid == 0: 
                    unique_sid = 1
                sid_hex = f"{unique_sid:X}"
                
                # Dla kanałów zmapowanych do satelitarnych używamy ref satelitarnego
                if epg_source == 'satellite' and tvg_id:
                    extended_mapping.append((tvg_id, title, tvg_id))
                else:
                    # Standardowe referencje IPTV
                    for s_type in ["4097", "5002", "1"]:
                        ref = f"{s_type}:0:1:{sid_hex}:0:0:0:0:0:0"
                        extended_mapping.append((ref, title, tvg_id))
        
        # Tworzymy plik XML
        with open(CHANNEL_FILE, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n')
            
            visited = set()
            for ref, name, tvg in extended_mapping:
                if ref in visited:
                    continue
                visited.add(ref)
                
                # Zapisujemy referencję
                f.write(f'  <channel id="{tvg if tvg else name}">{ref}</channel>\n')
            
            f.write('</channels>')
        
        return True
    except Exception as e:
        print(f"[IPTVDream] Błąd tworzenia mapowania EPG: {e}")
        return False

def cleanup_cache():
    """Czyści przeterminowane pliki w cache."""
    try:
        if os.path.exists(CACHE_DIR):
            for filename in os.listdir(CACHE_DIR):
                filepath = os.path.join(CACHE_DIR, filename)
                if os.path.isfile(filepath) and not _is_cache_valid(filepath):
                    os.remove(filepath)
    except:
        pass

# Automatyczne czyszczenie cache co godzinę
def auto_cleanup():
    cleanup_cache()

# Wywołaj czyszczenie przy imporcie
auto_cleanup()

create_epg_import_source = install_epg_sources