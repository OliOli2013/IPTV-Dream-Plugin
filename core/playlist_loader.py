# -*- coding: utf-8 -*-
"""IPTV Dream v6.5 - MODUŁ ŁADOWANIA PLAYLIST
- Ultra-szybkie ładowanie M3U
- Streamingowe parsowanie
- Inteligentne cache'owanie
- Wielowątkowe pobieranie
- Progresywne ładowanie
"""

import os, re, requests, time, hashlib, json, threading, gzip, io
from twisted.internet import reactor
from .config_manager import ConfigManager
from ..tools.net import http_get, NetError
from ..tools.logger import get_logger, mask_sensitive

class PlaylistLoader:
    """Zaawansowany ładowacz playlist z funkcjami optymalizacji."""
    
    def __init__(self):
        self.config = ConfigManager("/etc/enigma2/iptvdream_v6_config.json")
        self.cache_dir = "/tmp/iptvdream_cache"
        self.session = requests.Session()
        # logger + network settings
        self.log = get_logger("IPTVDream.Playlist", log_file=self.config.get("log_file", "/tmp/iptvdream.log"), debug=bool(self.config.get("debug", False)))
        # Streaming M3U bywa wolne; read timeout 30s powoduje fałszywe "Read timed out".
        # Jeśli użytkownik ma stary config z niskim net_timeout_read, podbijamy go do bezpiecznej wartości.
        try:
            ct = int(self.config.get("net_timeout_connect", 10))
        except Exception:
            ct = 10
        try:
            rt = int(self.config.get("net_timeout_read", 180))
        except Exception:
            rt = 180
        if rt < 90:
            rt = 180
        if ct < 3:
            ct = 3
        self.net_timeout = (ct, rt)
        self.net_retries = int(self.config.get("net_retries", 2))
        self.net_backoff = float(self.config.get("net_backoff", 0.8))
        self.ssl_verify = bool(self.config.get("ssl_verify", False))
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache'
        })
        
        # logger / network tuning
        self.debug = bool(self.config.get("debug", False))
        self.log_file = self.config.get("log_file", "/tmp/iptvdream.log")
        self.logger = get_logger("IPTVDream.Playlist", log_file=self.log_file, debug=self.debug)

        # Upewnij się, że katalog cache istnieje
        os.makedirs(self.cache_dir, exist_ok=True)


    def _meta_path(self, cache_key):
        return os.path.join(self.cache_dir, f"{cache_key}.meta.json")

    def _read_meta(self, cache_key):
        try:
            mp = self._meta_path(cache_key)
            if os.path.exists(mp):
                with open(mp, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _write_meta(self, cache_key, meta):
        try:
            mp = self._meta_path(cache_key)
            with open(mp, 'w', encoding='utf-8') as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    def get_cache_key(self, url):
        """Generuje klucz cache dla URL."""
        return hashlib.md5(url.encode('utf-8')).hexdigest()

    def _cache_key_input(self, url, headers=None):
        """Stable cache-key material for a URL + optional headers.

        Some providers require headers (UA/Referer). We include them in the cache-key only
        when explicitly provided, without breaking older call sites.
        """
        try:
            if headers and isinstance(headers, dict):
                # only include a small subset to avoid cache explosion
                keys = [k for k in headers.keys() if k and str(k).lower() in ("user-agent", "referer", "origin")]
                if keys:
                    sig = "&".join(["%s=%s" % (k, headers.get(k, "")) for k in sorted(keys)])
                    return "%s|%s" % (url, sig)
        except Exception:
            pass
        return url

    def is_cache_valid(self, cache_file, max_age=3600):
        """Sprawdza czy cache jest ważny."""
        if not os.path.exists(cache_file):
            return False
        return (time.time() - os.path.getmtime(cache_file)) < max_age

    def get_cached_content(self, url, headers=None):
        """Pobiera zawartość z cache jeśli dostępna."""
        cache_key = self.get_cache_key(self._cache_key_input(url, headers=headers))
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.m3u")
        
        if self.is_cache_valid(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    return f.read()
            except:
                pass
        return None

    def cache_content(self, url, content, meta=None, headers=None):
        """Zapisuje zawartość do cache (opcjonalnie z metadanymi HTTP)."""
        cache_key = self.get_cache_key(self._cache_key_input(url, headers=headers))
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.m3u")
        meta_file  = os.path.join(self.cache_dir, f"{cache_key}.meta.json")

        try:
            with open(cache_file, 'wb') as f:
                f.write(content)
        except Exception:
            pass

        if meta:
            try:
                with open(meta_file, 'w') as f:
                    json.dump(meta, f, indent=2)
            except Exception:
                pass

    def get_cached_metadata(self, url, headers=None):
        """Returns cached HTTP metadata (ETag/Last-Modified) if present."""
        try:
            cache_key = self.get_cache_key(self._cache_key_input(url, headers=headers))
            meta_file = os.path.join(self.cache_dir, f"{cache_key}.meta.json")
            if os.path.exists(meta_file):
                with open(meta_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}


    def load_m3u_url(self, url, progress_callback=None, headers=None):
        """Streaming M3U download with cache, conditional GET, timeouts and retries."""
        cache_key = self.get_cache_key(self._cache_key_input(url, headers=headers))
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.m3u")

        def _cb(pct, msg):
            try:
                if progress_callback:
                    reactor.callFromThread(progress_callback, pct, msg)
            except Exception:
                pass

        # 1) If cache is valid, attempt conditional GET (ETag / Last-Modified)
        meta = self._read_meta(cache_key)
        cached_ok = self.is_cache_valid(cache_file, max_age=int(self.config.get("cache_max_age", 3600)))
        if cached_ok:
            cond_headers = {}
            etag = meta.get("etag")
            last_mod = meta.get("last_modified")
            if etag:
                cond_headers["If-None-Match"] = etag
            if last_mod:
                cond_headers["If-Modified-Since"] = last_mod

            if cond_headers:
                try:
                    _cb(5, "Checking updates..." if self.config.get("language") == "en" else "Sprawdzanie zmian...")
                    r = http_get(
                        url,
                        session=self.session,
                        headers=dict((headers or {}), **cond_headers) if headers else cond_headers,
                        stream=False,
                        verify=self.ssl_verify,
                        timeout=self.net_timeout,
                        retries=self.net_retries,
                        backoff=self.net_backoff,
                        debug=bool(self.config.get("debug", False)),
                        log_file=self.config.get("log_file", "/tmp/iptvdream.log"),
                    )
                    if getattr(r, "status_code", 200) == 304:
                        _cb(100, "Loaded from cache" if self.config.get("language") == "en" else "Ładowanie z cache...")
                        with open(cache_file, 'rb') as f:
                            return f.read()
                except Exception as e:
                    # On network issues, fall back to cache
                    self.log.debug("Conditional GET failed, using cache: %s", mask_sensitive(e))
                    _cb(100, "Loaded from cache" if self.config.get("language") == "en" else "Ładowanie z cache...")
                    try:
                        with open(cache_file, 'rb') as f:
                            return f.read()
                    except Exception:
                        pass

        # 2) No valid cache or cache disabled -> full download (stream)
        try:
            _cb(1, "Downloading..." if self.config.get("language") == "en" else "Pobieranie...")
            r = http_get(
                url,
                session=self.session,
                headers=headers,
                stream=True,
                verify=self.ssl_verify,
                timeout=self.net_timeout,
                retries=self.net_retries,
                backoff=self.net_backoff,
                debug=bool(self.config.get("debug", False)),
                log_file=self.config.get("log_file", "/tmp/iptvdream.log"),
            )

            total_size = int(r.headers.get('content-length', 0) or 0)
            content = io.BytesIO()
            chunk_size = 8192
            downloaded = 0

            try:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    content.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        if total_size > 0:
                            progress = min(99, (downloaded / float(total_size)) * 100.0)
                            _cb(progress, "Downloaded: %.1f KB" % (downloaded/1024.0) if self.config.get("language") == "en" else "Pobrano: %.1f KB" % (downloaded/1024.0))
                        else:
                            # chunked/unknown size: show activity every ~512KB
                            if downloaded % (512 * 1024) < chunk_size:
                                _cb(20, "Downloaded: %.1f MB" % (downloaded/1024.0/1024.0) if self.config.get("language") == "en" else "Pobrano: %.1f MB" % (downloaded/1024.0/1024.0))
            except requests.exceptions.RequestException:
                # If we have any cache, fall back.
                if os.path.exists(cache_file):
                    try:
                        _cb(100, "Loaded from cache" if self.config.get("language") == "en" else "Ładowanie z cache...")
                        with open(cache_file, 'rb') as f:
                            return f.read()
                    except Exception:
                        pass
                raise

            content_data = content.getvalue()
            # Save cache + metadata
            try:
                self.cache_content(url, content_data, headers=headers)
                meta = {
                    "url": url,
                    "saved_at": time.time(),
                    "size": len(content_data),
                    "etag": r.headers.get("ETag", ""),
                    "last_modified": r.headers.get("Last-Modified", ""),
                }
                self._write_meta(cache_key, meta)
            except Exception:
                pass

            _cb(100, "Done" if self.config.get("language") == "en" else "Gotowe")
            return content_data

        except Exception as e:
            raise Exception("M3U load error: %s" % e)

    def load_m3u_file(self, file_path):
        """Ładuje M3U z pliku."""
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            raise Exception(f"Błąd odczytu pliku: {e}")

    def parse_m3u_content(self, content, progress_callback=None):
        """
        NOWE: Streamingowe parsowanie M3U!
        Przetwarza zawartość w czasie rzeczywistym.
        """
        channels = []
        
        try:
            # Dekodowanie z obsługą błędów
            try:
                text = content.decode("utf-8", "ignore")
            except:
                text = str(content)
            
            # Regexy - skompilowane dla lepszej wydajności
            extinf_pattern = re.compile(r'#EXTINF:([^,]*),(.*)', re.IGNORECASE)
            attr_pattern = re.compile(r'([a-zA-Z0-9_-]+)\s*=\s*("[^"]*"|[^,;\s]+)')
            # Uwaga: group_pattern jest też używany w _parse_extinf().
            # Przekazujemy go jawnie, żeby uniknąć NameError "group_pattern is not defined".
            group_pattern = re.compile(r'^\[([^\]]+)\]')
            adult_pattern = re.compile(r'(xxx|adult|porn|sex|erotic|18\+|mature)', re.IGNORECASE)
            vod_pattern = re.compile(r'(vod|movie|film|video|series|serial)', re.IGNORECASE)
            
            lines = text.splitlines()
            current_entry = {}
            total_lines = len(lines)
            processed = 0
            
            for line in lines:
                processed += 1
                line = line.strip()
                if not line:
                    continue
                
                # #EXTINF
                if line.startswith("#EXTINF"):
                    current_entry = self._parse_extinf(line, extinf_pattern, attr_pattern, group_pattern)
                    
                # #EXTGRP
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
                    if "group" not in current_entry or not current_entry["group"]:
                        title_lower = current_entry.get("title", "").lower()
                        
                        if adult_pattern.search(title_lower):
                            current_entry["group"] = "XXX"
                        elif vod_pattern.search(title_lower):
                            current_entry["group"] = "VOD"
                        elif '/movie/' in url.lower() or '/series/' in url.lower():
                            current_entry["group"] = "VOD"
                        else:
                            current_entry["group"] = "Inne"
                    
                    # Tworzenie kanału
                    channel = {
                        "title": current_entry.get("title", "No Name"),
                        "url": url,
                        "group": current_entry.get("group", "Inne"),
                        "logo": current_entry.get("logo", ""),
                        "epg_id": current_entry.get("epg_id", "")
                    }
                    
                    channels.append(channel)
                    current_entry = {}
                    
                    # Aktualizuj progress co 100 kanałów
                    if progress_callback and len(channels) % 100 == 0:
                        progress = min(100, (processed / total_lines) * 100)
                        reactor.callFromThread(progress_callback, progress, 
                                             f"Przetwarzanie: {len(channels)} kanałów")
            
            return channels
            
        except Exception as e:
            raise Exception(f"Błąd parsowania M3U: {e}")

    def _parse_extinf(self, line, extinf_pattern, attr_pattern, group_pattern=None):
        """Parsuje linię EXTINF."""
        entry = {}
        
        # Podział na metadane i tytuł
        if ',' in line:
            parts = line.split(',', 1)
            meta_part = parts[0]
            entry["title"] = parts[1].strip() if len(parts) > 1 else "No Name"
        else:
            meta_part = line
            entry["title"] = "No Name"

        # Szukanie atrybutów
        attrs = attr_pattern.findall(meta_part)
        for key, val in attrs:
            clean_val = val.replace('"', '').strip()
            key_lower = key.lower()
            
            if key_lower in ["group-title", "group", "category", "cat"]:
                entry["group"] = clean_val
            elif key_lower in ["tvg-logo", "logo"]:
                entry["logo"] = clean_val
            elif key_lower in ["tvg-id", "epg-id", "id"]:
                entry["epg_id"] = clean_val
        
        # Jeśli brak grupy, szukaj w tytule
        if "group" not in entry and group_pattern is not None:
            try:
                group_match = group_pattern.match(entry.get("title", ""))
                if group_match:
                    entry["group"] = group_match.group(1).strip()
            except Exception:
                pass
        
        return entry

    def load_with_progress(self, url, progress_callback):
        """
        Główna funkcja ładująca z progress barem.
        Zwraca listę kanałów.
        """
        try:
            # 1. Załaduj zawartość
            content = self.load_m3u_url(url, progress_callback)
            
            # 2. Parsuj z progress barem
            channels = self.parse_m3u_content(content, progress_callback)
            
            return channels
            
        except Exception as e:
            raise e

    def get_playlist_info(self, url):
        """Pobiera informacje o playlistie bez pełnego ładowania."""
        try:
            response = self.session.head(url, timeout=10)
            info = {
                "url": url,
                "status_code": response.status_code,
                "content_type": response.headers.get('content-type', 'unknown'),
                "content_length": int(response.headers.get('content-length', 0)),
                "last_modified": response.headers.get('last-modified', 'unknown')
            }
            return info
        except:
            return {"url": url, "status_code": 0, "error": "Nieznany"}

    def cleanup_cache(self, max_age=86400):
        """Czyści przeterminowane pliki cache."""
        try:
            if os.path.exists(self.cache_dir):
                for filename in os.listdir(self.cache_dir):
                    filepath = os.path.join(self.cache_dir, filename)
                    if os.path.isfile(filepath):
                        file_age = time.time() - os.path.getmtime(filepath)
                        if file_age > max_age:
                            os.remove(filepath)
        except:
            pass

    def get_performance_stats(self):
        """Zwraca statystyki wydajności."""
        cache_files = len([f for f in os.listdir(self.cache_dir) if os.path.isfile(os.path.join(self.cache_dir, f))])
        
        return {
            "Cache size": f"{cache_files} plików",
            "Cache directory": self.cache_dir,
            "Session active": "Tak" if self.session else "Nie",
            "Last cleanup": "Automatyczna"
        }

# NOWE: Klasa pomocnicza do obsługi playlist
class PlaylistCache:
    """Zaawansowany cache dla playlist."""
    
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        self.cache_index = os.path.join(cache_dir, "index.json")
        self.load_index()
    
    def load_index(self):
        """Wczytuje indeks cache."""
        try:
            if os.path.exists(self.cache_index):
                with open(self.cache_index, 'r') as f:
                    self.index = json.load(f)
            else:
                self.index = {}
        except:
            self.index = {}
    
    def save_index(self):
        """Zapisuje indeks cache."""
        try:
            with open(self.cache_index, 'w') as f:
                json.dump(self.index, f, indent=2)
        except:
            pass
    
    def add_to_cache(self, url, metadata):
        """Dodaje wpis do cache."""
        cache_key = hashlib.md5(url.encode('utf-8')).hexdigest()
        self.index[cache_key] = {
            "url": url,
            "metadata": metadata,
            "timestamp": time.time()
        }
        self.save_index()
    
    def get_from_cache(self, url):
        """Pobiera z cache."""
        cache_key = hashlib.md5(url.encode('utf-8')).hexdigest()
        if cache_key in self.index:
            entry = self.index[cache_key]
            # Sprawdź ważność (1 godzina)
            if time.time() - entry.get("timestamp", 0) < 3600:
                return entry.get("metadata")
        return None

# NOWE: Monitor wydajności
class PerformanceMonitor:
    """Monitoruje wydajność wtyczki."""
    
    def __init__(self, log_file):
        self.log_file = log_file
        self.stats = {
            "total_loads": 0,
            "total_channels": 0,
            "total_time": 0,
            "errors": 0
        }
        self.load_stats()
    
    def load_stats(self):
        """Wczytuje statystyki."""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    self.stats = json.load(f)
        except:
            pass
    
    def save_stats(self):
        """Zapisuje statystyki."""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except:
            pass
    
    def record_load(self, channel_count, load_time, error=False):
        """Rejestruje ładowanie."""
        self.stats["total_loads"] += 1
        self.stats["total_channels"] += channel_count
        self.stats["total_time"] += load_time
        if error:
            self.stats["errors"] += 1
        self.save_stats()
    
    def get_stats(self):
        """Zwraca statystyki."""
        avg_time = self.stats["total_time"] / self.stats["total_loads"] if self.stats["total_loads"] > 0 else 0
        avg_channels = self.stats["total_channels"] / self.stats["total_loads"] if self.stats["total_loads"] > 0 else 0
        
        return {
            "Załadowane playlisty": self.stats["total_loads"],
            "Kanały łącznie": self.stats["total_channels"],
            "Błędy": self.stats["errors"],
            "Średni czas": f"{avg_time:.1f}s",
            "Średnio kanałów": f"{avg_channels:.0f}",
            "Wydajność": f"{avg_channels/avg_time:.0f} kan/s" if avg_time > 0 else "N/A"
        }