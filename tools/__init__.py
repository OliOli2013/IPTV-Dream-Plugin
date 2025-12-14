# -*- coding: utf-8 -*-
"""
Moduł narzędzi dla wtyczki IPTV Dream v5.1
"""

from . import lang
from . import mac_portal
from . import updater
from . import xtream_one_window
from . import bouquet_picker
from . import epg_picon
from . import webif

# Wersja modułu narzędzi
TOOLS_VERSION = "5.1"

__all__ = [
    'lang',
    'mac_portal', 
    'updater',
    'xtream_one_window',
    'bouquet_picker',
    'epg_picon',
    'webif',
    'TOOLS_VERSION'
]