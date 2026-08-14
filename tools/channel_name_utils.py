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
_PREFIX_NOISE = set(('VIP','RAW'))
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




# Display-cleaning is intentionally less aggressive than EPG/picon normalization.
# It removes technical country/language prefixes such as |DE|, [PL], DE:, PL -
# while preserving the real on-screen channel/group name including HD/FHD/4K.
_DISPLAY_COUNTRY_TOKENS = set((
    'PL','POL','POLSKA','POLAND','DE','DEU','GER','GERMANY','DEUTSCHLAND',
    'EN','ENG','UK','GB','GBR','US','USA','ES','ESP','SPAIN','ESPANA','FR','FRA',
    'IT','ITA','NL','NLD','TR','TUR','CZ','CZE','SK','SVK','RO','ROU','HU','HUN',
    'AT','AUT','CH','CHE','PT','PRT','GR','GRC','RU','RUS','UA','UKR','AR','ARA',
    'BE','BEL','SE','SWE','NO','NOR','DK','DNK','FI','FIN','IE','IRL','CA','CAN',
    'MX','MEX','BR','BRA','IN','IND','AU','AUS','NZ','NZL','EU','INT','WORLD'
))

_FLAG_RE = re.compile(r'^[\U0001F1E6-\U0001F1FF]{2}\s*', re.UNICODE)


def _is_country_token(token):
    return _safe_text(token).strip().upper() in _DISPLAY_COUNTRY_TOKENS


def strip_country_prefix(name):
    """Remove repeated country/language prefixes from a display name.

    Examples:
      ``|DE| HOPE TV`` -> ``HOPE TV``
      ``[PL] TVP 1 HD`` -> ``TVP 1 HD``
      ``DE: MAGENTA HD`` -> ``MAGENTA HD``

    The function deliberately preserves quality markers (HD/FHD/UHD/4K) and
    does not remove country-looking text from the middle of a legitimate name.
    """
    raw = _safe_text(name).replace('\r', ' ').replace('\n', ' ').strip()
    raw = re.sub(r'\s+', ' ', raw)
    if not raw:
        return ''

    # Optional flag emoji before the technical prefix/name.
    try:
        raw = _FLAG_RE.sub('', raw, count=1).strip()
    except Exception:
        pass

    # A provider may stack more than one marker, so iterate a few times.
    for _i in range(6):
        before = raw

        # Bracketed / pipe wrapped markers: |DE|, [DE], (DE), {DE}
        m = re.match(r'^\s*[\|\[\(\{]\s*([A-Za-z]{2,12})\s*[\|\]\)\}]\s*(?:[\|:;\-–—•»/]+\s*)?', raw)
        if m and _is_country_token(m.group(1)):
            raw = raw[m.end():].strip()

        # Plain uppercase marker followed by an explicit separator: DE |, PL -, UK:
        if raw == before:
            m = re.match(r'^\s*([A-Za-z]{2,12})\s*(?:\||:|;|\-|–|—|•|»|/)\s*', raw)
            if m and _is_country_token(m.group(1)):
                raw = raw[m.end():].strip()

        # Common provider form without a separator: ``DE HOPE TV``. Require an
        # uppercase country token and at least one additional word to reduce
        # false positives for ordinary channel names.
        if raw == before:
            m = re.match(r'^\s*([A-Z]{2,5})\s+(.{2,})$', raw)
            if m and _is_country_token(m.group(1)):
                raw = m.group(2).strip()

        raw = re.sub(r'^\s*[\|:;\-–—•»/]+\s*', '', raw).strip()
        if raw == before:
            break

    return re.sub(r'\s+', ' ', raw).strip()


def clean_display_channel_name(name):
    """Name used in Enigma2 lists and #DESCRIPTION entries."""
    cleaned = strip_country_prefix(name)
    return cleaned or _safe_text(name).strip() or 'No Name'


def clean_bouquet_name(name):
    """Visible bouquet/group name; country prefix removed, quality kept."""
    cleaned = strip_country_prefix(name)
    return cleaned or _safe_text(name).strip() or 'Main'


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
    display = clean_display_channel_name(raw)
    variants = set()
    for v in (raw, display, base, _ascii_fold(raw), _ascii_fold(display), _ascii_fold(base)):
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
