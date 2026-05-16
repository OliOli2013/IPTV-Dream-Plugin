# -*- coding: utf-8 -*-
"""
IPTV Dream - normalizacja nazw kanałów dla EPG i picon.
Mechanizm wzorowany na sprawdzonych rozwiązaniach TvMad:
- czyszczenie prefiksów krajowych i jakościowych,
- generowanie wielu wariantów nazwy,
- obsługa aliasów z pliku picon_name_aliases.txt.
"""
from __future__ import absolute_import, print_function

import os
import re
import unicodedata

_COUNTRY_TOKENS = set((
    'PL','POL','POLAND','POLSKA','EN','UK','GB','US','USA','DE','GER','GERMANY','DEUTSCHLAND',
    'ES','ESP','SPAIN','ESPANA','AR','ARA','ARABIC','FR','IT','NL','TR','CZ','SK','RO','HU',
    'VIP','RAW','INT','EU','EUROPE','WORLD'
))
_PREFIX_NOISE = set(('VIP','RAW','TV','LIVE','CHANNEL','CANAL','KANAŁ','KANAL'))
_QUALITY_TOKENS = set(('HD','FHD','UHD','4K','8K','SD','HEVC','H265','H264','1080P','720P','50FPS'))
_ALIAS_CACHE = None


def _safe_text(v):
    try:
        if v is None:
            return ''
        return str(v)
    except Exception:
        return ''


def _ascii_fold(text):
    try:
        text = unicodedata.normalize('NFKD', _safe_text(text))
        return ''.join(c for c in text if not unicodedata.combining(c))
    except Exception:
        return _safe_text(text)


def _tokenize_display(name):
    s = _ascii_fold(name)
    s = s.replace('&', ' and ').replace('+', ' plus ')
    s = re.sub(r'[\[\]{}()]+', ' ', s)
    s = re.sub(r'[|:;,_/\\\-\.]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return [x for x in s.split(' ') if x]


def _expand_compact_token(tok):
    tok = _safe_text(tok).strip()
    if not tok:
        return []
    up = tok.upper()
    # TVP1 -> TVP 1, HBO2 -> HBO 2, CANALPLUS4K -> CANAL PLUS 4K
    m = re.match(r'^([A-Z]+)(\d+)$', up)
    if m:
        return [m.group(1), m.group(2)]
    return [tok]


def _normalize_display_tokens(tokens):
    out = []
    for tok in tokens:
        t = _safe_text(tok).strip()
        if not t:
            continue
        up = t.upper()
        # Usuń tagi jakościowe z końców nazw, ale nie z samych nazw typu 4FUN.
        if up in _QUALITY_TOKENS:
            continue
        if up.endswith('HD') and len(up) > 3 and not up.startswith('HBO'):
            t = re.sub(r'HD$', '', t, flags=re.I).strip()
        if up.startswith('FHD') or up.startswith('UHD'):
            continue
        if t:
            out.extend(_expand_compact_token(t))
    return out


def _canonical_live_name(name):
    tokens = _tokenize_display(name)
    # prefixy typu PL, DE, VIP na początku
    while tokens and tokens[0].upper() in (_COUNTRY_TOKENS | _PREFIX_NOISE):
        tokens.pop(0)
    # sufiksy typu PL/HD/FHD na końcu
    while tokens and tokens[-1].upper() in (_COUNTRY_TOKENS | _QUALITY_TOKENS):
        tokens.pop()
    tokens = _normalize_display_tokens(tokens)
    s = ' '.join(tokens).strip()
    s = re.sub(r'\s+', ' ', s)
    return s or _safe_text(name).strip()


def clean_live_channel_name(name):
    return _canonical_live_name(name)


def normalize_channel_key(name, keep_quality=False):
    s = _canonical_live_name(name)
    tokens = _tokenize_display(s)
    if not keep_quality:
        tokens = [t for t in tokens if t.upper() not in _QUALITY_TOKENS]
    # Jednolity klucz bez znaków specjalnych.
    key = ''.join(tokens).lower()
    key = re.sub(r'[^a-z0-9]+', '', key)
    return key


def channel_name_variants(name):
    base = _canonical_live_name(name)
    raw = _safe_text(name).strip()
    variants = set()
    for v in (raw, base, _ascii_fold(raw), _ascii_fold(base)):
        v = (v or '').strip()
        if not v:
            continue
        variants.add(v)
        variants.add(v.lower())
        variants.add(re.sub(r'\s+', '', v).lower())
        variants.add(re.sub(r'[^A-Za-z0-9]+', '_', _ascii_fold(v)).strip('_').lower())
        variants.add(re.sub(r'[^A-Za-z0-9]+', '', _ascii_fold(v)).lower())
    key = normalize_channel_key(name)
    if key:
        variants.add(key)
    # Popularne warianty z kanałami numerowanymi.
    m = re.match(r'^(.*?)(\d+)$', base.strip())
    if m:
        prefix = m.group(1).strip()
        num = m.group(2)
        if prefix:
            variants.add((prefix + num).lower().replace(' ', ''))
            variants.add((prefix + '_' + num).lower().replace(' ', '_'))
            variants.add((prefix + '-' + num).lower().replace(' ', '-'))
            variants.add((prefix + '.' + num).lower().replace(' ', '.'))
    return [v for v in variants if v]


def _alias_file_path():
    return os.path.join(os.path.dirname(__file__), 'picon_name_aliases.txt')


def load_picon_alias_index():
    global _ALIAS_CACHE
    if _ALIAS_CACHE is not None:
        return _ALIAS_CACHE
    idx = {}
    path = _alias_file_path()
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    s = (line or '').strip()
                    if not s or s.startswith('#'):
                        continue
                    key = normalize_channel_key(s)
                    if key:
                        idx.setdefault(key, []).append(s)
    except Exception:
        idx = {}
    _ALIAS_CACHE = idx
    return idx


def _special_alias_candidates(name):
    out = set()
    key = normalize_channel_key(name)
    if key:
        out.add(key)
    # XXX/adult – często bez właściwego tvg-id.
    low = _safe_text(name).lower()
    if any(x in low for x in ('xxx', 'adult', '18+', 'porn', 'erotic', 'sex')):
        out.update(['xxx', 'adult', 'xxx.tv', 'adult.tv'])
    return out


def alias_candidates(name):
    out = set()
    try:
        idx = load_picon_alias_index()
        for v in channel_name_variants(name):
            key = normalize_channel_key(v)
            if key:
                out.add(key)
                for a in idx.get(key, []):
                    out.add(a)
                    out.add(re.sub(r'[^A-Za-z0-9]+', '_', _ascii_fold(a)).strip('_').lower())
                    out.add(normalize_channel_key(a))
        out.update(_special_alias_candidates(name))
    except Exception:
        pass
    return [v for v in out if v]
