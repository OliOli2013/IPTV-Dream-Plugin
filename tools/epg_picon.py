# -*- coding: utf-8 -*-
import os, urllib.request, urllib.error, shutil, re

PICONS_DIR = "/usr/share/enigma2/picon/"

def fetch_epg_for_playlist(playlist):
    """Dummy – możesz rozwinąć pobieranie EPG z XMLTV."""
    pass

def download_picon_url(url, title):
    """Pobiera logo i zapisuje jako picon."""
    os.makedirs(PICONS_DIR, exist_ok=True)
    safe = re.sub(r'
