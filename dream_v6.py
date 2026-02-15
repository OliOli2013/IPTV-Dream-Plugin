# -*- coding: utf-8 -*-
"""IPTV Dream v6.0

Cel tej wersji w repozytorium użytkownika:
- Zachować funkcjonalność i optymalizacje v6 (szybsze ładowanie, cache, multi-thread),
- Zachować okno główne v6 (większy rozmiar, panel informacji, progress bar),
- Jednocześnie wizualnie nawiązać do v5 (pasek przycisków, numeracja opcji, QR + opis).

Kod jest przygotowany tak, aby nie powodować Green Screen (defensywna obsługa wyjątków).
"""

from __future__ import absolute_import, print_function

import os
import re
import json
import time
import threading
import socket

import requests
from twisted.internet import reactor

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.Language import language
from Components.Sources.StaticText import StaticText

try:
    from enigma import eTimer, eDVBDB
except Exception:
    eTimer = None
    eDVBDB = None

# lokalne moduły
from .file_pick import M3UFilePick
from .export_v2 import export_bouquets
from .tools.lang import _
from .tools.net import http_get
from .tools.logger import get_logger, mask_sensitive
from .tools.bouquet_picker import BouquetPicker
from .tools.webif import start_web_server, stop_web_server
from .tools.updater import check_update, do_update
from .tools.epg_picon import install_epg_sources
from .tools.favorites import FavoritesManager
from .tools.statistics import StatisticsManager
from .tools.history import HistoryManager
from .tools.mac_portal import load_mac_json, save_mac_json, add_mac_portal
from .tools.mac_portal import parse_mac_playlist
from .tools.picon_manager_v6 import PiconManager
from .tools.epg_manager_v6 import EPGManager
from .tools.xtream_one_window_fixed import XtreamWindow  # alias w pliku

from .core.playlist_loader import PlaylistLoader

PLUGIN_VERSION = "6.4"
CONFIG_FILE = "/etc/enigma2/iptvdream_v6_config.json"
CACHE_DIR = "/tmp/iptvdream_v6_cache"

DL_TIMEOUT = 90
LOAD_TIMEOUT_DEFAULT_MS = 300000  # 5 minut (domyślnie)
MAC_VODSERIES_TIMEOUT_MS = 14400000  # 4 godziny (VOD/Seriale z MAC; duże biblioteki)
LOAD_TIMEOUT_MS = LOAD_TIMEOUT_DEFAULT_MS
WEBIF_PORT = 9999

EPG_URL_KEY = "epg_url"


def _safe_mkdir(path):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def run_in_thread(fn, cb, *args, **kwargs):
    """Uruchamia fn w wątku i zwraca wynik do cb(result, error)."""

    def _runner():
        try:
            res = fn(*args, **kwargs)
            reactor.callFromThread(cb, res, None)
        except Exception as e:
            reactor.callFromThread(cb, None, str(e))

    t = threading.Thread(target=_runner)
    t.daemon = True
    t.start()


def get_lan_ip():
    """Najczęściej poprawny IP LAN bez wywołań shell."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class IPTVDreamV6(Screen):
    skin = """
    <screen name="IPTVDreamV6" position="center,center" size="1200,800" title="IPTV Dream v6.4">
        <!-- TŁO (styl v6, nawiązanie kolorystyką do v5) -->
        <eLabel position="0,0" size="1200,800" backgroundColor="#0f0f0f" zPosition="-5" />

        <!-- NAGŁÓWEK -->
        <eLabel position="20,18" size="1160,70" backgroundColor="#1a1a1a" cornerRadius="14" zPosition="-4" />
        <eLabel position="20,18" size="1160,4" backgroundColor="#00c800" zPosition="-3" />
        <widget name="title_label" position="40,30" size="1120,44" font="Regular;34" halign="center" valign="center" foregroundColor="#00ff88" transparent="1" />
        <widget name="footer" position="40,74" size="1120,18" font="Regular;16" halign="center" valign="center" foregroundColor="#9a9a9a" transparent="1" />

        <!-- PASEK STATUSU -->
        <eLabel position="20,95" size="1160,40" backgroundColor="#222222" cornerRadius="10" zPosition="-4" />
        <widget name="status_bar" position="40,102" size="1120,28" font="Regular;22" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />

        <!-- PANEL MENU (lewa strona) -->
        <eLabel position="20,150" size="600,430" backgroundColor="#171717" cornerRadius="14" zPosition="-4" />
        <widget name="menu_list" position="35,165" size="570,400" font="Regular;26" itemHeight="44" scrollbarMode="showOnDemand" enableWrapAround="1" transparent="1"  foregroundColor="#ffffff" foregroundColorSelected="#00ff88" backgroundColorSelected="#303030" />

        <!-- PANEL INFORMACYJNY (prawa strona) -->
        <eLabel position="640,150" size="540,430" backgroundColor="#1d1d1d" cornerRadius="14" zPosition="-4" />
        <widget name="info_title" position="660,165" size="500,34" font="Regular;24" halign="center" foregroundColor="#ffcc00" transparent="1" />
        <widget name="info_text" position="660,205" size="500,360" font="Regular;20" halign="left" valign="top" foregroundColor="#e6e6e6" transparent="1" />

        <!-- QR + opis (jak v5, ale dopasowane do v6) -->
        <eLabel position="20,595" size="600,140" backgroundColor="#141414" cornerRadius="14" zPosition="-4" />
        <widget name="qr" position="35,610" size="110,110" alphatest="on" />
        <widget name="support" position="155,608" size="450,120" font="Regular;20" foregroundColor="#00ff00" valign="top" transparent="1" />

        <!-- PRAWY DOLNY PANEL PODPOWIEDZI -->
        <eLabel position="640,595" size="540,140" backgroundColor="#141414" cornerRadius="14" zPosition="-4" />
        <widget name="hint" position="660,610" size="500,110" font="Regular;20" foregroundColor="#bdbdbd" valign="top" transparent="1" />

        <!-- PROGRESS BAR (ukryty domyślnie) -->
        <widget name="progress_bar" position="20,742" size="1160,16" borderWidth="2" borderColor="#00c800" backgroundColor="#303030" zPosition="2" />
        <widget name="progress_text" position="20,720" size="1160,20" font="Regular;18" halign="center" foregroundColor="#00c800" transparent="1" zPosition="3" />

        <!-- PRZYCISKI KOLOROWE (styl v5, nowoczesne zaokrąglenie) -->
        <eLabel position="20,765" size="280,35" backgroundColor="#9f1313" cornerRadius="10" zPosition="1" />
        <eLabel position="320,765" size="280,35" backgroundColor="#1f771f" cornerRadius="10" zPosition="1" />
        <eLabel position="620,765" size="280,35" backgroundColor="#b59a00" cornerRadius="10" zPosition="1" />
        <eLabel position="920,765" size="260,35" backgroundColor="#0040a0" cornerRadius="10" zPosition="1" />

        <widget name="key_red" position="20,765" size="280,35" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" zPosition="2" />
        <widget name="key_green" position="320,765" size="280,35" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" zPosition="2" />
        <widget name="key_yellow" position="620,765" size="280,35" font="Regular;20" halign="center" valign="center" foregroundColor="#000000" transparent="1" zPosition="2" />
        <widget name="key_blue" position="920,765" size="260,35" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" zPosition="2" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        # Initial language is taken from the system. It may be overridden by plugin config later.
        self.lang = (language.getLanguage() or "pl")[:2].lower()
        if self.lang not in ("pl", "en"):
            self.lang = "pl"

        # UI
        self["title_label"] = Label(_("title", self.lang))
        self["menu_list"] = MenuList([])
        self["info_title"] = Label("")
        self["info_text"] = Label("")
        self["status_bar"] = Label("")
        self["progress_bar"] = ProgressBar()
        self["progress_text"] = Label("")
        self["key_red"] = Label(_("exit", self.lang))
        self["key_green"] = Label(_("check_upd", self.lang))
        self["key_yellow"] = Label(_("epg_install", self.lang))
        self["key_blue"] = Label(_("export", self.lang))

        self["qr"] = Pixmap()
        if self.lang == "pl":
            support_txt = "\c00ffffffPodoba Ci się wtyczka?\n\c0000ff00Wesprzyj twórcę i rozwój.\n\c00ffcc00Dziękuję!\c00ffffff"
        else:
            support_txt = "\c00ffffffDo you like the plugin?\n\c0000ff00Support the creator & development.\n\c00ffcc00Thank you!\c00ffffff"
        self["support"] = Label(support_txt)


        if self.lang == "pl":
            self["hint"] = Label("Naciśnij 1-9 lub OK, aby wybrać opcję.\nWebIF: port 9999 • Cache i streaming aktywne.")
        else:
            self["hint"] = Label("Press 1-9 or OK to select an option.\nWebIF: port 9999 • Cache & streaming enabled.")
        try:
            foot_date = time.strftime("%Y-%m-%d")
        except Exception:
            foot_date = ""
        self["footer"] = Label(_("foot", self.lang).format(date=foot_date) + " v%s" % PLUGIN_VERSION)


        # --- Inicjalizacja logiki v6 (konfiguracja, akcje, timery) ---
        _safe_mkdir(CACHE_DIR)
        self.cfg = {}
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.cfg = json.load(f) or {}
        except Exception:
            self.cfg = {}

        # ustawienia domyślne
        self.cfg.setdefault('language', self.lang)
        self.cfg.setdefault('service_type', 4097)
        self.cfg.setdefault('webif_enabled', False)
        self.cfg.setdefault('last_url', 'http://')
        self.cfg.setdefault('last_source', None)
        self.cfg.setdefault('debug', False)
        self.cfg.setdefault('log_file', '/tmp/iptvdream.log')
        self.cfg.setdefault('ssl_verify', False)
        self.cfg.setdefault('net_timeout_connect', 7)
        self.cfg.setdefault('net_timeout_read', 30)
        self.cfg.setdefault('net_retries', 2)
        self.cfg.setdefault('net_backoff', 0.8)

        # Prefer language from plugin config if present (normalize)
        try:
            cfg_lang = str(self.cfg.get('language', self.lang)).strip().lower()
            if cfg_lang in ("pl", "en"):
                self.lang = cfg_lang
        except Exception:
            pass

        # Apply language-dependent static UI texts now that config is loaded
        self._apply_language_to_static_ui()

        # logger
        self.log = get_logger('IPTVDream', log_file=self.cfg.get('log_file', '/tmp/iptvdream.log'), debug=bool(self.cfg.get('debug', False)))

        # typ serwisu (4097/5002)
        try:
            self.service_type = int(self.cfg.get('service_type', 4097))
        except Exception:
            self.service_type = 4097

        self.webif_enabled = bool(self.cfg.get('webif_enabled', False))
        self.last_source = self.cfg.get('last_source')
        self.current_playlist = None
        self.playlist_name = ''
        self.menu_context = 'main'

        # menadżery v6
        self.loader = PlaylistLoader()
        self.favorites = FavoritesManager()
        self.statistics = StatisticsManager()
        self.history = HistoryManager()
        self.picons = PiconManager()
        self.epg_manager = EPGManager()

        # timeout watchdog (wydłużony w LOAD_TIMEOUT_MS)
        self.loading_timer = None
        if eTimer:
            try:
                self.loading_timer = eTimer()
                try:
                    self.loading_timer.callback.append(self.onLoadingTimeout)
                except Exception:
                    self.loading_timer_conn = self.loading_timer.timeout.connect(self.onLoadingTimeout)
            except Exception:
                self.loading_timer = None

        self.is_loading = False
        self.load_start_time = 0

        # mapowanie klawiszy jak w v5 (kolory) + numeracja 1-9
        self['actions'] = ActionMap(
            ['ColorActions', 'OkCancelActions', 'NumberActions'],
            {
                'red': self.close,
                'green': self.checkUpdates,
                'yellow': self.installEpgSources,
                'blue': self.exportBouquets,
                'ok': self.onMenuSelect,
                'cancel': self.onCancel,
                '1': lambda: self.onNumberKey(1),
                '2': lambda: self.onNumberKey(2),
                '3': lambda: self.onNumberKey(3),
                '4': lambda: self.onNumberKey(4),
                '5': lambda: self.onNumberKey(5),
                '6': lambda: self.onNumberKey(6),
                '7': lambda: self.onNumberKey(7),
                '8': lambda: self.onNumberKey(8),
                '9': lambda: self.onNumberKey(9),
            },
            -1,
        )

        # inicjalizacja UI po zbudowaniu ekranu (pixmap, menu)
        self.onLayoutFinish.append(self._init_ui)

    def _apply_language_to_static_ui(self):
        """Refresh static UI labels that depend on language."""
        try:
            self["title_label"].setText(_("title", self.lang))
            self["key_red"].setText(_("exit", self.lang))
            self["key_green"].setText(_("check_upd", self.lang))
            self["key_yellow"].setText(_("epg_install", self.lang))
            self["key_blue"].setText(_("export", self.lang))
        except Exception:
            pass

        # Support text block
        try:
            if self.lang == "pl":
                support_txt = "\\c00ffffffPodoba Ci się wtyczka?\n\\c0000ff00Wesprzyj twórcę i rozwój.\n\\c00ffcc00Dziękuję!\\c00ffffff"
            else:
                support_txt = "\\c00ffffffDo you like the plugin?\n\\c0000ff00Support the creator & development.\n\\c00ffcc00Thank you!\\c00ffffff"
            self["support"].setText(support_txt)
        except Exception:
            pass

        # Hint + footer
        try:
            if self.lang == "pl":
                self["hint"].setText("Naciśnij 1-9 lub OK, aby wybrać opcję.\nWebIF: port 9999 • Cache i streaming aktywne.")
            else:
                self["hint"].setText("Press 1-9 or OK to select an option.\nWebIF: port 9999 • Cache & streaming enabled.")
        except Exception:
            pass
        try:
            foot_date = time.strftime("%Y-%m-%d")
        except Exception:
            foot_date = ""
        try:
            self["footer"].setText(_("foot", self.lang).format(date=foot_date) + " v%s" % PLUGIN_VERSION)
        except Exception:
            pass

    # ---------- config ----------

    def _save_cfg(self):
        """Bezpieczny zapis konfiguracji.

        Brak tej metody powodował błędy typu:
        - WebIF error: 'IPTVDreamV6' object has no attribute '_save_cfg'
        - Green Screen po zatwierdzeniu URL M3U (zapisywanie last_url/last_source)
        """
        try:
            # Uzupełnij wartości runtime
            self.cfg["language"] = self.lang
            self.cfg["service_type"] = int(getattr(self, "service_type", 4097))
            self.cfg["webif_enabled"] = bool(getattr(self, "webif_enabled", False))
            if getattr(self, "last_source", None) is not None:
                self.cfg["last_source"] = self.last_source

            # Zapis atomowy
            tmp = CONFIG_FILE + ".tmp"
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self.cfg, f, indent=2, ensure_ascii=False)
                os.replace(tmp, CONFIG_FILE)
            finally:
                try:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                except Exception:
                    pass
        except Exception:
            # Nie wywalaj GUI przy problemie zapisu
            pass


    def updateInfoPanel(self, title, text):
        self["info_title"].setText(title)
        self["info_text"].setText(text)

    def _init_ui(self):
        """Uzupełnia UI po utworzeniu ekranu (menu + QR) i uruchamia WebIF jeśli włączone."""
        # QR
        try:
            from Tools.LoadPixmap import LoadPixmap
            qr_path = os.path.join(os.path.dirname(__file__), "pic", "qrcode.png")
            if os.path.exists(qr_path):
                p = LoadPixmap(path=qr_path)
                if p is not None and getattr(self["qr"], "instance", None):
                    self["qr"].instance.setPixmap(p)
                    self["qr"].show()
        except Exception:
            pass

        # Start WebIF jeśli włączone w config
        if getattr(self, "webif_enabled", False):
            try:
                start_web_server(WEBIF_PORT, self.onWebIfData)
            except Exception:
                self.webif_enabled = False

        # stan początkowy
        try:
            self["progress_bar"].hide()
            self["progress_text"].hide()
        except Exception:
            pass

        self.updateInfoPanel(_("Witamy", self.lang), _("welcome_body", self.lang) % PLUGIN_VERSION)
        self.showMainMenu()

    def onCancel(self):
        """EXIT: powrót albo zamknięcie."""
        try:
            if getattr(self, "is_loading", False):
                self.stopLoading()
                self["status_bar"].setText(_("Przerwano.", self.lang))
                return
        except Exception:
            pass

        if getattr(self, "menu_context", "main") != "main":
            return self.showMainMenu()
        self.close()

    def onNumberKey(self, n):
        """Wybór pozycji klawiszami 1-9 (jak w v5)."""
        try:
            lst = self["menu_list"].list
        except Exception:
            lst = None
        if not lst:
            return
        idx = int(n) - 1
        if idx < 0 or idx >= len(lst):
            return
        try:
            self["menu_list"].moveToIndex(idx)
        except Exception:
            pass
        try:
            action = lst[idx][1] if len(lst[idx]) > 1 else None
        except Exception:
            action = None
        self._dispatch(action)

    def installEpgSources(self):
        """ŻÓŁTY: instalacja źródeł EPG (v5-style)."""
        return self.forceInstallEPG()

    def exportBouquets(self):
        """NIEBIESKI: eksport do bukietu (v5-style)."""
        return self.exportBouquet()

    def showMainMenu(self):
        ip = get_lan_ip()
        webif_txt = "ON" if self.webif_enabled else "OFF"
        webif_url = "http://%s:%d" % (ip, WEBIF_PORT)

        # Kolory numerów (jak w referencyjnych screenach v5):
        # 1-4 zielony, 5 szary, 6 fiolet, 7 pomarańcz, 8 niebieski, 9 czerwony.
        num_reset = "\c00ffffff"
        num_colors = {
            1: "\c0000ff00", 2: "\c0000ff00", 3: "\c0000ff00", 4: "\c0000ff00",
            5: "\c00a0a0a0", 6: "\c00b000ff", 7: "\c00ff7a00", 8: "\c000080ff", 9: "\c00ff0000",
        }
        def N(i):
            return "%s%d%s" % (num_colors.get(i, "\c00ffffff"), i, num_reset)

        if self.lang == "pl":
            lbl1 = "🌐 M3U z URL"
            lbl2 = "📁 M3U z pliku"
            lbl3 = "⚡ Xtream Codes"
            lbl4 = "🔑 MAC Portal"
            lbl5 = "⭐ Ulubione"
            lbl6 = "⚙️ Zarządzanie"
            lbl7 = "📊 Statystyki"
            lbl8 = "🌐 Web Interfejs (%s)  %s" % (webif_txt, webif_url)
            lbl9 = "🔄 Aktualizacje"
        else:
            lbl1 = "🌐 M3U URL"
            lbl2 = "📁 M3U File"
            lbl3 = "⚡ Xtream Codes"
            lbl4 = "🔑 MAC Portal"
            lbl5 = "⭐ Favorites"
            lbl6 = "⚙️ Management"
            lbl7 = "📊 Statistics"
            lbl8 = "🌐 Web Interface (%s)  %s" % (webif_txt, webif_url)
            lbl9 = "🔄 Updates"

        items = [
            ("%s  %s" % (N(1), lbl1), "m3u_url"),
            ("%s  %s" % (N(2), lbl2), "m3u_file"),
            ("%s  %s" % (N(3), lbl3), "xtream"),
            ("%s  %s" % (N(4), lbl4), "mac"),
            ("%s  %s" % (N(5), lbl5), "favorites"),
            ("%s  %s" % (N(6), lbl6), "manage"),
            ("%s  %s" % (N(7), lbl7), "stats"),
            ("%s  %s" % (N(8), lbl8), "webif"),
            ("%s  %s" % (N(9), lbl9), "update"),
        ]
        self.menu_context = "main"
        self["menu_list"].setList(items)

        if self.lang == "pl":
            self["status_bar"].setText("Naciśnij 1-9 lub OK, aby wybrać opcję")
            self["hint"].setText("1-4: źródło • 5: ulubione • 6: zarządzanie\n7: statystyki • 8: WebIF (9999) • 9: aktualizacje")
        else:
            self["status_bar"].setText("Press 1-9 or OK to select an option")
            self["hint"].setText("1-4: source • 5: favorites • 6: management\n7: statistics • 8: WebIF (9999) • 9: updates")

    def showManagementMenu(self):
        self.menu_context = "manage"

        dbg_on = bool(self.cfg.get('debug', False))
        if self.lang == "pl":
            st_title = "Zarządzanie"
            back_lbl = "⬅️ Powrót"
            cache_lbl = "🧹 Wyczyść cache (M3U)"
            hist_lbl = "🗑️ Wyczyść historię"
            hint_txt = "OK: wybór • EXIT: powrót/wyjście\nCache: włączony • Streaming: tak"
            lang_lbl = "⚙️ Język: %s" % ("PL" if self.lang == "pl" else "EN")
            stype_lbl = "🎬 Typ serwisu: %d" % self.service_type
            epg_lbl = "📺 EPG URL (custom)"
            dbg_lbl = "🪲 Debug: %s" % ("ON" if dbg_on else "OFF")
            log_lbl = "📄 Pokaż log (/tmp/iptvdream.log)"
            logc_lbl = "🧹 Wyczyść log"
        else:
            st_title = "Management"
            back_lbl = "⬅️ Back"
            cache_lbl = "🧹 Clear cache (M3U)"
            hist_lbl = "🗑️ Clear history"
            hint_txt = "OK: select • EXIT: back/close\nCache: enabled • Streaming: yes"
            lang_lbl = "⚙️ Language: %s" % ("PL" if self.lang == "pl" else "EN")
            stype_lbl = "🎬 Service type: %d" % self.service_type
            epg_lbl = "📺 EPG URL (custom)"
            dbg_lbl = "🪲 Debug: %s" % ("ON" if dbg_on else "OFF")
            log_lbl = "📄 Show log (/tmp/iptvdream.log)"
            logc_lbl = "🧹 Clear log"

        items = [
            (lang_lbl, "lang"),
            (stype_lbl, "stype"),
            (epg_lbl, "epgurl"),
            (dbg_lbl, "debug_toggle"),
            (log_lbl, "show_log"),
            (logc_lbl, "clear_log"),
            (cache_lbl, "clear_cache"),
            (hist_lbl, "clear_history"),
            (back_lbl, "back_main"),
        ]
        self["menu_list"].setList(items)
        self["status_bar"].setText(st_title)
        self["hint"].setText(hint_txt)

    def showPlaylistMenu(self):
        if not self.current_playlist:
            self.showMainMenu()
            return
        self.menu_context = "playlist"
        items = [
            (_("📊 Podgląd playlisty", self.lang), "preview"),
            (_("📁 Grupy", self.lang), "groups"),
            (_("⭐ Dodaj całość do ulubionych", self.lang), "fav_add_all"),
            (_("🎨 Pobierz pikony", self.lang), "picons"),
            (_("📺 Instaluj EPG + przypisz", self.lang), "epg_map"),
            (_("🔄 Odśwież (ostatnie źródło)", self.lang), "refresh"),
            (_("⬅️ Powrót", self.lang), "back_main"),
        ]
        self["menu_list"].setList(items)
        self["status_bar"].setText(_("Playlista: %s", self.lang) % (self.playlist_name or ""))
        self["hint"].setText(_("ZIELONY: aktualizacje • ŻÓŁTY: źródła EPG • NIEBIESKI: eksport\nOK: wybór • 8: WebIF 9999", self.lang))

    def showFavorites(self):
        try:
            groups = self.favorites.get_favorite_groups()
        except Exception:
            groups = []

        if not groups:
            self.session.open(MessageBox, _("Brak ulubionych kanałów!", self.lang), MessageBox.TYPE_INFO)
            return

        self.menu_context = "favorites_groups"
        items = []
        for g in groups:
            try:
                cnt = len(self.favorites.get_favorites_in_group(g))
            except Exception:
                cnt = 0
            items.append(("⭐ %s (%d)" % (g, cnt), ("fav_group", g)))
        items.append((_("⬅️ Powrót", self.lang), "back_main"))
        self["menu_list"].setList(items)
        self["status_bar"].setText(_("Ulubione", self.lang))

    def showFavoritesGroup(self, group_name):
        chans = self.favorites.get_favorites_in_group(group_name)
        if not chans:
            self.session.open(MessageBox, _("Brak kanałów w tej grupie.", self.lang), MessageBox.TYPE_INFO)
            return

        self.menu_context = "favorites_list"
        items = []
        for ch in chans[:300]:
            title = ch.get("title", "Bez nazwy" if self.lang == "pl" else "No name")
            items.append(("• %s" % title, ("fav_item", ch)))
        items.append((_("⬅️ Powrót", self.lang), "back_fav_groups"))
        self["menu_list"].setList(items)
        self["status_bar"].setText(_("Ulubione: %s", self.lang) % group_name)

    # ---------- nawigacja / dispatch ----------

    def onMenuSelect(self):
        try:
            cur = self["menu_list"].getCurrent()
        except Exception:
            cur = None
        if not cur:
            return

        action = cur[1] if len(cur) > 1 else None
        self._dispatch(action)

    def _dispatch(self, action):
        if not action:
            return

        # --- MAC Portal menu (v6) ---
        # W menu MAC w liście są akcje typu: "mac_add", "mac_delete" oraz tuple ("mac_pick", portal)
        # Bez tej obsługi działał tylko "Powrót".
        if getattr(self, "menu_context", "") == "mac_menu":
            if action == "mac_add":
                return self.addMacPortal()
            if action == "mac_delete":
                return self.deleteMacPortal()
            if action == "back_main":
                return self.showMainMenu()
            if isinstance(action, tuple) and len(action) >= 2 and action[0] == "mac_pick":
                p = action[1] or {}
                host = (p.get("host") or "").strip()
                mac = (p.get("mac") or "").strip()
                if host and mac:
                    return self.onMacPicked(p)
                return

        # tuple actions
        if isinstance(action, tuple):
            if action[0] == "fav_group":
                return self.showFavoritesGroup(action[1])
            if action[0] == "fav_item":
                ch = action[1]
                self.updateInfoPanel(_("Ulubione", self.lang), _("Kanał: %s\nURL: %s", self.lang) % (ch.get("title", ""), ch.get("url", "")))
                return

        # string actions
        if action == "m3u_url":
            return self.openUrl()
        if action == "m3u_file":
            return self.openFile()
        if action == "xtream":
            return self.openXtream()
        if action == "mac":
            return self.openMacMenu()
        if action == "favorites":
            return self.showFavorites()
        if action == "manage":
            return self.showManagementMenu()
        if action == "stats":
            return self.showStats()
        if action == "webif":
            return self.toggleWebIf()
        if action == "update":
            return self.checkUpdates()

        if action == "lang":
            self.lang = "en" if self.lang == "pl" else "pl"
            self.cfg["language"] = self.lang
            self._save_cfg()
            # Refresh language-dependent static UI and info panel immediately.
            self._apply_language_to_static_ui()
            try:
                self.updateInfoPanel(_("Witamy", self.lang), _("welcome_body", self.lang) % PLUGIN_VERSION)
            except Exception:
                pass
            self.session.open(MessageBox, (_("lang_changed", self.lang) + " %s") % self.lang.upper(), MessageBox.TYPE_INFO, timeout=2)
            return self.showManagementMenu()

        if action == "stype":
            self.service_type = 5002 if self.service_type == 4097 else 4097
            self.cfg["service_type"] = self.service_type
            self._save_cfg()
            self.session.open(MessageBox, (_("Typ serwisu: %d", self.lang) % self.service_type), MessageBox.TYPE_INFO, timeout=2)
            return self.showManagementMenu()

        if action == "epgurl":
            cur = self.cfg.get(EPG_URL_KEY, "http://")
            title = "Wklej URL EPG:" if self.lang == "pl" else "Paste EPG URL:"
            self.session.openWithCallback(self.onEpgUrlReady, VirtualKeyBoard, title=title, text=cur)
            return
        if action == "debug_toggle":
            self.cfg['debug'] = not bool(self.cfg.get('debug', False))
            self._save_cfg()
            # refresh logger
            try:
                self.log = get_logger('IPTVDream', log_file=self.cfg.get('log_file', '/tmp/iptvdream.log'), debug=bool(self.cfg.get('debug', False)))
            except Exception:
                pass
            msg = ('Debug: ON' if self.cfg['debug'] else 'Debug: OFF') if self.lang == 'en' else ('Debug: WŁ.' if self.cfg['debug'] else 'Debug: WYŁ.')
            self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, timeout=2)
            return self.showManagementMenu()

        if action == "show_log":
            try:
                path = self.cfg.get('log_file', '/tmp/iptvdream.log')
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        data = f.read()
                    # limit display
                    if len(data) > 12000:
                        data = data[-12000:]
                    title = 'Log (last lines)' if self.lang == 'en' else 'Log (ostatnie linie)'
                    self.session.open(MessageBox, ('%s\n\n%s' % (title, (data or '(empty)'))), MessageBox.TYPE_INFO)
                else:
                    self.session.open(MessageBox, 'Log not found' if self.lang == 'en' else 'Brak pliku logu', MessageBox.TYPE_INFO, timeout=3)
            except Exception as e:
                self.session.open(MessageBox, 'Log error: %s' % e, MessageBox.TYPE_ERROR)
            return

        if action == "clear_log":
            try:
                path = self.cfg.get('log_file', '/tmp/iptvdream.log')
                if os.path.exists(path):
                    open(path, 'w').close()
                self.session.open(MessageBox, 'Log cleared' if self.lang == 'en' else 'Log wyczyszczony', MessageBox.TYPE_INFO, timeout=2)
            except Exception as e:
                self.session.open(MessageBox, 'Log error: %s' % e, MessageBox.TYPE_ERROR)
            return self.showManagementMenu()

        if action == "clear_cache":
            return self.clearCache()
        if action == "clear_history":
            return self.clearHistory()
        if action == "back_main":
            return self.showMainMenu()
        if action == "back_fav_groups":
            return self.showFavorites()

        # playlist menu
        if action == "preview":
            return self.showPlaylistPreview()
        if action == "groups":
            return self.showPlaylistGroups()
        if action == "fav_add_all":
            return self.addPlaylistToFavorites()
        if action == "picons":
            return self.downloadPiconsForPlaylist()
        if action == "epg_map":
            return self.installEpgAndMap()
        if action == "refresh":
            return self.refreshLastSource()

    # ---------- operacje ładowania ----------

    def startLoading(self, message, timeout_ms=None):
        self.is_loading = True
        self.load_start_time = time.time()
        self["status_bar"].setText(message)
        self["progress_bar"].setValue(0)
        self["progress_text"].setText("0%")
        self["progress_bar"].show()
        self["progress_text"].show()
        if self.loading_timer:
            try:
                tmo = int(timeout_ms) if timeout_ms is not None else int(LOAD_TIMEOUT_MS)
                self.loading_timer.start(tmo)
            except Exception:
                pass

    def stopLoading(self):
        self.is_loading = False
        if self.loading_timer:
            try:
                self.loading_timer.stop()
            except Exception:
                pass
        self["progress_bar"].hide()
        self["progress_text"].hide()

    def updateProgress(self, value, text=""):
        try:
            self["progress_bar"].setValue(int(value))
            if text:
                self["progress_text"].setText("%d%% - %s" % (int(value), text))
            else:
                self["progress_text"].setText("%d%%" % int(value))
        except Exception:
            pass

    def onLoadingTimeout(self):
        if self.is_loading:
            self.stopLoading()
            self["status_bar"].setText(_("Przekroczono czas ładowania (timeout).", self.lang))

    # ---------- M3U URL ----------

    def openUrl(self):
        last_url = self.cfg.get("last_url", "http://")
        self.session.openWithCallback(self.onUrlReady, VirtualKeyBoard, title=_("Wprowadź URL playlisty M3U:", self.lang), text=last_url)

    def onUrlReady(self, url):
        if not url or not url.startswith(("http://", "https://")):
            return

        self.cfg["last_url"] = url
        self.last_source = {"type": "m3u_url", "value": url}
        self.cfg["last_source"] = self.last_source
        self._save_cfg()

        self.startLoading(_("Pobieranie playlisty (URL) ...", self.lang))

        def _load():
            # PlaylistLoader ma cache i parsowanie
            content = self.loader.load_m3u_url(url, progress_callback=self.updateProgress)
            playlist = self.loader.parse_m3u_content(content, progress_callback=self.updateProgress)
            return playlist

        run_in_thread(_load, lambda res, err: self.onPlaylistLoaded(res, "M3U-URL", err))

    # ---------- M3U file ----------

    def openFile(self):
        self.session.openWithCallback(self.onFileReady, M3UFilePick, start_dir="/tmp/")

    def onFileReady(self, path):
        if not path:
            return
        self.last_source = {"type": "m3u_file", "value": path}
        self.cfg["last_source"] = self.last_source
        self._save_cfg()

        self.startLoading(_("Wczytywanie pliku M3U ...", self.lang))

        def _load():
            content = self.loader.load_m3u_file(path)
            playlist = self.loader.parse_m3u_content(content, progress_callback=self.updateProgress)
            return playlist

        name = os.path.splitext(os.path.basename(path))[0]
        run_in_thread(_load, lambda res, err: self.onPlaylistLoaded(res, name, err))

    # ---------- Xtream ----------

    def openXtream(self):
        self.session.openWithCallback(self.onXtreamOne, XtreamWindow)

    def onXtreamOne(self, data):
        if not data:
            return
        self.xtream_data = data
        options = [
            ("LIVE", "live"),
            ("VOD", "vod"),
            ("ALL", "all"),
            ("ADULT", "adult"),
        ]
        self.session.openWithCallback(self.onXtreamTypeSelected, ChoiceBox, title=_("Wybierz typ treści", self.lang), list=options)

    def onXtreamTypeSelected(self, choice):
        if not choice:
            return
        content_type = choice[1]
        host, user, pwd = self.xtream_data
        self.startLoading(_("Pobieranie Xtream ...", self.lang))

        def _dl():
            base = host if host.startswith("http") else "http://%s" % host
            url = "%s/get.php?username=%s&password=%s&type=m3u_plus&output=ts" % (base, user, pwd)
            r = http_get(url, timeout=(int(self.cfg.get('net_timeout_connect',7)), int(self.cfg.get('net_timeout_read',30))), retries=int(self.cfg.get('net_retries',2)), backoff=float(self.cfg.get('net_backoff',0.8)), verify=bool(self.cfg.get('ssl_verify', False)), debug=bool(self.cfg.get('debug', False)), log_file=self.cfg.get('log_file','/tmp/iptvdream.log'))
            return r.content

        def _done(data, err):
            if err:
                self.onPlaylistLoaded(None, None, err)
                return
            playlist = parse_m3u_bytes_improved(data, content_filter=content_type)
            suffix = "LIVE" if content_type == "live" else "VOD" if content_type == "vod" else "ADULT" if content_type == "adult" else "ALL"
            self.last_source = {"type": "xtream", "value": {"host": host, "user": user, "pass": pwd, "filter": content_type}}
            self.cfg["last_source"] = self.last_source
            self._save_cfg()
            self.onPlaylistLoaded(playlist, "Xtream-%s-%s" % (user, suffix), None)

        run_in_thread(_dl, _done)

    # ---------- MAC Portal ----------

    def openMacMenu(self):
        portals = load_mac_json() or []
        items = [(_("➕ Dodaj nowy portal", self.lang), "mac_add")]
        for p in portals:
            host = p.get("host", "")
            mac = p.get("mac", "")
            items.append(("🔑 %s | %s" % (host, mac), ("mac_pick", p)))
        items.append((_("🗑️ Usuń portal", self.lang), "mac_delete"))
        items.append((_("⬅️ Powrót", self.lang), "back_main"))
        self.menu_context = "mac_menu"
        self["menu_list"].setList(items)
        self["status_bar"].setText(_("MAC Portal", self.lang))

    def _mac_menu_dispatch(self, action):
        # helper unused: kept for readability
        return

    def addMacPortal(self):
        self.session.openWithCallback(
            self.onMacJson,
            VirtualKeyBoard,
            title=("Wklej JSON:" if self.lang == "pl" else "Paste JSON:"),
            text='{"host":"...","mac":"..."}'
        )

    def onMacJson(self, txt):
        if not txt:
            return
        try:
            data = json.loads(txt)
            host = (data.get("host") or "").strip()
            mac = (data.get("mac") or "").strip()
            if not host or not mac:
                self.session.open(MessageBox, _("Brak host/mac w JSON.", self.lang), MessageBox.TYPE_ERROR)
                return
            add_mac_portal(host, mac)
            self.session.open(MessageBox, _("Dodano portal MAC.", self.lang), MessageBox.TYPE_INFO, timeout=3)
            self.openMacMenu()
        except Exception as e:
            self.session.open(MessageBox, "JSON Error: %s" % e, MessageBox.TYPE_ERROR)

    def onMacPicked(self, portal):
        """After picking a saved MAC portal, ask for content type."""
        if not portal:
            return
        host = (portal.get('host') or '').strip()
        mac = (portal.get('mac') or '').strip()
        pname = (portal.get('name') or '').strip()
        if not host or not mac:
            return
        self._mac_pick_ctx = (host, mac, pname)
        opts = [("LIVE", 'live'), ("VOD", 'vod'), ("SERIALE", 'series')]
        self.session.openWithCallback(self.onMacTypeSelected, ChoiceBox, title=_("Wybierz typ treści", self.lang), list=opts)

    def onMacTypeSelected(self, choice):
        if not choice:
            return
        ctype = choice[1]
        try:
            host, mac, pname = getattr(self, '_mac_pick_ctx', ('', '', ''))
        except Exception:
            host, mac, pname = ('', '', '')
        if host and mac:
            return self.startMacDownload(host, mac, content_type=ctype, portal_name=pname)

    def startMacDownload(self, host, mac, content_type='live', portal_name=None):
        tmo = MAC_VODSERIES_TIMEOUT_MS if content_type in ("vod","series") else LOAD_TIMEOUT_MS
        msg = _("Pobieranie z MAC Portal ...", self.lang)
        if content_type in ("vod","series"):
            msg = (_("Pobieranie z MAC Portal ...", self.lang) + ("\n(duża biblioteka może wczytywać się długo)" if self.lang=="pl" else "\n(large libraries may take a long time)"))
        self.startLoading(msg, timeout_ms=tmo)

        def _load():
            # tools/mac_portal.py w repozytorium przyjmuje (host, mac) bez progress_callback.
            # Progress pokazujemy na poziomie GUI (start/stop + status), a parsowanie nie blokuje GUI.
            playlist = parse_mac_playlist(host, mac, content_type=content_type)
            return playlist

        self.last_source = {"type": "mac", "value": {"host": host, "mac": mac, "filter": content_type}}
        self.cfg["last_source"] = self.last_source
        self._save_cfg()
        # unique playlist name per portal + content type
        def _mk_id():
            try:
                dom = host.split('://', 1)[-1].split('/', 1)[0]
            except Exception:
                dom = host
            mac_id = mac.replace(':', '').replace('-', '')
            mac_id = mac_id[-6:] if len(mac_id) >= 6 else mac_id
            ident = (portal_name or dom).strip() or dom
            ident = ident.replace('/', '_').replace(' ', '_')
            return '%s_%s' % (ident, mac_id) if mac_id else ident
        suffix = 'LIVE' if content_type == 'live' else ('VOD' if content_type == 'vod' else 'SERIES')
        pl_name = 'MAC-%s-%s' % (_mk_id(), suffix)
        run_in_thread(_load, lambda res, err: self.onPlaylistLoaded(res, pl_name, err))

    def deleteMacPortal(self):
        portals = load_mac_json() or []
        if not portals:
            self.session.open(MessageBox, _("Brak zapisanych portali.", self.lang), MessageBox.TYPE_INFO)
            return
        items = []
        for idx, p in enumerate(portals):
            items.append((_("Usuń: %s | %s", self.lang) % (p.get("host", ""), p.get("mac", "")), idx))
        self.session.openWithCallback(self.onMacDeletePicked, ChoiceBox, title=_("Wybierz portal do usunięcia", self.lang), list=items)

    def onMacDeletePicked(self, choice):
        if not choice:
            return
        idx = choice[1]
        portals = load_mac_json() or []
        if 0 <= idx < len(portals):
            portals.pop(idx)
            save_mac_json(portals)
            self.session.open(MessageBox, _("Usunięto portal.", self.lang), MessageBox.TYPE_INFO, timeout=3)
        self.openMacMenu()

    # ---------- WebIF ----------

    def toggleWebIf(self):
        try:
            if self.webif_enabled:
                stop_web_server()
                self.webif_enabled = False
            else:
                start_web_server(WEBIF_PORT, self.onWebIfData)
                self.webif_enabled = True

            self.cfg["webif_enabled"] = self.webif_enabled
            self._save_cfg()
            self.showMainMenu()
        except Exception as e:
            self.session.open(MessageBox, "WebIF error: %s" % e, MessageBox.TYPE_ERROR)

    def onWebIfData(self, data):
        """Callback z WebIF (POST)."""
        try:
            typ = data.get("type")
            if typ == "m3u":
                url = data.get("url")
                if url:
                    reactor.callFromThread(self.onUrlReady, url)
            elif typ == "xtream":
                host = data.get("host")
                user = data.get("user")
                pwd = data.get("pass")
                if host and user:
                    self.xtream_data = (host, user, pwd)
                    reactor.callFromThread(self.onXtreamTypeSelected, ("ALL", "all"))
            elif typ == "mac":
                host = data.get("host")
                mac = data.get("mac")
                mode = (data.get('mode') or data.get('filter') or 'live')
                if mode not in ('live','vod','series'):
                    mode = 'live'
                if host and mac:
                    try:
                        add_mac_portal(host, mac)
                    except Exception:
                        pass
                    reactor.callFromThread(self.startMacDownload, host, mac, mode, None)
        except Exception as e:
            print("[IPTVDreamV6] WebIF data error:", e)

    # ---------- po załadowaniu playlisty ----------

    def onPlaylistLoaded(self, playlist, name, error):
        self.stopLoading()

        if error:
            self["status_bar"].setText(_("Błąd: %s", self.lang) % error)
            self.session.open(MessageBox, _("Błąd ładowania: %s", self.lang) % error, MessageBox.TYPE_ERROR)
            return

        if not playlist:
            self["status_bar"].setText(_("Pusta playlista!", self.lang))
            return

        load_time = time.time() - self.load_start_time if self.load_start_time else 0
        speed = (len(playlist) / load_time) if load_time > 0 else 0

        self.current_playlist = playlist
        self.playlist_name = name or "Playlist"

        self["status_bar"].setText(_("Załadowano %d kanałów w %.1fs (%.0f kan/s)", self.lang) % (len(playlist), load_time, speed))

        # statystyki / historia
        try:
            self.statistics.update_stats(len(playlist), load_time)
        except Exception:
            pass
        try:
            self.history.add_to_history({"title": self.playlist_name, "url": ""})
        except Exception:
            pass

        title = _("Załadowano", self.lang)
        if self.lang == "pl":
            body = "Playlista: %s\nKanałów: %d\nCzas: %.1fs\nWydajność: %.0f kan/s\n\nUżyj NIEBIESKIEGO: Eksport do bukietu" % (self.playlist_name, len(playlist), load_time, speed)
        else:
            body = "Playlist: %s\nChannels: %d\nTime: %.1fs\nSpeed: %.0f ch/s\n\nUse BLUE: Export bouquet" % (self.playlist_name, len(playlist), load_time, speed)
        self.updateInfoPanel(title, body)

        self.showPlaylistMenu()

    def showPlaylistPreview(self):
        if not self.current_playlist:
            return
        groups = {}
        for ch in self.current_playlist:
            grp = ch.get("group", "Inne" if self.lang == "pl" else "Other")
            groups.setdefault(grp, 0)
            groups[grp] += 1
        txt = ("Playlista: %s\nKanałów: %d\n\n" if self.lang == "pl" else "Playlist: %s\nChannels: %d\n\n") % (self.playlist_name, len(self.current_playlist))
        for g, c in sorted(groups.items(), key=lambda x: x[0].lower()):
            txt += "• %s: %d\n" % (g, c)
        self.updateInfoPanel(_("Podgląd", self.lang), txt)

    def showPlaylistGroups(self):
        if not self.current_playlist:
            return
        groups = {}
        for ch in self.current_playlist:
            grp = ch.get("group", "Inne" if self.lang == "pl" else "Other")
            groups.setdefault(grp, []).append(ch)

        self.menu_context = "playlist_groups"
        items = [("📁 %s (%d)" % (g, len(chs)), ("pl_group", g)) for g, chs in sorted(groups.items(), key=lambda x: x[0].lower())]
        items.append((_("⬅️ Powrót", self.lang), "back_playlist"))
        self._playlist_groups_cache = groups
        self["menu_list"].setList(items)
        self["status_bar"].setText(_("Grupy", self.lang))

    def showPlaylistGroupItems(self, group_name):
        chs = self._playlist_groups_cache.get(group_name, [])
        self.menu_context = "playlist_group_items"
        items = []
        for ch in chs[:400]:
            items.append(("• %s" % ch.get("title", "Bez nazwy" if self.lang == "pl" else "No name"), ("pl_item", ch)))
        items.append((_("⬅️ Powrót", self.lang), ("pl_groups_back", None)))
        self["menu_list"].setList(items)
        self["status_bar"].setText(group_name)

    def addPlaylistToFavorites(self):
        if not self.current_playlist:
            return

        def _ask_group(_):
            self.session.openWithCallback(self.onFavGroupName, VirtualKeyBoard, title=_("Nazwa grupy ulubionych:", self.lang), text="Ulubione")

        self.session.openWithCallback(_ask_group, MessageBox, _("Dodać wszystkie kanały do ulubionych?", self.lang), MessageBox.TYPE_YESNO)

    def onFavGroupName(self, group_name):
        if not group_name:
            return
        try:
            for ch in self.current_playlist:
                self.favorites.add_to_favorites(ch, group_name=group_name)
            self.session.open(MessageBox, _("Dodano do ulubionych (grupa: %s).", self.lang) % group_name, MessageBox.TYPE_INFO, timeout=3)
        except Exception as e:
            self.session.open(MessageBox, _("Błąd ulubionych: %s", self.lang) % e, MessageBox.TYPE_ERROR)

    def downloadPiconsForPlaylist(self):
        if not self.current_playlist:
            return

        self.startLoading(_("Pobieranie picon ...", self.lang))

        def _work():
            """Pobiera pikony szybciej (wielowątkowo) i aktualizuje progress."""
            items = []
            for ch in (self.current_playlist or []):
                title = (ch.get("title") or "").strip()
                purl = (ch.get("tvg-logo") or ch.get("logo") or "").strip()
                if title and purl:
                    items.append((purl, title))

            total = len(items)
            if total <= 0:
                return 0

            # Liczba równoległych pobrań z konfiguracji PiconManager (fallback=5)
            max_workers = 5
            try:
                max_workers = int(getattr(self.picons, "config", {}).get("max_concurrent_downloads", 5))
            except Exception:
                max_workers = 5
            if max_workers < 1:
                max_workers = 1
            if max_workers > 12:
                max_workers = 12

            ok = 0
            done = 0

            def _one(purl_title):
                purl, title = purl_title
                try:
                    out = self.picons.download_picon(purl, title)
                    return True if out else False
                except Exception:
                    return False

            # Spróbuj concurrent.futures; jeśli niedostępne, leć sekwencyjnie.
            try:
                from concurrent.futures import ThreadPoolExecutor, as_completed
                with ThreadPoolExecutor(max_workers=max_workers) as ex:
                    futs = [ex.submit(_one, it) for it in items]
                    for fut in as_completed(futs):
                        done += 1
                        try:
                            if fut.result():
                                ok += 1
                        except Exception:
                            pass
                        if total > 0 and (done % 10 == 0 or done == total):
                            try:
                                reactor.callFromThread(
                                    self.updateProgress,
                                    min(100, (done / float(total)) * 100),
                                    "Picon %d/%d" % (done, total)
                                )
                            except Exception:
                                pass
            except Exception:
                for it in items:
                    done += 1
                    if _one(it):
                        ok += 1
                    if total > 0 and (done % 25 == 0 or done == total):
                        try:
                            reactor.callFromThread(self.updateProgress, min(100, (done / float(total)) * 100), "Picon %d/%d" % (done, total))
                        except Exception:
                            pass

            return ok

        def _done(res, err):
            self.stopLoading()
            if err:
                self.session.open(MessageBox, "Picon error: %s" % err, MessageBox.TYPE_ERROR)
                return
            self.session.open(MessageBox, _("Pobrano/gotowe picon: %d", self.lang) % res, MessageBox.TYPE_INFO)

        run_in_thread(_work, _done)

    def installEpgAndMap(self):
        # w tej paczce: instalacja źródeł EPG; mapowanie (jeśli potrzeba) pozostaje w module EPGManager
        self.forceInstallEPG()

    def refreshLastSource(self):
        src = self.cfg.get("last_source")
        if not src:
            self.session.open(MessageBox, _("Brak ostatniego źródła.", self.lang), MessageBox.TYPE_INFO)
            return
        st = src.get("type")
        val = src.get("value")
        if st == "m3u_url":
            return self.onUrlReady(val)
        if st == "m3u_file":
            return self.onFileReady(val)
        if st == "mac":
            return self.startMacDownload(val.get("host"), val.get("mac"), content_type=val.get("filter","live"))
        if st == "xtream":
            host = val.get("host")
            user = val.get("user")
            pwd = val.get("pass")
            flt = val.get("filter", "all")
            self.xtream_data = (host, user, pwd)
            return self.onXtreamTypeSelected(("REFRESH", flt))

    # ---------- EPG / Update / Settings ----------

    def forceInstallEPG(self):
        custom_url = self.cfg.get(EPG_URL_KEY)
        try:
            ok, msg = install_epg_sources(custom_url=custom_url)
            if ok:
                self.session.open(MessageBox, "%s" % msg, MessageBox.TYPE_INFO)
            else:
                self.session.open(MessageBox, "EPG error: %s" % msg, MessageBox.TYPE_ERROR)
        except Exception as e:
            self.session.open(MessageBox, "EPG error: %s" % e, MessageBox.TYPE_ERROR)

    def checkUpdates(self):
        self.startLoading(_("Sprawdzanie aktualizacji ...", self.lang))

        def _chk():
            # tools/updater.check_update() zwraca 4 wartości w repo:
            # (is_update, local, remote_or_msg, changelog)
            return check_update()

        def _done(res, err):
            self.stopLoading()
            if err:
                self.session.open(MessageBox, "Update error: %s" % err, MessageBox.TYPE_ERROR)
                return
            # Normalizacja wyniku (różne implementacje mogą zwracać inne krotki)
            if isinstance(res, tuple) and len(res) >= 4:
                has_upd, local, remote_or_msg, changelog = res[0], res[1], res[2], res[3]
                if remote_or_msg in ("Błąd sieci", "NETWORK_ERROR"):
                    self.session.open(MessageBox, _("Błąd sieci podczas sprawdzania aktualizacji.\n\nWersja lokalna: %s", self.lang) % local, MessageBox.TYPE_ERROR)
                    return
                if not has_upd:
                    self.session.open(MessageBox, _("Brak aktualizacji.\n\nLokalna: %s\nZdalna: %s", self.lang) % (local, remote_or_msg), MessageBox.TYPE_INFO)
                    return
                info = "Lokalna: %s\nZdalna: %s" % (local, remote_or_msg)
                if changelog:
                    info += "\n\nChangelog:\n%s" % changelog[:800]
                self.session.openWithCallback(lambda yn: self._do_update_yesno(yn, info), MessageBox,
                                              _("Dostępna aktualizacja:\n%s\n\nZainstalować?", self.lang) % info, MessageBox.TYPE_YESNO)
                return

            # fallback dla starych wersji
            try:
                ok, info = res
            except Exception:
                self.session.open(MessageBox, _("Update error: unknown response format", self.lang), MessageBox.TYPE_ERROR)
                return
            if not ok:
                self.session.open(MessageBox, (_("Brak aktualizacji.\n\n%s", self.lang) % info), MessageBox.TYPE_INFO)
                return
            self.session.openWithCallback(lambda yn: self._do_update_yesno(yn, info), MessageBox,
                                          _("Dostępna aktualizacja:\n%s\n\nZainstalować?", self.lang) % info, MessageBox.TYPE_YESNO)

        run_in_thread(_chk, _done)

    def _do_update_yesno(self, yes, info):
        if not yes:
            return
        self.startLoading(_("Instalowanie aktualizacji ...", self.lang))

        def _upd():
            return do_update()

        def _done(res, err):
            self.stopLoading()
            if err:
                self.session.open(MessageBox, "Update error: %s" % err, MessageBox.TYPE_ERROR)
                return
            # tools/updater.do_update() w repo zwykle zwraca tylko True (bez komunikatu).
            if isinstance(res, tuple) and len(res) >= 2:
                ok, msg = res[0], res[1]
                self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)
                return
            if res is True:
                self.session.open(MessageBox, _("Zainstalowano aktualizację. Zrestartuj GUI.", self.lang), MessageBox.TYPE_INFO)
            else:
                self.session.open(MessageBox, _("Aktualizacja zakończona (brak szczegółów).", self.lang), MessageBox.TYPE_INFO)

        run_in_thread(_upd, _done)

    def showSettings(self):
        items = []
        items.append((_("Język: %s", self.lang) % ("PL" if self.lang == "pl" else "EN"), "lang"))
        items.append((_("Typ serwisu: %d", self.lang) % self.service_type, "stype"))
        items.append(("EPG URL (custom)", "epgurl"))
        items.append((_("⬅️ Powrót", self.lang), "back"))

        self.session.openWithCallback(self.onSettingsChoice, ChoiceBox, title=_("Ustawienia", self.lang), list=items)

    def onSettingsChoice(self, choice):
        if not choice:
            return
        act = choice[1]
        if act == "lang":
            self.lang = "en" if self.lang == "pl" else "pl"
            self.cfg["language"] = self.lang
            self._save_cfg()
            self.session.open(MessageBox, (_("lang_changed", self.lang) + " %s") % self.lang.upper(), MessageBox.TYPE_INFO, timeout=2)
            return
        if act == "stype":
            self.service_type = 5002 if self.service_type == 4097 else 4097
            self.cfg["service_type"] = self.service_type
            self._save_cfg()
            self.session.open(MessageBox, (_("Typ serwisu: %d", self.lang) % self.service_type), MessageBox.TYPE_INFO, timeout=2)
            return
        if act == "epgurl":
            cur = self.cfg.get(EPG_URL_KEY, "http://")
            self.session.openWithCallback(self.onEpgUrlReady, VirtualKeyBoard, title=_("Wklej URL EPG:", self.lang), text=cur)
            return

    def onEpgUrlReady(self, url):
        if not url:
            return
        self.cfg[EPG_URL_KEY] = url
        self._save_cfg()
        self.session.open(MessageBox, _("Zapisano URL EPG.", self.lang), MessageBox.TYPE_INFO, timeout=2)

    def clearCache(self):
        try:
            if os.path.exists(CACHE_DIR):
                for root, dirs, files in os.walk(CACHE_DIR, topdown=False):
                    for f in files:
                        try:
                            os.remove(os.path.join(root, f))
                        except Exception:
                            pass
                    for d in dirs:
                        try:
                            os.rmdir(os.path.join(root, d))
                        except Exception:
                            pass
            _safe_mkdir(CACHE_DIR)
            self.session.open(MessageBox, _("Wyczyszczono cache.", self.lang), MessageBox.TYPE_INFO, timeout=2)
        except Exception as e:
            self.session.open(MessageBox, "Cache error: %s" % e, MessageBox.TYPE_ERROR)

    def clearHistory(self):
        try:
            self.history.clear_history()
            self.session.open(MessageBox, _("Wyczyszczono historię.", self.lang), MessageBox.TYPE_INFO, timeout=2)
        except Exception as e:
            self.session.open(MessageBox, "History error: %s" % e, MessageBox.TYPE_ERROR)

    def showStats(self):
        try:
            st = self.statistics.get_stats(lang=self.lang)
        except Exception:
            st = []

        txt = "📊 STATYSTYKI\n\n" if self.lang == "pl" else "📊 STATISTICS\n\n"

        if st:
            it = st.items() if hasattr(st, "items") else st
            for k, v in it:
                if v == "" or v is None:
                    txt += "%s\n" % (k,)
                else:
                    txt += "%s: %s\n" % (k, v)
        else:
            txt += _("Brak danych.", self.lang)

        self.updateInfoPanel(_("Statystyki", self.lang), txt)

    # ---------- eksport ----------

    def exportBouquet(self):
        if not self.current_playlist:
            self.session.open(MessageBox, _("Najpierw wczytaj playlistę!", self.lang), MessageBox.TYPE_ERROR)
            return

        groups = {}
        for ch in self.current_playlist:
            grp = ch.get("group", "Inne" if self.lang == "pl" else "Other")
            groups.setdefault(grp, []).append(ch)

        self.export_groups = groups
        self.session.openWithCallback(self.onBouquetsSelected, BouquetPicker, self.export_groups)

    def onBouquetsSelected(self, selected_keys):
        if not selected_keys:
            return
        final_list = []
        for k in selected_keys:
            final_list.extend(self.export_groups.get(k, []))

        res, chans = export_bouquets(final_list, self.playlist_name)

        try:
            if eDVBDB:
                eDVBDB.getInstance().reloadBouquets()
                eDVBDB.getInstance().reloadServicelist()
        except Exception:
            pass

        self.session.open(MessageBox, _("exported_channels_bouquets", self.lang) % (chans, res), MessageBox.TYPE_INFO)

    # ---------- close ----------

    def close(self):
        try:
            self._save_cfg()
        except Exception:
            pass
        try:
            if self.webif_enabled:
                stop_web_server()
        except Exception:
            pass
        try:
            if self.loading_timer:
                self.loading_timer.stop()
        except Exception:
            pass
        Screen.close(self)


# Alias dla zgodności z plugin.py
IPTVDreamMain = IPTVDreamV6


def parse_m3u_bytes_improved(data, content_filter=None):
    """Parser M3U (kompatybilny z poprzednimi wydaniami).

    Args:
        data: bytes
        content_filter: live/vod/adult/all/None
    Returns:
        list[dict]
    """
    if not data:
        return []

    try:
        text = data.decode("utf-8", "ignore")
    except Exception:
        try:
            text = data.decode("latin-1", "ignore")
        except Exception:
            return []

    lines = text.splitlines()
    out = []

    # filtry - heurystyka na podstawie group-title / tvg-name
    def _match_filter(meta):
        if not content_filter or content_filter in ("all",):
            return True
        meta_l = (meta or "").lower()
        if content_filter == "adult":
            return ("xxx" in meta_l) or ("adult" in meta_l)
        if content_filter == "vod":
            return ("vod" in meta_l) or ("movie" in meta_l) or ("series" in meta_l)
        if content_filter == "live":
            # Live: wszystko, co nie wygląda na VOD/XXX
            return not (("vod" in meta_l) or ("movie" in meta_l) or ("series" in meta_l) or ("xxx" in meta_l) or ("adult" in meta_l))
        return True

    extinf_re = re.compile(r"#EXTINF:(?P<attrs>[^,]*),(?P<title>.*)$")
    attr_re = re.compile(r'(\w+?)="(.*?)"')

    cur = None
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if ln.startswith("#EXTINF"):
            m = extinf_re.match(ln)
            if not m:
                cur = None
                continue
            attrs = m.group("attrs")
            title = (m.group("title") or "").strip()
            a = {k: v for (k, v) in attr_re.findall(attrs)}
            group = a.get("group-title") or a.get("group") or "Inne"
            logo = a.get("tvg-logo") or ""
            if not _match_filter(group + " " + title):
                cur = None
                continue
            cur = {
                "title": title,
                "group": group,
                "tvg-logo": logo,
                "tvg-id": a.get("tvg-id", ""),
                "tvg-name": a.get("tvg-name", ""),
            }
            continue
        if ln.startswith("#"):
            continue
        # URL
        if cur is not None:
            cur["url"] = ln
            out.append(cur)
            cur = None

    return out
