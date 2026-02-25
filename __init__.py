# -*- coding: utf-8 -*-
"""IPTV Dream - Package Initialization"""

def _read_version():
    """Read version from bundled VERSION file.

    Keeps UI/version strings consistent even if opkg metadata differs.
    """
    try:
        import os
        here = os.path.dirname(__file__)
        vp = os.path.join(here, "VERSION")
        if os.path.exists(vp):
            with open(vp, "r", encoding="utf-8") as f:
                v = (f.read() or "").strip()
                if v:
                    return v
    except Exception:
        pass
    return "6.5"

__version__ = _read_version()
__author__ = "IPTV Dream Team"
__license__ = "GPLv2"
__description__ = "Ultra-fast IPTV plugin for Enigma2 - REVOLUTION!"

# Package metadata
PLUGIN_NAME = "IPTV Dream v%s" % __version__
PLUGIN_VERSION = __version__
PLUGIN_DESCRIPTION = "Wtyczka IPTV (PL/EN) - REWOLUCJA / REVOLUTION!"

# Import main classes
from .dream_v6 import IPTVDreamMain
from .export_v2 import export_bouquets, add_to_bouquets_index

# Make main classes available
__all__ = [
    'IPTVDreamMain',
    'export_bouquets',
    'add_to_bouquets_index',
    'PLUGIN_NAME',
    'PLUGIN_VERSION',
    'PLUGIN_DESCRIPTION'
]