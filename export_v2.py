# -*- coding: utf-8 -*-
"""
IPTV Dream v6.6.3 - eksport bukietów + EPG/Picon.

Wersja przebudowana pod mechanizmy zgodne z TvMad:
- normalizacja nazw kanałów i aliasy picon,
- wiele wariantów identyfikatorów EPG Import,
- linkowanie/kopiowanie picon pod nazwy service-ref,
- bezpieczne, unikalne nazwy bukietów.
"""
from __future__ import absolute_import, print_function

import os
import re
import zlib
import shutil
import urllib.parse
from xml.sax.saxutils import escape

try:
    from enigma import eDVBDB
except Exception:
    eDVBDB = None

try:
    from .tools.channel_name_utils import clean_live_channel_name, normalize_channel_key, channel_name_variants, alias_candidates
except Exception:
    clean_live_channel_name = None
    normalize_channel_key = None
    channel_name_variants = None
    alias_candidates = None

BOUQUET_DIR = "/etc/enigma2"
EPG_DIR = "/etc/epgimport"
EPG_CHANNEL_FILE = os.path.join(EPG_DIR, "iptvdream.channels.xml")
EPG_SOURCE_FILE = os.path.join(EPG_DIR, "iptvdream.sources.xml")
PICON_DEST_DIR = "/usr/share/enigma2/picon"
PICON_SOURCE_DIRS = [
    "/usr/share/enigma2/picon",
    "/picon",
    "/picon/logos",
    "/media/hdd/picon",
    "/media/usb/picon",
    "/media/mmc/picon",
    "/etc/enigma2/picon",
]

# User-Agent MAG250 dla odtwarzania strumieni IPTV.
RAW_UA = "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"


def _safe_text(v):
    try:
        if v is None:
            return ""
        return str(v)
    except Exception:
        return ""


def sanit(name):
    name = _safe_text(name).strip()
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name if name else "Unknown"


def sanit_title(name):
    if not name:
        return "No Name"
    name = _safe_text(name).replace('\n', '').strip()
    name = re.sub(r'tvg-[a-z]+="[^"]*"', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[\(\[].*?[\)\]]', '', name)
    name = re.sub(r'^(PL|EN|DE|IT|UK|US|ES|AR|VIP|RAW|FHD|UHD|HEVC|4K)\s*[|:-]?\s*', '', name, flags=re.IGNORECASE)
    # Nie usuwamy agresywnie XXX/adult – to była jedna z przyczyn gubienia treści dla dorosłych.
    tags = ['HD', 'FHD', 'UHD', '4K', 'RAW', 'VIP', 'PL', 'SD', 'HEVC', 'H265', 'UK', 'US', 'DE', 'ES']
    for tag in tags:
        name = re.sub(r'\s+[-|]?\s*' + tag + r'$', '', name, flags=re.IGNORECASE)
    name = name.replace('|', ' ').replace('"', '').strip()
    name = re.sub(r'\s+', ' ', name)
    if clean_live_channel_name:
        try:
            cleaned = clean_live_channel_name(name)
            if cleaned and len(cleaned) >= 2:
                name = cleaned
        except Exception:
            pass
    return name if len(name) >= 2 else "Stream"


def _mk_bouquet_filename(bq_name, group_name):
    safe_bq = sanit(bq_name or "IPTV")
    safe_grp = sanit(group_name or "Main")
    sig = zlib.crc32((safe_bq + "|" + safe_grp).encode("utf-8", "ignore")) & 0xffffffff
    safe_bq_s = safe_bq[:28]
    safe_grp_s = safe_grp[:28]
    return ("userbouquet.iptv_dream_%s_%s_%08x.tv" % (safe_bq_s, safe_grp_s, sig)).lower()


def _stable_sid(url, title=""):
    raw = (_safe_text(url) + "|" + _safe_text(title)).encode("utf-8", "ignore")
    sid = zlib.crc32(raw) & 0xffff
    return sid or 1


def _short_service_ref(service_ref):
    ref = _safe_text(service_ref).strip()
    if not ref:
        return ""
    # Full IPTV service refs contain URL and title after the 10th colon. Picon/EPG mapping uses the technical part.
    parts = ref.split(':')
    if len(parts) >= 10:
        return ':'.join(parts[:10])
    return ref.rstrip(':')


def _service_ref_import_variants(ref):
    short = _short_service_ref(ref)
    out = []
    if short:
        out.append(short)
        out.append(short + ':')
        # Część EPGImport zapisuje bez lub z końcowym dwukropkiem.
        if short.startswith('4097:'):
            out.append('5002:' + short.split(':', 1)[1])
            out.append('1:' + short.split(':', 1)[1])
        elif short.startswith('5002:'):
            out.append('4097:' + short.split(':', 1)[1])
            out.append('1:' + short.split(':', 1)[1])
    # Unikalne, bez pustych.
    seen = set()
    clean = []
    for x in out:
        x = x.strip()
        if x and x not in seen:
            seen.add(x)
            clean.append(x)
    return clean


def _service_ref_picon_basenames(ref):
    out = []
    for v in _service_ref_import_variants(ref):
        base = v.replace(':', '_').strip('_')
        if base:
            out.append(base)
            out.append(base + '_')
    # dedupe
    seen = set()
    return [x for x in out if not (x in seen or seen.add(x))]


def _picon_name_variants(channel_name, tvg_id=""):
    vals = set()
    for raw in (channel_name, tvg_id):
        raw = _safe_text(raw).strip()
        if not raw:
            continue
        vals.add(raw)
        vals.add(raw.lower())
        vals.add(raw.replace(' ', '').lower())
        vals.add(re.sub(r'[^A-Za-z0-9]+', '_', raw).strip('_').lower())
        vals.add(re.sub(r'[^A-Za-z0-9]+', '', raw).lower())
        try:
            if normalize_channel_key:
                k = normalize_channel_key(raw)
                if k:
                    vals.add(k)
        except Exception:
            pass
        try:
            if channel_name_variants:
                vals.update(channel_name_variants(raw))
        except Exception:
            pass
        try:
            if alias_candidates:
                vals.update(alias_candidates(raw))
        except Exception:
            pass
    return [v for v in vals if v]


def _find_existing_picon(channel_name, tvg_id=""):
    cands = []
    for v in _picon_name_variants(channel_name, tvg_id):
        cands.append(v)
    # szukaj bez wielkości znaków i z typowymi rozszerzeniami
    dirs = []
    for d in PICON_SOURCE_DIRS:
        if d not in dirs:
            dirs.append(d)
    for d in dirs:
        try:
            if not os.path.isdir(d):
                continue
            names = set(os.listdir(d))
        except Exception:
            continue
        lower_map = {}
        try:
            for n in names:
                lower_map.setdefault(n.lower(), n)
        except Exception:
            lower_map = {}
        for c in cands:
            for ext in ('.png', '.PNG'):
                fn = c + ext
                real = lower_map.get(fn.lower())
                if real:
                    path = os.path.join(d, real)
                    if os.path.exists(path):
                        return path
    return None


def _ensure_dir(path):
    try:
        if not os.path.isdir(path):
            os.makedirs(path)
    except Exception:
        pass


def _copy_or_link(src, dst):
    try:
        if not src or not os.path.exists(src):
            return False
        _ensure_dir(os.path.dirname(dst))
        if os.path.exists(dst) or os.path.islink(dst):
            return True
        try:
            os.symlink(src, dst)
            return True
        except Exception:
            shutil.copyfile(src, dst)
            return True
    except Exception:
        return False


def _link_picon_for_channel(channel_name, tvg_id, service_refs, dest_dir=PICON_DEST_DIR):
    src = _find_existing_picon(channel_name, tvg_id)
    if not src:
        return False
    ok = False
    targets = []
    for ref in service_refs or []:
        for b in _service_ref_picon_basenames(ref):
            targets.append(os.path.join(dest_dir, b + '.png'))
    # Dodatkowo nazwy tekstowe, dla skinów/wtyczek szukających po nazwie kanału.
    for b in _picon_name_variants(channel_name, tvg_id)[:20]:
        targets.append(os.path.join(dest_dir, b + '.png'))
    seen = set()
    for t in targets:
        if not t or t in seen:
            continue
        seen.add(t)
        if os.path.abspath(src) == os.path.abspath(t):
            ok = True
            continue
        if _copy_or_link(src, t):
            ok = True
    return ok


def _is_adult_channel(title, group=""):
    hay = (title + ' ' + group).lower()
    return any(x in hay for x in ('xxx', 'adult', '18+', '+18', 'porn', 'porno', 'erotic', 'sex'))


def _is_vod_like(title, group="", url=""):
    hay = (title + ' ' + group + ' ' + url).lower()
    # VOD/series exports can be massive; they normally do not need live EPGImport mappings.
    return any(x in hay for x in ('vod', 'movie', 'movies', 'film', 'films', 'series', 'serial', 'seriale', '/movie/', '/series/'))


def _epg_id_variants(name, tvg_id="", group=""):
    ids = set()
    tvg_id = _safe_text(tvg_id).strip()
    name = _safe_text(name).strip()
    group = _safe_text(group).strip()
    if tvg_id:
        ids.add(tvg_id)
    if name:
        ids.add(name)
    try:
        if channel_name_variants:
            ids.update(channel_name_variants(name))
    except Exception:
        pass
    try:
        if alias_candidates:
            ids.update(alias_candidates(name))
    except Exception:
        pass

    # TvMad-style suffix expansion for common XMLTV sources.
    suffixes = ['pl', 'gb', 'uk', 'us', 'de', 'at', 'ch', 'es', 'mx', 'ar', 'ru', 'fr', 'it', 'nl', 'tr', 'cz', 'sk', 'ro', 'hu', 'eu', 'world']
    base_names = set()
    for v in list(ids):
        v = _safe_text(v).strip()
        if not v:
            continue
        compact = re.sub(r'\s+', '', v)
        kebab = re.sub(r'\s+', '-', v.lower())
        dotted = re.sub(r'\s+', '.', v.lower())
        underscored = re.sub(r'\s+', '_', v.lower())
        base_names.update([compact, kebab, dotted, underscored])
    ids.update(base_names)
    for v in list(base_names):
        for suf in suffixes:
            ids.add('%s.%s' % (v, suf))

    simple = re.sub(r'\b(HD|FHD|UHD|4K|RAW|VIP|PL|TV|CHANNEL)\b', '', name, flags=re.I).strip()
    if simple and simple != name:
        ids.add(simple)
        ids.add(re.sub(r'\s+', '', simple))
        for suf in suffixes:
            ids.add('%s.%s' % (re.sub(r'\s+', '', simple), suf))

    if _is_adult_channel(name, group):
        ids.update(['xxx', 'adult', 'xxx.tv', 'adult.tv'])

    # Usuń śmieci i ogranicz liczbę wpisów, żeby plik EPGImport nie rósł absurdalnie.
    out = []
    seen = set()
    for x in ids:
        x = _safe_text(x).strip()
        if not x or len(x) > 160:
            continue
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out[:45]


def add_to_bouquets_index(bq_filename):
    idx = os.path.join(BOUQUET_DIR, "bouquets.tv")
    entry = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "%s" ORDER BY bouquet\n' % bq_filename
    try:
        lines = []
        if os.path.exists(idx):
            with open(idx, "r", errors="ignore") as f:
                lines = f.readlines()
        if not any(entry.strip() == line.strip() for line in lines):
            lines.append(entry)
            with open(idx, "w") as f:
                f.writelines(lines)
    except Exception:
        pass


def _write_epg_sources():
    """Create/refresh IPTV Dream EPGImport source file without touching user channel mappings."""
    try:
        _ensure_dir(EPG_DIR)
        # Główne źródła podobne do starszych wersji, ale rozszerzone o DE/ES/AR.
        sources = [
            ("IPTV Dream - Poland", "http://epg.ovh/pl.xml.gz"),
            ("IPTV Dream - Poland open-epg", "https://www.open-epg.com/files/poland2.xml.gz"),
            ("IPTV Dream - Germany", "https://iptv-epg.org/files/epg-de.xml.gz"),
            ("IPTV Dream - Spain", "https://iptv-epg.org/files/epg-es.xml.gz"),
            ("IPTV Dream - UK", "https://iptv-epg.org/files/epg-gb.xml.gz"),
            ("IPTV Dream - USA", "https://iptv-epg.org/files/epg-us.xml.gz"),
            ("IPTV Dream - France", "https://iptv-epg.org/files/epg-fr.xml.gz"),
            ("IPTV Dream - Italy", "https://iptv-epg.org/files/epg-it.xml.gz"),
            ("IPTV Dream - Russia", "https://iptv-epg.org/files/epg-ru.xml.gz"),
            ("IPTV Dream - World Mix", "http://epg.bevy.be/bevy.xml.gz"),
        ]
        buf = ['<?xml version="1.0" encoding="utf-8"?>\n<sources>\n', '  <sourcecat sourcecatname="IPTV Dream EPG">\n']
        for desc, url in sources:
            buf.append('    <source type="gen_xmltv" channels="iptvdream.channels.xml">\n')
            buf.append('      <description>%s</description>\n' % escape(desc))
            buf.append('      <url>%s</url>\n' % escape(url))
            buf.append('    </source>\n')
        buf.append('  </sourcecat>\n</sources>\n')
        tmp = EPG_SOURCE_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(''.join(buf))
        try:
            os.replace(tmp, EPG_SOURCE_FILE)
        except Exception:
            os.rename(tmp, EPG_SOURCE_FILE)
        return True
    except Exception as e:
        print('[IPTVDream] EPG source write error: %s' % e)
        return False


def create_epg_xml(mapping):
    """Write EPGImport channel mapping with many XMLTV aliases."""
    try:
        _ensure_dir(EPG_DIR)
        tmp = EPG_CHANNEL_FILE + '.tmp'
        visited = set()
        with open(tmp, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n<channels>\n')
            for entry in mapping or []:
                try:
                    ref = entry.get('ref') if isinstance(entry, dict) else entry[0]
                    name = entry.get('name') if isinstance(entry, dict) else entry[1]
                    tvg = entry.get('tvg') if isinstance(entry, dict) else (entry[2] if len(entry) > 2 else '')
                    group = entry.get('group') if isinstance(entry, dict) else (entry[3] if len(entry) > 3 else '')
                except Exception:
                    continue
                for r in _service_ref_import_variants(ref):
                    for xid in _epg_id_variants(name, tvg, group):
                        key = r + '|' + xid
                        if key in visited:
                            continue
                        visited.add(key)
                        f.write('  <channel id="%s">%s</channel>\n' % (escape(xid), escape(r)))
            f.write('</channels>\n')
        try:
            os.replace(tmp, EPG_CHANNEL_FILE)
        except Exception:
            os.rename(tmp, EPG_CHANNEL_FILE)
        _write_epg_sources()
        return True
    except Exception as e:
        print('[IPTVDream] Błąd EPG XML: %s' % e)
        return False


def export_bouquets(playlist, bouquet_name=None, keep_groups=True, service_type="4097"):
    """Eksportuje playlistę do bukietów Enigma2 + tworzy EPGImport i picon aliases."""
    try:
        service_type = str(int(service_type))
    except Exception:
        service_type = str(service_type or "4097")

    groups = {}
    for ch in playlist or []:
        grp = ch.get("group", "Main") if keep_groups else "Main"
        grp = _safe_text(grp).strip() or "Main"
        groups.setdefault(grp, []).append(ch)

    total_channels = 0
    total_bouquets = 0
    epg_mapping = []
    picon_tasks = []

    ua_encoded = urllib.parse.quote(RAW_UA)
    ua_suffix = "#User-Agent=%s" % ua_encoded

    for grp, chans in groups.items():
        filename = _mk_bouquet_filename(bouquet_name, grp)
        bq_fullpath = os.path.join(BOUQUET_DIR, filename)
        try:
            _ensure_dir(BOUQUET_DIR)
            with open(bq_fullpath, "w", encoding="utf-8") as f:
                f.write("#NAME %s - %s\n" % (bouquet_name or "IPTV", grp))
                for ch in chans:
                    url = _safe_text(ch.get("url", "")).strip()
                    if not url:
                        continue
                    title_raw = ch.get("title") or ch.get("name") or "No Name"
                    title = sanit_title(title_raw)
                    tvg_id = (ch.get("epg_id") or ch.get("tvg-id") or ch.get("tvg_id") or ch.get("tvg-name") or ch.get("tvg_name") or "")
                    logo = (ch.get("logo") or ch.get("tvg-logo") or ch.get("tvg_logo") or "")
                    url = url.replace(" ", "%20")
                    if "User-Agent" not in url and "user-agent" not in url.lower():
                        url += ua_suffix
                    sid = _stable_sid(url, title)
                    sid_hex = "%X" % sid
                    ref_prefix = "%s:0:1:%s:0:0:0:0:0:0" % (service_type, sid_hex)
                    full_ref = "%s:%s:%s" % (ref_prefix, url, title)
                    f.write("#SERVICE %s\n" % full_ref)
                    f.write("#DESCRIPTION %s\n" % title)

                    refs = [ref_prefix]
                    # Keep EPG/Picon compatible across common IPTV players.
                    for alt_type in ("4097", "5002", "1"):
                        refs.append("%s:0:1:%s:0:0:0:0:0:0" % (alt_type, sid_hex))
                    # Do not generate huge EPGImport maps for VOD/series libraries; this was a common
                    # reason for blue/green screen during "export all" on large MAC/Xtream lists.
                    if not _is_vod_like(title, grp, url):
                        for r in refs:
                            epg_mapping.append({'ref': r, 'name': title, 'tvg': tvg_id, 'group': grp})
                    picon_tasks.append((title, tvg_id, refs, logo))
                    total_channels += 1
        except Exception as e:
            print('[IPTVDream] Export bouquet error %s: %s' % (filename, e))
            continue

        add_to_bouquets_index(filename)
        total_bouquets += 1

    create_epg_xml(epg_mapping)

    # Picon: link/copy existing picons to service-ref filenames. This is fast and does not require network.
    linked = 0
    for title, tvg_id, refs, logo in picon_tasks:
        try:
            if _link_picon_for_channel(title, tvg_id, refs, PICON_DEST_DIR):
                linked += 1
        except Exception:
            pass

    try:
        if eDVBDB:
            eDVBDB.getInstance().reloadBouquets()
            eDVBDB.getInstance().reloadServicelist()
    except Exception:
        pass

    return total_bouquets, total_channels


def create_satellite_epg_mapping():
    """Compatibility stub kept for old imports."""
    return False


def export_epg_to_m3u(playlist, filename="/tmp/iptvdream_with_epg.m3u"):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for channel in playlist or []:
                title = channel.get('title', 'No Name')
                url = channel.get('url', '')
                group = channel.get('group', 'Inne')
                logo = channel.get('logo') or channel.get('tvg-logo') or ''
                epg_id = channel.get('epg_id') or channel.get('tvg-id') or ''
                extinf = '#EXTINF:-1'
                if group:
                    extinf += ' group-title="%s"' % group
                if logo:
                    extinf += ' tvg-logo="%s"' % logo
                if epg_id:
                    extinf += ' tvg-id="%s"' % epg_id
                extinf += ',%s\n' % title
                f.write(extinf)
                f.write("%s\n" % url)
        return filename
    except Exception as e:
        print('[IPTVDream] Błąd eksportu M3U z EPG: %s' % e)
        return None


create_epg_import_source_with_mapping = create_epg_xml
