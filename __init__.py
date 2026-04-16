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
    return "6.5.2"

__version__ = _read_version()
__author__ = "IPTV Dream Team"
__license__ = "GPLv2"
__description__ = "Ultra-fast IPTV plugin for Enigma2 - REVOLUTION!"

# Package metadata
PLUGIN_NAME = "IPTV Dream v%s" % __version__
PLUGIN_VERSION = __version__
PLUGIN_DESCRIPTION = "Wtyczka IPTV (PL/EN) - REWOLUCJA / REVOLUTION!"

# Do not eagerly import Enigma2 UI modules here. The plugin list should stay lightweight
# and should not fail just because an optional runtime dependency (e.g. Pillow for picons)
# is not installed yet. Import the heavy modules only when the plugin is actually opened.

def get_main_class():
    from .dream_v6 import IPTVDreamMain
    return IPTVDreamMain


def get_export_functions():
    from .export_v2 import export_bouquets, add_to_bouquets_index
    return export_bouquets, add_to_bouquets_index

__all__ = [
    'get_main_class',
    'get_export_functions',
    'PLUGIN_NAME',
    'PLUGIN_VERSION',
    'PLUGIN_DESCRIPTION'
]
