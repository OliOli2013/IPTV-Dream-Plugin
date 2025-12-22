# -*- coding: utf-8 -*-
"""
IPTV Dream v6.2 - Package Initialization
"""

__version__ = "6.2"
__author__ = "IPTV Dream Team"
__license__ = "GPLv2"
__description__ = "Ultra-fast IPTV plugin for Enigma2 - REVOLUTION!"

# Package metadata
PLUGIN_NAME = "IPTV Dream v6.2"
PLUGIN_VERSION = "6.2"
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