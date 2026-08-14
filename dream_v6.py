# -*- coding: utf-8 -*-
"""IPTV Dream v8.0.0

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

try:
    from urllib.parse import urlencode
except Exception:
    from urllib import urlencode

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
from .tools.lang import _, SUPPORTED_LANGS, LANGUAGE_NAMES, normalize_lang
from .tools.net import http_get
from .tools.logger import get_logger, mask_sensitive
from .tools.bouquet_picker import BouquetPicker
from .tools.webif import start_web_server, stop_web_server
from .tools.updater import check_update, do_update
from .tools.epg_picon import install_epg_sources
from .tools.favorites import FavoritesManager
from .tools.statistics import StatisticsManager
from .tools.history import HistoryManager
from .tools.mac_portal import load_mac_json, save_mac_json, add_mac_portal, clear_mac_backups
from .tools.mac_portal import _parse_json_flexible as parse_json_flexible_mac
from .tools.mac_portal import parse_mac_playlist
from .tools.picon_manager_v6 import PiconManager
from .tools.epg_manager_v6 import EPGManager
from .tools.xtream_one_window_fixed import XtreamWindow  # alias w pliku

from .core.playlist_loader import PlaylistLoader

def _read_version():
    try:
        here = os.path.dirname(__file__)
        vp = os.path.join(here, "VERSION")
        if os.path.exists(vp):
            with open(vp, "r", encoding="utf-8") as f:
                v = (f.read() or "").strip()
                if v:
                    return v
    except Exception:
        pass
    return "8.0.0"

PLUGIN_VERSION = _read_version()
CONFIG_FILE = "/etc/enigma2/iptvdream_v6_config.json"
CACHE_DIR = "/tmp/iptvdream_cache"
LEGACY_CACHE_DIR = "/tmp/iptvdream_v6_cache"

DL_TIMEOUT = 90
LOAD_TIMEOUT_DEFAULT_MS = 180000  # 3 minuty (domyślnie)
MAC_VODSERIES_TIMEOUT_MS = 600000  # 10 minut: duże MAC VOD/Seriale, ale bez wiszenia godzinami
LOAD_TIMEOUT_MS = LOAD_TIMEOUT_DEFAULT_MS
WEBIF_PORT = 9999


def _detect_system_language():
    """Return supported system language or English fallback."""
    try:
        lang = (language.getLanguage() or "en")[:2].lower()
    except Exception:
        lang = "en"
    return lang if lang in SUPPORTED_LANGS else "en"

def _language_display_name(code):
    code = normalize_lang(code, 'en')
    return LANGUAGE_NAMES.get(code, code.upper())

EPG_URL_KEY = "epg_url"

PROJECT_URL = "https://olioli2013.github.io/aio-iptv-projekt/"

PROJECT_LABELS = {
    "pl": ("Strona projektu", "Zeskanuj kod QR, aby odwiedzić stronę twórcy."),
    "en": ("Project website", "Scan the QR code to visit the creator website."),
    "de": ("Projekt-Webseite", "Scanne den QR-Code, um die Webseite des Autors zu öffnen."),
    "es": ("Web del proyecto", "Escanea el código QR para visitar la web del creador."),
    "ar": ("موقع المشروع", "امسح رمز QR لزيارة موقع المطور."),
    "ru": ("Сайт проекта", "Отсканируйте QR-код, чтобы открыть сайт автора."),
}

# Context help is intentionally kept inside the main screen instead of opening
# extra dialogs. Moving the selection immediately explains what the option does.
ACTION_HELP = {
    "pl": {
        "m3u_url": ("M3U z URL", "Dodaje playlistę M3U/M3U8 z adresu internetowego. Wklej pełny URL listy; wtyczka pobierze i pogrupuje kanały.", "OK: wprowadź adres playlisty M3U."),
        "m3u_file": ("M3U z pliku", "Otwiera lokalny plik M3U/M3U8 z pamięci tunera, /tmp lub nośnika USB.", "OK: wybierz plik M3U/M3U8."),
        "xtream": ("Xtream Codes", "Łączy się z panelem Xtream przy użyciu hosta, użytkownika i hasła. Obsługuje LIVE, VOD i filtrowanie treści.", "OK: otwórz konfigurację Xtream Codes."),
        "mac": ("MAC Portal", "Obsługa portali MAC / Stalker / MAG. Dodaj portal albo wybierz zapisany profil i rodzaj treści.", "OK: otwórz listę portali MAC."),
        "favorites": ("Ulubione", "Otwiera zapisane grupy i kanały dodane do ulubionych w IPTV Dream.", "OK: pokaż ulubione."),
        "manage": ("Zarządzanie", "Język, typ serwisu 4097/5002, EPG, logi, cache, historia oraz zarządzanie bukietami IPTV Dream.", "OK: otwórz ustawienia i narzędzia."),
        "stats": ("Statystyki", "Pokazuje statystyki sesji, ładowania playlist oraz użycia wtyczki.", "OK: pokaż statystyki."),
        "webif": ("Web Interfejs", "Włącza lub wyłącza WebIF IPTV Dream na porcie 9999 w sieci lokalnej.", "OK: przełącz WebIF."),
        "update": ("Aktualizacje", "Sprawdza wersję w oficjalnym repozytorium i może bezpiecznie zainstalować nowsze wydanie.", "OK: sprawdź aktualizacje."),
        "lang": ("Język", "Wybiera język interfejsu albo tryb automatyczny zgodny z językiem Enigma2.", "OK: wybierz język."),
        "stype": ("Typ serwisu", "Przełącza referencje IPTV pomiędzy 4097 i 5002. Użyj typu najlepiej współpracującego z odtwarzaczem Twojego image.", "OK: przełącz 4097 / 5002."),
        "epgurl": ("Własny URL EPG", "Pozwala zapisać własne źródło XMLTV/EPG używane przez narzędzia EPG.", "OK: wprowadź adres EPG."),
        "debug_toggle": ("Tryb debug", "Włącza szczegółowy zapis diagnostyczny do /tmp/iptvdream.log. Używaj głównie podczas diagnozy błędów.", "OK: włącz lub wyłącz debug."),
        "show_log": ("Pokaż log", "Wyświetla ostatnią część logu IPTV Dream z informacjami diagnostycznymi.", "OK: otwórz log."),
        "clear_log": ("Wyczyść log", "Czyści plik diagnostyczny IPTV Dream bez zmiany ustawień i playlist.", "OK: wyczyść log."),
        "clear_cache": ("Wyczyść cache", "Usuwa tymczasowy cache playlist. Przy następnym otwarciu lista zostanie pobrana ponownie.", "OK: usuń cache."),
        "clear_history": ("Wyczyść historię", "Usuwa lokalną historię użycia i oglądanych pozycji IPTV Dream.", "OK: wyczyść historię."),
        "delete_bouquets": ("Usuń bukiety IPTV Dream", "Pozwala usunąć bukiety utworzone przez IPTV Dream z listy kanałów Enigma2.", "OK: wybierz zestaw do usunięcia."),
        "preview": ("Podgląd playlisty", "Pokazuje liczbę kanałów oraz grupy wykryte w aktualnie załadowanej playliście.", "OK: pokaż podsumowanie."),
        "groups": ("Grupy / bukiety", "Otwiera grupy z playlisty. Przy eksporcie ich nazwy są używane jako czyste nazwy bukietów bez nazwy listy/portalu.", "OK: pokaż grupy."),
        "fav_add_all": ("Dodaj do ulubionych", "Dodaje wszystkie kanały z aktualnej playlisty do wskazanej grupy ulubionych.", "OK: wybierz nazwę grupy ulubionych."),
        "picons": ("Pikony", "Pobiera logotypy kanałów z adresów tvg-logo i zapisuje je w wybranym katalogu picon.", "OK: wybierz miejsce zapisu piconów."),
        "epg_map": ("EPG + przypisanie", "Instaluje źródła EPG i przygotowuje mapowanie kanałów do EPGImport.", "OK: uruchom mapowanie EPG."),
        "refresh": ("Odśwież źródło", "Ponownie pobiera ostatnio użyte źródło M3U, Xtream lub MAC i odświeża listę.", "OK: odśwież playlistę."),
        "mac_add": ("Dodaj portal MAC", "Dodaje profil portalu MAC/Stalker/MAG na podstawie hosta i adresu MAC.", "OK: dodaj portal."),
        "mac_delete": ("Usuń portal MAC", "Usuwa zapisany profil portalu MAC z konfiguracji IPTV Dream.", "OK: wybierz portal do usunięcia."),
    },
    "en": {
        "m3u_url": ("M3U URL", "Adds an M3U/M3U8 playlist from an Internet address. Paste the full URL; IPTV Dream will download and group channels.", "OK: enter the M3U playlist URL."),
        "m3u_file": ("M3U file", "Opens a local M3U/M3U8 file from receiver storage, /tmp or a USB device.", "OK: choose an M3U/M3U8 file."),
        "xtream": ("Xtream Codes", "Connects to an Xtream panel using host, username and password. Supports LIVE, VOD and content filtering.", "OK: open Xtream Codes setup."),
        "mac": ("MAC Portal", "Handles MAC / Stalker / MAG portals. Add a portal or select a saved profile and content type.", "OK: open MAC portals."),
        "favorites": ("Favorites", "Opens saved favorite groups and channels stored by IPTV Dream.", "OK: show favorites."),
        "manage": ("Management", "Language, 4097/5002 service type, EPG, logs, cache, history and IPTV Dream bouquet management.", "OK: open settings and tools."),
        "stats": ("Statistics", "Shows session, playlist-loading and plugin usage statistics.", "OK: show statistics."),
        "webif": ("Web Interface", "Enables or disables IPTV Dream WebIF on port 9999 in the local network.", "OK: toggle WebIF."),
        "update": ("Updates", "Checks the official repository and can safely install a newer release.", "OK: check for updates."),
        "lang": ("Language", "Selects the interface language or automatic mode following the Enigma2 system language.", "OK: choose language."),
        "stype": ("Service type", "Switches IPTV service references between 4097 and 5002. Use the type that works best with your image/player.", "OK: switch 4097 / 5002."),
        "epgurl": ("Custom EPG URL", "Stores a custom XMLTV/EPG source used by IPTV Dream EPG tools.", "OK: enter EPG URL."),
        "debug_toggle": ("Debug mode", "Enables detailed diagnostics in /tmp/iptvdream.log. Mainly useful when troubleshooting.", "OK: toggle debug."),
        "show_log": ("Show log", "Displays the latest IPTV Dream diagnostic log entries.", "OK: open log."),
        "clear_log": ("Clear log", "Clears the IPTV Dream diagnostic log without changing playlists or settings.", "OK: clear log."),
        "clear_cache": ("Clear cache", "Removes temporary playlist cache. The source will be downloaded again next time.", "OK: clear cache."),
        "clear_history": ("Clear history", "Removes local IPTV Dream usage/watch history.", "OK: clear history."),
        "delete_bouquets": ("Delete IPTV Dream bouquets", "Lets you remove bouquets created by IPTV Dream from Enigma2 channel lists.", "OK: choose bouquet set to delete."),
        "preview": ("Playlist preview", "Shows channel count and groups detected in the currently loaded playlist.", "OK: show summary."),
        "groups": ("Groups / bouquets", "Opens playlist groups. Export uses the clean group name as the visible bouquet name, without source/portal prefixes.", "OK: show groups."),
        "fav_add_all": ("Add to favorites", "Adds all channels in the current playlist to a favorite group you choose.", "OK: choose favorite group name."),
        "picons": ("Picons", "Downloads channel logos from tvg-logo URLs and stores them in the selected picon directory.", "OK: choose picon destination."),
        "epg_map": ("EPG + mapping", "Installs EPG sources and prepares channel mapping for EPGImport.", "OK: start EPG mapping."),
        "refresh": ("Refresh source", "Downloads the last M3U, Xtream or MAC source again and refreshes the playlist.", "OK: refresh playlist."),
        "mac_add": ("Add MAC portal", "Adds a MAC/Stalker/MAG portal profile using host and MAC address.", "OK: add portal."),
        "mac_delete": ("Delete MAC portal", "Removes a saved MAC portal profile from IPTV Dream.", "OK: choose portal to delete."),
    },
    "de": {
        "m3u_url": ("M3U-URL", "Fügt eine M3U/M3U8-Playlist aus dem Internet hinzu. Vollständige URL einfügen; IPTV Dream lädt und gruppiert die Sender.", "OK: M3U-URL eingeben."),
        "m3u_file": ("M3U-Datei", "Öffnet eine lokale M3U/M3U8-Datei vom Receiver, aus /tmp oder von USB.", "OK: M3U/M3U8-Datei auswählen."),
        "xtream": ("Xtream Codes", "Verbindet sich über Host, Benutzername und Passwort mit Xtream. LIVE, VOD und Filter werden unterstützt.", "OK: Xtream Codes öffnen."),
        "mac": ("MAC-Portal", "Unterstützt MAC/Stalker/MAG-Portale. Portal hinzufügen oder gespeichertes Profil und Inhaltstyp wählen.", "OK: MAC-Portale öffnen."),
        "favorites": ("Favoriten", "Öffnet gespeicherte Favoritengruppen und Sender.", "OK: Favoriten anzeigen."),
        "manage": ("Verwaltung", "Sprache, Servicetyp 4097/5002, EPG, Logs, Cache, Verlauf und IPTV-Dream-Bouquets verwalten.", "OK: Einstellungen öffnen."),
        "stats": ("Statistiken", "Zeigt Sitzungs-, Playlist- und Nutzungsstatistiken.", "OK: Statistiken anzeigen."),
        "webif": ("Webinterface", "Schaltet das IPTV-Dream-WebIF im lokalen Netz auf Port 9999 ein oder aus.", "OK: WebIF umschalten."),
        "update": ("Updates", "Prüft das offizielle Repository und kann eine neue Version sicher installieren.", "OK: nach Updates suchen."),
        "lang": ("Sprache", "Wählt die Sprache oder den Automatikmodus entsprechend Enigma2.", "OK: Sprache wählen."),
        "stype": ("Servicetyp", "Wechselt IPTV-Service-Referenzen zwischen 4097 und 5002.", "OK: 4097 / 5002 wechseln."),
        "epgurl": ("Eigene EPG-URL", "Speichert eine eigene XMLTV/EPG-Quelle für die EPG-Werkzeuge.", "OK: EPG-URL eingeben."),
        "debug_toggle": ("Debug-Modus", "Aktiviert ausführliche Diagnose in /tmp/iptvdream.log.", "OK: Debug umschalten."),
        "show_log": ("Log anzeigen", "Zeigt die letzten IPTV-Dream-Diagnoseeinträge.", "OK: Log öffnen."),
        "clear_log": ("Log löschen", "Leert das Diagnose-Log ohne Einstellungen zu ändern.", "OK: Log löschen."),
        "clear_cache": ("Cache leeren", "Löscht den Playlist-Cache; die Quelle wird beim nächsten Mal neu geladen.", "OK: Cache leeren."),
        "clear_history": ("Verlauf löschen", "Löscht den lokalen IPTV-Dream-Verlauf.", "OK: Verlauf löschen."),
        "delete_bouquets": ("IPTV-Dream-Bouquets löschen", "Entfernt von IPTV Dream erstellte Bouquets aus Enigma2.", "OK: Bouquet-Satz wählen."),
        "preview": ("Playlist-Übersicht", "Zeigt Senderzahl und erkannte Gruppen der geladenen Playlist.", "OK: Übersicht anzeigen."),
        "groups": ("Gruppen / Bouquets", "Öffnet Playlist-Gruppen. Beim Export wird nur der saubere Gruppenname als Bouquetname verwendet.", "OK: Gruppen anzeigen."),
        "fav_add_all": ("Zu Favoriten", "Fügt alle Sender der aktuellen Playlist einer Favoritengruppe hinzu.", "OK: Favoritengruppe wählen."),
        "picons": ("Picons", "Lädt Senderlogos aus tvg-logo und speichert sie im gewählten Picon-Verzeichnis.", "OK: Picon-Ziel wählen."),
        "epg_map": ("EPG + Zuordnung", "Installiert EPG-Quellen und erstellt die Zuordnung für EPGImport.", "OK: EPG-Zuordnung starten."),
        "refresh": ("Quelle aktualisieren", "Lädt die zuletzt verwendete M3U-, Xtream- oder MAC-Quelle erneut.", "OK: Playlist aktualisieren."),
        "mac_add": ("MAC-Portal hinzufügen", "Fügt ein MAC/Stalker/MAG-Profil mit Host und MAC-Adresse hinzu.", "OK: Portal hinzufügen."),
        "mac_delete": ("MAC-Portal löschen", "Entfernt ein gespeichertes MAC-Portalprofil.", "OK: Portal zum Löschen wählen."),
    },
    "es": {
        "m3u_url": ("URL M3U", "Añade una lista M3U/M3U8 desde Internet. Pega la URL completa; IPTV Dream descargará y agrupará los canales.", "OK: introduce la URL M3U."),
        "m3u_file": ("Archivo M3U", "Abre un archivo M3U/M3U8 local del receptor, /tmp o USB.", "OK: selecciona el archivo M3U/M3U8."),
        "xtream": ("Xtream Codes", "Conecta con Xtream usando host, usuario y contraseña. Admite LIVE, VOD y filtros.", "OK: abre Xtream Codes."),
        "mac": ("Portal MAC", "Gestiona portales MAC/Stalker/MAG. Añade un portal o elige un perfil guardado y el tipo de contenido.", "OK: abre los portales MAC."),
        "favorites": ("Favoritos", "Abre grupos y canales guardados como favoritos.", "OK: muestra favoritos."),
        "manage": ("Gestión", "Idioma, servicio 4097/5002, EPG, logs, caché, historial y bouquets de IPTV Dream.", "OK: abre ajustes y herramientas."),
        "stats": ("Estadísticas", "Muestra estadísticas de sesión, listas y uso del plugin.", "OK: muestra estadísticas."),
        "webif": ("Interfaz web", "Activa o desactiva WebIF de IPTV Dream en el puerto 9999 de la red local.", "OK: cambia WebIF."),
        "update": ("Actualizaciones", "Comprueba el repositorio oficial y puede instalar una versión más reciente de forma segura.", "OK: buscar actualizaciones."),
        "lang": ("Idioma", "Selecciona el idioma o el modo automático según Enigma2.", "OK: elige idioma."),
        "stype": ("Tipo de servicio", "Cambia las referencias IPTV entre 4097 y 5002.", "OK: cambia 4097 / 5002."),
        "epgurl": ("URL EPG propia", "Guarda una fuente XMLTV/EPG personalizada para las herramientas EPG.", "OK: introduce URL EPG."),
        "debug_toggle": ("Modo debug", "Activa diagnóstico detallado en /tmp/iptvdream.log.", "OK: cambia debug."),
        "show_log": ("Ver log", "Muestra las últimas entradas de diagnóstico de IPTV Dream.", "OK: abre el log."),
        "clear_log": ("Borrar log", "Vacía el log sin cambiar listas ni ajustes.", "OK: borra el log."),
        "clear_cache": ("Borrar caché", "Elimina la caché de listas; la fuente se descargará otra vez.", "OK: borra la caché."),
        "clear_history": ("Borrar historial", "Elimina el historial local de IPTV Dream.", "OK: borra el historial."),
        "delete_bouquets": ("Borrar bouquets IPTV Dream", "Elimina bouquets creados por IPTV Dream de Enigma2.", "OK: elige el conjunto a borrar."),
        "preview": ("Vista previa", "Muestra número de canales y grupos detectados en la lista cargada.", "OK: muestra el resumen."),
        "groups": ("Grupos / bouquets", "Abre los grupos. Al exportar se usa solo el nombre limpio del grupo como bouquet.", "OK: muestra los grupos."),
        "fav_add_all": ("Añadir a favoritos", "Añade todos los canales a un grupo de favoritos elegido.", "OK: elige el grupo."),
        "picons": ("Picons", "Descarga logos desde tvg-logo y los guarda en el directorio elegido.", "OK: elige destino de picons."),
        "epg_map": ("EPG + mapeo", "Instala fuentes EPG y prepara el mapeo para EPGImport.", "OK: iniciar mapeo EPG."),
        "refresh": ("Actualizar fuente", "Vuelve a descargar la última fuente M3U, Xtream o MAC.", "OK: actualiza la lista."),
        "mac_add": ("Añadir portal MAC", "Añade un perfil MAC/Stalker/MAG con host y dirección MAC.", "OK: añade portal."),
        "mac_delete": ("Eliminar portal MAC", "Elimina un perfil MAC guardado.", "OK: elige portal a eliminar."),
    },
    "ar": {
        "m3u_url": ("رابط M3U", "يضيف قائمة M3U/M3U8 من الإنترنت. الصق الرابط الكامل وسيقوم IPTV Dream بتنزيل القنوات وتجميعها.", "OK: أدخل رابط M3U."),
        "m3u_file": ("ملف M3U", "يفتح ملف M3U/M3U8 محلياً من الجهاز أو /tmp أو USB.", "OK: اختر ملف M3U/M3U8."),
        "xtream": ("Xtream Codes", "يتصل بلوحة Xtream باستخدام المضيف واسم المستخدم وكلمة المرور ويدعم LIVE وVOD والفلاتر.", "OK: افتح إعداد Xtream Codes."),
        "mac": ("بوابة MAC", "يدير بوابات MAC/Stalker/MAG. أضف بوابة أو اختر ملفاً محفوظاً ونوع المحتوى.", "OK: افتح بوابات MAC."),
        "favorites": ("المفضلة", "يفتح مجموعات وقنوات المفضلة المحفوظة.", "OK: اعرض المفضلة."),
        "manage": ("الإدارة", "اللغة ونوع الخدمة 4097/5002 وEPG والسجلات والكاش والتاريخ وباقات IPTV Dream.", "OK: افتح الإعدادات والأدوات."),
        "stats": ("الإحصائيات", "يعرض إحصائيات الجلسة وتحميل القوائم واستخدام الإضافة.", "OK: اعرض الإحصائيات."),
        "webif": ("واجهة الويب", "تشغيل أو إيقاف WebIF على المنفذ 9999 في الشبكة المحلية.", "OK: بدّل WebIF."),
        "update": ("التحديثات", "يفحص المستودع الرسمي ويمكنه تثبيت إصدار أحدث بأمان.", "OK: افحص التحديثات."),
        "lang": ("اللغة", "اختيار لغة الواجهة أو الوضع التلقائي حسب Enigma2.", "OK: اختر اللغة."),
        "stype": ("نوع الخدمة", "التبديل بين مراجع IPTV من النوع 4097 و5002.", "OK: بدّل 4097 / 5002."),
        "epgurl": ("رابط EPG خاص", "يحفظ مصدر XMLTV/EPG خاص لاستخدامه مع أدوات EPG.", "OK: أدخل رابط EPG."),
        "debug_toggle": ("وضع التصحيح", "يفعّل سجلاً تشخيصياً مفصلاً في /tmp/iptvdream.log.", "OK: بدّل وضع التصحيح."),
        "show_log": ("عرض السجل", "يعرض أحدث رسائل التشخيص الخاصة بـ IPTV Dream.", "OK: افتح السجل."),
        "clear_log": ("مسح السجل", "يمسح سجل التشخيص بدون تغيير القوائم أو الإعدادات.", "OK: امسح السجل."),
        "clear_cache": ("مسح الكاش", "يحذف كاش القوائم المؤقت وسيتم تنزيل المصدر من جديد.", "OK: امسح الكاش."),
        "clear_history": ("مسح السجل السابق", "يحذف تاريخ الاستخدام المحلي لـ IPTV Dream.", "OK: امسح التاريخ."),
        "delete_bouquets": ("حذف باقات IPTV Dream", "يحذف الباقات التي أنشأها IPTV Dream من Enigma2.", "OK: اختر الباقات للحذف."),
        "preview": ("معاينة القائمة", "يعرض عدد القنوات والمجموعات المكتشفة في القائمة الحالية.", "OK: اعرض الملخص."),
        "groups": ("المجموعات / الباقات", "يفتح مجموعات القائمة. عند التصدير يستخدم اسم المجموعة النظيف فقط كاسم للباقـة.", "OK: اعرض المجموعات."),
        "fav_add_all": ("إضافة للمفضلة", "يضيف كل القنوات إلى مجموعة مفضلة تختارها.", "OK: اختر مجموعة المفضلة."),
        "picons": ("Picons", "ينزل شعارات القنوات من tvg-logo ويحفظها في مجلد picon المختار.", "OK: اختر مجلد picon."),
        "epg_map": ("EPG + الربط", "يثبت مصادر EPG ويجهز ربط القنوات لـ EPGImport.", "OK: ابدأ ربط EPG."),
        "refresh": ("تحديث المصدر", "يعيد تنزيل آخر مصدر M3U أو Xtream أو MAC.", "OK: حدّث القائمة."),
        "mac_add": ("إضافة بوابة MAC", "يضيف ملف بوابة MAC/Stalker/MAG باستخدام المضيف وعنوان MAC.", "OK: أضف البوابة."),
        "mac_delete": ("حذف بوابة MAC", "يحذف ملف بوابة MAC محفوظاً.", "OK: اختر البوابة للحذف."),
    },
    "ru": {
        "m3u_url": ("M3U по URL", "Добавляет M3U/M3U8-плейлист из Интернета. Вставьте полный URL; IPTV Dream загрузит и сгруппирует каналы.", "OK: введите URL M3U."),
        "m3u_file": ("Файл M3U", "Открывает локальный M3U/M3U8 из памяти ресивера, /tmp или USB.", "OK: выберите M3U/M3U8."),
        "xtream": ("Xtream Codes", "Подключается к Xtream по host, логину и паролю. Поддерживает LIVE, VOD и фильтры.", "OK: открыть Xtream Codes."),
        "mac": ("MAC-портал", "Работает с MAC/Stalker/MAG. Добавьте портал или выберите сохранённый профиль и тип контента.", "OK: открыть MAC-порталы."),
        "favorites": ("Избранное", "Открывает сохранённые группы и каналы избранного.", "OK: показать избранное."),
        "manage": ("Управление", "Язык, тип 4097/5002, EPG, логи, кэш, история и управление букетами IPTV Dream.", "OK: открыть настройки."),
        "stats": ("Статистика", "Показывает статистику сеанса, загрузки плейлистов и использования плагина.", "OK: показать статистику."),
        "webif": ("Web-интерфейс", "Включает или выключает WebIF IPTV Dream на порту 9999 в локальной сети.", "OK: переключить WebIF."),
        "update": ("Обновления", "Проверяет официальный репозиторий и может безопасно установить новую версию.", "OK: проверить обновления."),
        "lang": ("Язык", "Выбирает язык интерфейса или автоматический режим по Enigma2.", "OK: выбрать язык."),
        "stype": ("Тип сервиса", "Переключает IPTV service reference между 4097 и 5002.", "OK: переключить 4097 / 5002."),
        "epgurl": ("Свой URL EPG", "Сохраняет пользовательский источник XMLTV/EPG для инструментов EPG.", "OK: введите URL EPG."),
        "debug_toggle": ("Режим debug", "Включает подробную диагностику в /tmp/iptvdream.log.", "OK: переключить debug."),
        "show_log": ("Показать лог", "Показывает последние диагностические записи IPTV Dream.", "OK: открыть лог."),
        "clear_log": ("Очистить лог", "Очищает диагностический лог без изменения настроек и плейлистов.", "OK: очистить лог."),
        "clear_cache": ("Очистить кэш", "Удаляет временный кэш плейлистов; источник будет загружен заново.", "OK: очистить кэш."),
        "clear_history": ("Очистить историю", "Удаляет локальную историю IPTV Dream.", "OK: очистить историю."),
        "delete_bouquets": ("Удалить букеты IPTV Dream", "Удаляет букеты, созданные IPTV Dream, из Enigma2.", "OK: выберите набор букетов."),
        "preview": ("Обзор плейлиста", "Показывает число каналов и найденные группы текущего плейлиста.", "OK: показать сводку."),
        "groups": ("Группы / букеты", "Открывает группы. При экспорте видимым именем букета становится только чистое имя группы.", "OK: показать группы."),
        "fav_add_all": ("Добавить в избранное", "Добавляет все каналы в выбранную группу избранного.", "OK: выберите группу."),
        "picons": ("Пиконы", "Загружает логотипы из tvg-logo в выбранную папку picon.", "OK: выберите папку picon."),
        "epg_map": ("EPG + привязка", "Устанавливает источники EPG и создаёт привязку каналов для EPGImport.", "OK: начать привязку EPG."),
        "refresh": ("Обновить источник", "Повторно загружает последний источник M3U, Xtream или MAC.", "OK: обновить плейлист."),
        "mac_add": ("Добавить MAC-портал", "Добавляет профиль MAC/Stalker/MAG по host и MAC-адресу.", "OK: добавить портал."),
        "mac_delete": ("Удалить MAC-портал", "Удаляет сохранённый профиль MAC-портала.", "OK: выберите портал."),
    },
}

GENERIC_HELP = {
    "pl": ("Informacja", "Wybierz pozycję z listy. Opis aktualnie zaznaczonej funkcji pojawia się automatycznie.", "OK: wykonaj wybraną funkcję. EXIT: powrót."),
    "en": ("Information", "Select an item. The description of the highlighted function is shown automatically.", "OK: run selected function. EXIT: back."),
    "de": ("Information", "Wähle einen Eintrag. Die Beschreibung der markierten Funktion wird automatisch angezeigt.", "OK: Funktion ausführen. EXIT: zurück."),
    "es": ("Información", "Selecciona una opción. La descripción de la función marcada aparece automáticamente.", "OK: ejecutar. EXIT: volver."),
    "ar": ("معلومات", "اختر عنصراً من القائمة. يظهر شرح الوظيفة المحددة تلقائياً.", "OK: تنفيذ الوظيفة. EXIT: رجوع."),
    "ru": ("Информация", "Выберите пункт. Описание выделенной функции показывается автоматически.", "OK: выполнить. EXIT: назад."),
}


PROJECT_HELP = {
    "pl": ("Strona projektu / QR", "Pokazuje duży, czytelny kod QR prowadzący bezpośrednio do oficjalnej strony projektu IPTV Dream / AIO.", "OK lub 0: otwórz duży kod QR."),
    "en": ("Project website / QR", "Shows a large readable QR code linking directly to the official IPTV Dream / AIO project website.", "OK or 0: open the large QR code."),
    "de": ("Projekt-Webseite / QR", "Zeigt einen großen, gut lesbaren QR-Code zur offiziellen IPTV Dream / AIO Projekt-Webseite.", "OK oder 0: großen QR-Code öffnen."),
    "es": ("Web del proyecto / QR", "Muestra un código QR grande y legible que abre la web oficial del proyecto IPTV Dream / AIO.", "OK o 0: abrir el código QR grande."),
    "ar": ("موقع المشروع / QR", "يعرض رمز QR كبيراً وواضحاً يفتح الموقع الرسمي لمشروع IPTV Dream / AIO.", "OK أو 0: افتح رمز QR الكبير."),
    "ru": ("Сайт проекта / QR", "Показывает большой читаемый QR-код, ведущий на официальный сайт проекта IPTV Dream / AIO.", "OK или 0: открыть большой QR-код."),
}

PROJECT_MENU_LABELS = {
    "pl": "Strona projektu / QR",
    "en": "Project website / QR",
    "de": "Projekt-Webseite / QR",
    "es": "Web del proyecto / QR",
    "ar": "موقع المشروع / QR",
    "ru": "Сайт проекта / QR",
}

QUICK_LEGEND = {
    "pl": "1-4: źródła     5: ulubione     6: zarządzanie\n7: statystyki     8: WebIF     9: aktualizacje     0: strona / QR",
    "en": "1-4: sources     5: favorites     6: management\n7: statistics     8: WebIF     9: updates     0: website / QR",
    "de": "1-4: Quellen     5: Favoriten     6: Verwaltung\n7: Statistik     8: WebIF     9: Updates     0: Webseite / QR",
    "es": "1-4: fuentes     5: favoritos     6: gestión\n7: estadísticas     8: WebIF     9: actualizaciones     0: web / QR",
    "ar": "1-4: المصادر     5: المفضلة     6: الإدارة\n7: الإحصاءات     8: WebIF     9: التحديثات     0: الموقع / QR",
    "ru": "1-4: источники     5: избранное     6: управление\n7: статистика     8: WebIF     9: обновления     0: сайт / QR",
}

MAIN_STATUS = {
    "pl": "▲▼ wybór  •  OK uruchom  •  cyfry 1-9 skróty  •  0 strona projektu / QR",
    "en": "▲▼ select  •  OK run  •  keys 1-9 shortcuts  •  0 project website / QR",
    "de": "▲▼ wählen  •  OK starten  •  Tasten 1-9 Kurzbefehle  •  0 Projekt-Webseite / QR",
    "es": "▲▼ elegir  •  OK ejecutar  •  teclas 1-9 atajos  •  0 web del proyecto / QR",
    "ar": "▲▼ اختيار  •  OK تشغيل  •  الأرقام 1-9 اختصارات  •  0 موقع المشروع / QR",
    "ru": "▲▼ выбор  •  OK запуск  •  клавиши 1-9 быстрый выбор  •  0 сайт проекта / QR",
}

PROJECT_SCREEN_TEXT = {
    "pl": ("Strona projektu", "Zeskanuj kod telefonem, aby otworzyć stronę projektu.\nŻadne dane nie są wysyłane automatycznie."),
    "en": ("Project website", "Scan the code with your phone to open the project website.\nNo data is sent automatically."),
    "de": ("Projekt-Webseite", "Scanne den Code mit dem Telefon, um die Projekt-Webseite zu öffnen.\nEs werden keine Daten automatisch gesendet."),
    "es": ("Web del proyecto", "Escanea el código con el teléfono para abrir la web del proyecto.\nNo se envía ningún dato automáticamente."),
    "ar": ("موقع المشروع", "امسح الرمز بالهاتف لفتح موقع المشروع.\nلا يتم إرسال أي بيانات تلقائياً."),
    "ru": ("Сайт проекта", "Отсканируйте код телефоном, чтобы открыть сайт проекта.\nДанные автоматически не отправляются."),
}



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


class ProjectQRCodeScreen(Screen):
    """Large native Enigma2 QR screen. No browser or network action is triggered."""
    skin = """
    <screen name="ProjectQRCodeScreen" position="center,center" size="1040,600" title="IPTV Dream - Project website">
        <eLabel position="0,0" size="1040,600" backgroundColor="#06111d" zPosition="-10" />
        <eLabel position="18,12" size="1004,64" backgroundColor="#091a2b" zPosition="-8" />
        <eLabel position="18,12" size="1004,2" backgroundColor="#00d7ff" zPosition="-5" />
        <widget name="title" position="38,24" size="964,38" font="Regular;31" halign="center" valign="center" foregroundColor="#20d8ff" transparent="1" />

        <eLabel position="24,92" size="424,424" backgroundColor="#ffffff" zPosition="-7" />
        <widget name="qr" position="36,104" size="400,400" alphatest="on" scale="1" zPosition="2" />

        <eLabel position="470,92" size="546,424" backgroundColor="#091725" zPosition="-7" />
        <widget name="section" position="496,116" size="494,36" font="Regular;25" foregroundColor="#20d8ff" transparent="1" />
        <eLabel position="496,158" size="494,1" backgroundColor="#1e6c86" zPosition="-4" />
        <widget name="url" position="496,182" size="494,78" font="Regular;22" foregroundColor="#ffffff" valign="center" transparent="1" />
        <widget name="desc" position="496,286" size="494,116" font="Regular;20" foregroundColor="#d6e4ee" valign="top" transparent="1" />
        <widget name="multi" position="496,420" size="494,70" font="Regular;17" foregroundColor="#94b8ca" valign="top" transparent="1" />

        <eLabel position="24,536" size="250,46" backgroundColor="#9d1d28" zPosition="1" />
        <widget name="key_red" position="24,536" size="250,46" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" zPosition="2" />
        <widget name="footer" position="300,540" size="716,38" font="Regular;18" halign="right" valign="center" foregroundColor="#7fa8bc" transparent="1" />
    </screen>
    """

    def __init__(self, session, lang="en"):
        Screen.__init__(self, session)
        self.lang = normalize_lang(lang, "en")
        self["qr"] = Pixmap()
        self["title"] = Label("IPTV Dream v%s" % PLUGIN_VERSION)
        section, desc = PROJECT_SCREEN_TEXT.get(self.lang, PROJECT_SCREEN_TEXT["en"])
        self["section"] = Label(section)
        self["url"] = Label(PROJECT_URL)
        self["desc"] = Label(desc)
        self["multi"] = Label("PL: Zeskanuj kod telefonem.\nEN: Scan the code with your phone.\nDE: Scanne den Code mit dem Telefon.")
        try:
            back_text = _("back", self.lang)
        except Exception:
            back_text = "Back"
        self["key_red"] = Label(back_text)
        self["footer"] = Label("IPTV Dream • Paweł Pawełek")
        self["actions"] = ActionMap(["ColorActions", "OkCancelActions"], {
            "red": self.close,
            "cancel": self.close,
            "ok": self.close,
        }, -1)
        self.onLayoutFinish.append(self._load_qr)

    def _load_qr(self):
        try:
            from Tools.LoadPixmap import LoadPixmap
            path = os.path.join(os.path.dirname(__file__), "pic", "qrcode.png")
            pix = LoadPixmap(path=path)
            if pix is not None and getattr(self["qr"], "instance", None):
                self["qr"].instance.setPixmap(pix)
                self["qr"].show()
        except Exception:
            pass


class IPTVDreamV6(Screen):
    # AIO Panel-inspired native Enigma2 layout. It uses only built-in fonts and
    # widgets to keep compatibility across OpenATV/OpenPLi/OpenHDF/OpenViX skins.
    skin = """
    <screen name="IPTVDreamV6" position="center,center" size="1200,680" title="IPTV Dream v8.0.0">
        <eLabel position="0,0" size="1200,680" backgroundColor="#06111d" zPosition="-10" />

        <!-- Header: clean, centred, no e-mail/social clutter -->
        <eLabel position="16,10" size="1168,58" backgroundColor="#091a2b" zPosition="-8" />
        <eLabel position="16,10" size="1168,2" backgroundColor="#00d7ff" zPosition="-5" />
        <eLabel position="16,66" size="1168,1" backgroundColor="#174b61" zPosition="-5" />
        <widget name="title_label" position="180,19" size="840,38" font="Regular;34" halign="center" valign="center" foregroundColor="#20d8ff" transparent="1" />

        <!-- Compact runtime/status row -->
        <eLabel position="16,76" size="1168,31" backgroundColor="#081522" zPosition="-8" />
        <widget name="status_bar" position="34,80" size="1132,23" font="Regular;17" halign="center" valign="center" foregroundColor="#c8d8e2" transparent="1" />
        <widget name="progress_text" position="34,80" size="1132,19" font="Regular;16" halign="center" foregroundColor="#22f083" transparent="1" zPosition="3" />
        <widget name="progress_bar" position="34,101" size="1132,5" borderWidth="1" borderColor="#00d7ff" backgroundColor="#173142" zPosition="2" />

        <!-- Left navigation -->
        <eLabel position="16,117" size="520,340" backgroundColor="#071421" zPosition="-8" />
        <eLabel position="16,117" size="520,1" backgroundColor="#1c6078" zPosition="-5" />
        <widget name="menu_list" position="30,130" size="492,316" font="Regular;22" itemHeight="31" scrollbarMode="showOnDemand" enableWrapAround="1" transparent="1" foregroundColor="#edf4f8" foregroundColorSelected="#ffffff" backgroundColorSelected="#0b5a6b" />

        <!-- Right context information -->
        <eLabel position="552,117" size="632,340" backgroundColor="#081725" zPosition="-8" />
        <eLabel position="552,117" size="632,1" backgroundColor="#1c6078" zPosition="-5" />
        <widget name="info_title" position="576,132" size="584,38" font="Regular;25" halign="left" valign="center" foregroundColor="#20d8ff" transparent="1" />
        <eLabel position="576,177" size="584,1" backgroundColor="#1a6e89" zPosition="-4" />
        <widget name="info_text" position="576,190" size="584,248" font="Regular;17" halign="left" valign="top" foregroundColor="#d7e6ef" transparent="1" />

        <!-- Project website / real readable QR -->
        <eLabel position="16,467" size="520,104" backgroundColor="#071421" zPosition="-8" />
        <eLabel position="16,467" size="520,1" backgroundColor="#1c6078" zPosition="-5" />
        <widget name="qr" position="28,474" size="90,90" alphatest="on" scale="1" zPosition="2" />
        <widget name="support" position="132,476" size="388,40" font="Regular;17" foregroundColor="#20d8ff" valign="top" transparent="1" />
        <widget name="website" position="132,522" size="388,38" font="Regular;16" halign="left" valign="top" foregroundColor="#ffffff" transparent="1" />

        <!-- Quick navigation legend -->
        <eLabel position="552,467" size="632,104" backgroundColor="#071421" zPosition="-8" />
        <eLabel position="552,467" size="632,1" backgroundColor="#1c6078" zPosition="-5" />
        <widget name="quick_legend" position="576,484" size="584,70" font="Regular;17" foregroundColor="#9eb9c9" valign="center" transparent="1" />

        <!-- Coloured actions -->
        <eLabel position="16,582" size="278,40" backgroundColor="#a51d29" zPosition="1" />
        <eLabel position="309,582" size="278,40" backgroundColor="#128139" zPosition="1" />
        <eLabel position="602,582" size="278,40" backgroundColor="#b18b00" zPosition="1" />
        <eLabel position="895,582" size="289,40" backgroundColor="#1558ad" zPosition="1" />
        <widget name="key_red" position="16,582" size="278,40" font="Regular;18" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" zPosition="2" />
        <widget name="key_green" position="309,582" size="278,40" font="Regular;18" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" zPosition="2" />
        <widget name="key_yellow" position="602,582" size="278,40" font="Regular;18" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" zPosition="2" />
        <widget name="key_blue" position="895,582" size="289,40" font="Regular;18" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" zPosition="2" />

        <!-- Dynamic help: PL / EN / DE for the highlighted function -->
        <eLabel position="16,632" size="1168,43" backgroundColor="#081522" zPosition="-8" />
        <eLabel position="16,632" size="1168,1" backgroundColor="#1c6078" zPosition="-5" />
        <widget name="hint" position="34,637" size="1132,33" font="Regular;15" foregroundColor="#b8ccd8" valign="center" transparent="1" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        try:
            self.setTitle("IPTV Dream v%s" % PLUGIN_VERSION)
        except Exception:
            pass

        # Initial language: system language if supported, otherwise English.
        # Plugin config can keep manual language or AUTO mode.
        self.language_mode = "auto"
        self.lang = _detect_system_language()

        # UI
        self["title_label"] = Label(_("title", self.lang))
        self["menu_list"] = MenuList([])
        self["info_title"] = Label("")
        self["info_text"] = Label("")
        self["status_bar"] = Label("")
        self["progress_bar"] = ProgressBar()
        try:
            self["progress_bar"].setRange((0, 100))
        except Exception:
            pass
        self["progress_text"] = Label("")
        self["key_red"] = Label(_("exit", self.lang))
        self["key_green"] = Label(_("check_upd", self.lang))
        self["key_yellow"] = Label(_("epg_install", self.lang))
        self["key_blue"] = Label(_("export", self.lang))

        self["qr"] = Pixmap()
        self["support"] = Label("")
        self["website"] = Label(PROJECT_URL)
        self["quick_legend"] = Label("")
        self["hint"] = Label("")


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
        self.cfg.setdefault('language', 'auto')
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

        # Prefer language from plugin config; AUTO follows Enigma2 system language.
        try:
            cfg_lang = str(self.cfg.get('language', 'auto')).strip().lower()
            if cfg_lang == 'auto':
                self.language_mode = 'auto'
                self.lang = _detect_system_language()
            elif cfg_lang in SUPPORTED_LANGS:
                self.language_mode = cfg_lang
                self.lang = cfg_lang
            else:
                self.language_mode = 'auto'
                self.lang = _detect_system_language()
        except Exception:
            self.language_mode = 'auto'
            self.lang = _detect_system_language()

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
        try:
            saved_picon_dir = (self.cfg.get('picon_save_dir') or '').strip()
            if saved_picon_dir:
                self.picons.picon_dir = saved_picon_dir
        except Exception:
            pass
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
                '0': self.openProjectWebsite,
            },
            -1,
        )

        # Context help follows the highlighted item immediately.
        try:
            if self._onMenuSelectionChanged not in self["menu_list"].onSelectionChanged:
                self["menu_list"].onSelectionChanged.append(self._onMenuSelectionChanged)
        except Exception:
            pass

        # inicjalizacja UI po zbudowaniu ekranu (pixmap, menu)
        self.onLayoutFinish.append(self._init_ui)

    def _apply_language_to_static_ui(self):
        """Refresh static labels after a language change."""
        try:
            self["title_label"].setText("IPTV Dream v%s" % PLUGIN_VERSION)
            self["key_red"].setText(_("exit", self.lang))
            self["key_green"].setText(_("check_upd", self.lang))
            self["key_yellow"].setText(_("epg_install", self.lang))
            self["key_blue"].setText(_("export", self.lang))
        except Exception:
            pass

        try:
            label, scan = PROJECT_LABELS.get(self.lang, PROJECT_LABELS["en"])
            self["support"].setText("%s\n%s" % (label, scan))
            self["website"].setText(PROJECT_URL)
            self["quick_legend"].setText(QUICK_LEGEND.get(self.lang, QUICK_LEGEND["en"]))
        except Exception:
            pass

        try:
            self._onMenuSelectionChanged()
        except Exception:
            generic = GENERIC_HELP.get(self.lang, GENERIC_HELP["en"])
            try:
                self["hint"].setText(generic[2])
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
            self.cfg["language"] = getattr(self, "language_mode", self.lang)
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

    def _help_for_action(self, action):
        key = action[0] if isinstance(action, tuple) and action else action
        if key == "project":
            return PROJECT_HELP.get(self.lang, PROJECT_HELP["en"])
        lang_map = ACTION_HELP.get(self.lang, ACTION_HELP.get("en", {}))
        data = lang_map.get(key)
        if data:
            return data

        # Dynamic list items get useful information without hard-coded provider text.
        payload = action[1] if isinstance(action, tuple) and len(action) > 1 else None
        if key in ("fav_group", "pl_group"):
            group_name = str(payload or "")
            if self.lang == "pl": return ("Grupa", "Wybrana grupa: %s" % group_name, "OK: otwórz grupę.")
            if self.lang == "de": return ("Gruppe", "Ausgewählte Gruppe: %s" % group_name, "OK: Gruppe öffnen.")
            if self.lang == "es": return ("Grupo", "Grupo seleccionado: %s" % group_name, "OK: abrir grupo.")
            if self.lang == "ar": return ("المجموعة", "المجموعة المحددة: %s" % group_name, "OK: افتح المجموعة.")
            if self.lang == "ru": return ("Группа", "Выбранная группа: %s" % group_name, "OK: открыть группу.")
            return ("Group", "Selected group: %s" % group_name, "OK: open group.")
        if key in ("fav_item", "pl_item") and isinstance(payload, dict):
            title = payload.get("title") or payload.get("name") or ""
            group = payload.get("group") or ""
            if self.lang == "pl": return ("Kanał", "%s\nGrupa: %s" % (title, group), "OK: wybierz kanał.")
            if self.lang == "de": return ("Sender", "%s\nGruppe: %s" % (title, group), "OK: Sender wählen.")
            if self.lang == "es": return ("Canal", "%s\nGrupo: %s" % (title, group), "OK: seleccionar canal.")
            if self.lang == "ar": return ("القناة", "%s\nالمجموعة: %s" % (title, group), "OK: اختر القناة.")
            if self.lang == "ru": return ("Канал", "%s\nГруппа: %s" % (title, group), "OK: выбрать канал.")
            return ("Channel", "%s\nGroup: %s" % (title, group), "OK: select channel.")
        if key == "mac_pick" and isinstance(payload, dict):
            host = (payload.get("host") or payload.get("url") or "").strip()
            if self.lang == "pl": return ("Portal MAC", "Wybrany portal: %s" % host, "OK: wybierz rodzaj treści i połącz.")
            if self.lang == "de": return ("MAC-Portal", "Gewähltes Portal: %s" % host, "OK: Inhaltstyp wählen und verbinden.")
            if self.lang == "es": return ("Portal MAC", "Portal seleccionado: %s" % host, "OK: elige contenido y conecta.")
            if self.lang == "ar": return ("بوابة MAC", "البوابة المحددة: %s" % host, "OK: اختر نوع المحتوى واتصل.")
            if self.lang == "ru": return ("MAC-портал", "Выбранный портал: %s" % host, "OK: выберите тип контента.")
            return ("MAC Portal", "Selected portal: %s" % host, "OK: choose content type and connect.")

        if key in ("back_main", "back_playlist", "back_fav_groups", "pl_groups_back"):
            if self.lang == "pl": return ("Powrót", "Wraca do poprzedniego ekranu lub menu głównego.", "OK/EXIT: wróć.")
            if self.lang == "de": return ("Zurück", "Kehrt zum vorherigen Bildschirm oder Hauptmenü zurück.", "OK/EXIT: zurück.")
            if self.lang == "es": return ("Volver", "Vuelve a la pantalla anterior o al menú principal.", "OK/EXIT: volver.")
            if self.lang == "ar": return ("رجوع", "العودة إلى الشاشة السابقة أو القائمة الرئيسية.", "OK/EXIT: رجوع.")
            if self.lang == "ru": return ("Назад", "Возвращает на предыдущий экран или в главное меню.", "OK/EXIT: назад.")
            return ("Back", "Returns to the previous screen or main menu.", "OK/EXIT: back.")

        return GENERIC_HELP.get(self.lang, GENERIC_HELP["en"])

    def _main_multilingual_help(self, action):
        """PL/EN/DE explanation used on the main screen, matching the AIO-style mock-up."""
        key = action[0] if isinstance(action, tuple) and action else action
        if key == "project":
            tables = PROJECT_HELP
        else:
            tables = ACTION_HELP
        try:
            pl = tables.get("pl", {}).get(key) if tables is ACTION_HELP else tables.get("pl")
            en = tables.get("en", {}).get(key) if tables is ACTION_HELP else tables.get("en")
            de = tables.get("de", {}).get(key) if tables is ACTION_HELP else tables.get("de")
        except Exception:
            pl = en = de = None
        if not (pl and en and de):
            return None
        current = self._help_for_action(action)
        title = current[0]
        text = "PL  %s\n\nEN  %s\n\nDE  %s" % (pl[1], en[1], de[1])
        hint = "PL: %s   |   EN: %s   |   DE: %s" % (pl[2], en[2], de[2])
        return title, text, hint

    def _onMenuSelectionChanged(self):
        """Update the information panel when the highlight moves."""
        try:
            cur = self["menu_list"].getCurrent()
            action = cur[1] if cur and len(cur) > 1 else None
        except Exception:
            action = None
        if getattr(self, "menu_context", "main") == "main":
            data = self._main_multilingual_help(action)
        else:
            data = None
        title, text, hint = data if data else self._help_for_action(action)
        # Add current runtime values where useful.
        key = action[0] if isinstance(action, tuple) and action else action
        if key == "webif":
            try:
                text += "\nhttp://%s:%d  [%s]" % (get_lan_ip(), WEBIF_PORT, "ON" if self.webif_enabled else "OFF")
            except Exception:
                pass
        elif key == "stype":
            try:
                text += "\nCurrent / bieżący: %s" % self.service_type
            except Exception:
                pass
        self.updateInfoPanel(title, text)
        try:
            self["hint"].setText(hint)
        except Exception:
            pass

    def _init_ui(self):
        """Uzupełnia UI po utworzeniu ekranu (menu + QR) i uruchamia WebIF jeśli włączone."""
        # QR strony projektu. Skin ma scale="1", więc Enigma2 pokazuje cały kod,
        # a nie jego przycięty lewy-górny fragment.
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
                self.webif_enabled = bool(start_web_server(WEBIF_PORT, self.onWebIfData))
            except Exception:
                self.webif_enabled = False
            if not self.webif_enabled:
                self.cfg["webif_enabled"] = False
                self._save_cfg()

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
        """Wybór głównych pozycji klawiszami 1-9; klawisz 0 otwiera stronę projektu / QR."""
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
        num_reset = "\\c00ffffff"
        num_colors = {
            1: "\\c0000ff00", 2: "\\c0000ff00", 3: "\\c0000ff00", 4: "\\c0000ff00",
            0: "\\c0000d7ff", 5: "\\c00a0a0a0", 6: "\\c00b000ff", 7: "\\c00ff7a00", 8: "\\c000080ff", 9: "\\c00ff0000",
        }
        def N(i):
            return "%s%d%s" % (num_colors.get(i, "\\c00ffffff"), i, num_reset)

        lbl1 = _("menu_m3u_url", self.lang)
        lbl2 = _("menu_m3u_file", self.lang)
        lbl3 = _("menu_xtream", self.lang)
        lbl4 = _("menu_mac", self.lang)
        lbl5 = _("menu_favorites", self.lang)
        lbl6 = _("menu_management", self.lang)
        lbl7 = _("menu_stats", self.lang)
        lbl8 = (_("menu_webif", self.lang) % (webif_txt, "")).rstrip()
        lbl9 = _("menu_updates", self.lang)
        lbl0 = PROJECT_MENU_LABELS.get(self.lang, PROJECT_MENU_LABELS["en"])

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
            ("%s  %s" % (N(0), lbl0), "project"),
        ]
        self.menu_context = "main"
        self["menu_list"].setList(items)
        self._onMenuSelectionChanged()

        self["status_bar"].setText(MAIN_STATUS.get(self.lang, MAIN_STATUS["en"]))
        self._onMenuSelectionChanged()


    def _language_label(self):
        try:
            mode = getattr(self, 'language_mode', 'auto')
            if mode == 'auto':
                return _("language_auto_label", self.lang) % _language_display_name(_detect_system_language())
            return _("language_manual_label", self.lang) % _language_display_name(mode)
        except Exception:
            return self.lang.upper()

    def openProjectWebsite(self):
        """Open a large, readable QR code screen. It does not send any data."""
        try:
            self.session.open(ProjectQRCodeScreen, self.lang)
        except Exception as e:
            self.session.open(MessageBox, "QR error: %s" % e, MessageBox.TYPE_ERROR)

    def openLanguageChoice(self):
        items = [
            (_("lang_auto", self.lang) + " (%s)" % _language_display_name(_detect_system_language()), "auto"),
            (_("lang_polish", self.lang), "pl"),
            (_("lang_english", self.lang), "en"),
            (_("lang_german", self.lang), "de"),
            (_("lang_arabic", self.lang), "ar"),
            (_("lang_spanish", self.lang), "es"),
            (_("lang_russian", self.lang), "ru"),
        ]
        self.session.openWithCallback(self.onLanguageChoice, ChoiceBox, title=_("select_language", self.lang), list=items)

    def onLanguageChoice(self, choice):
        if not choice:
            return
        mode = choice[1]
        if mode == 'auto':
            self.language_mode = 'auto'
            self.lang = _detect_system_language()
        elif mode in SUPPORTED_LANGS:
            self.language_mode = mode
            self.lang = mode
        else:
            self.language_mode = 'auto'
            self.lang = _detect_system_language()
        self.cfg["language"] = self.language_mode
        self._save_cfg()
        self._apply_language_to_static_ui()
        try:
            self.updateInfoPanel(_("Witamy", self.lang), _("welcome_body", self.lang) % PLUGIN_VERSION)
        except Exception:
            pass
        try:
            self.session.open(MessageBox, _("language_saved", self.lang) % self._language_label(), MessageBox.TYPE_INFO, timeout=2)
        except Exception:
            pass
        return self.showManagementMenu()

    def showManagementMenu(self):
        self.menu_context = "manage"

        dbg_on = bool(self.cfg.get('debug', False))
        st_title = _("management", self.lang)
        back_lbl = _("back", self.lang)
        cache_lbl = _("clear_cache", self.lang)
        hist_lbl = _("clear_history", self.lang)
        hint_txt = _("management_hint", self.lang)
        lang_lbl = _("language_menu_label", self.lang) % self._language_label()
        stype_lbl = _("service_type_label", self.lang) % self.service_type
        epg_lbl = _("epg_url_label", self.lang)
        dbg_lbl = _("debug_label", self.lang) % ("ON" if dbg_on else "OFF")
        log_lbl = _("show_log_label", self.lang)
        logc_lbl = _("clear_log_label", self.lang)
        delbq_lbl = _("delete_bouquets_label", self.lang)

        items = [
            (lang_lbl, "lang"),
            (stype_lbl, "stype"),
            (epg_lbl, "epgurl"),
            (dbg_lbl, "debug_toggle"),
            (log_lbl, "show_log"),
            (logc_lbl, "clear_log"),
            (cache_lbl, "clear_cache"),
            (hist_lbl, "clear_history"),
            (delbq_lbl, "delete_bouquets"),
            (back_lbl, "back_main"),
        ]
        self["menu_list"].setList(items)
        self._onMenuSelectionChanged()
        self["status_bar"].setText(st_title)
        self._onMenuSelectionChanged()

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
        self._onMenuSelectionChanged()
        self["status_bar"].setText(_("Playlista: %s", self.lang) % (self.playlist_name or ""))
        self._onMenuSelectionChanged()

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
        self._onMenuSelectionChanged()
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
        self._onMenuSelectionChanged()
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
            if action[0] == "pl_group":
                return self.showPlaylistGroupItems(action[1])
            if action[0] == "pl_groups_back":
                return self.showPlaylistGroups()
            if action[0] == "pl_item":
                ch = action[1] or {}
                title = ch.get("title", "")
                group = ch.get("group", "")
                url = ch.get("url", "")
                self.updateInfoPanel(title or _("Kanał", self.lang), "%s\n%s" % (group, url))
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
        if action == "project":
            return self.openProjectWebsite()

        if action == "lang":
            return self.openLanguageChoice()

        if action == "stype":
            self.service_type = 5002 if self.service_type == 4097 else 4097
            self.cfg["service_type"] = self.service_type
            self._save_cfg()
            self.session.open(MessageBox, (_("Typ serwisu: %d", self.lang) % self.service_type), MessageBox.TYPE_INFO, timeout=2)
            return self.showManagementMenu()

        if action == "epgurl":
            cur = self.cfg.get(EPG_URL_KEY, "http://")
            title = _('Wklej URL EPG:', self.lang)
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
        if action == "delete_bouquets":
            return self.deleteDreamBouquets()
        if action == "back_main":
            return self.showMainMenu()
        if action == "back_playlist":
            return self.showPlaylistMenu()
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
        try:
            self["progress_bar"].setRange((0, 100))
        except Exception:
            pass
        self["progress_bar"].setValue(0)
        self["progress_text"].setText("0%")
        self["progress_bar"].show()
        self["progress_text"].show()
        if self.loading_timer:
            try:
                tmo = int(timeout_ms) if timeout_ms is not None else int(LOAD_TIMEOUT_MS)
                try:
                    self.loading_timer.start(tmo, True)
                except TypeError:
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
        if not getattr(self, "is_loading", False):
            return
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
        url = (url or "").strip()
        if not url:
            return

        # Accept formats like: URL|User-Agent=...&Referer=...
        raw_input = url
        headers = {}
        try:
            if '|' in url:
                url, opt = url.split('|', 1)
                url = url.strip()
                opt = opt.strip()
                for kv in re.split(r"[&;]", opt):
                    if '=' not in kv:
                        continue
                    k, v = kv.split('=', 1)
                    k = (k or '').strip().lower()
                    v = (v or '').strip()
                    if not v:
                        continue
                    if k in ('user-agent', 'useragent', 'ua'):
                        headers['User-Agent'] = v
                    elif k in ('referer', 'ref'):
                        headers['Referer'] = v
                    elif k == 'origin':
                        headers['Origin'] = v
        except Exception:
            headers = {}

        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url

        self._m3u_url_headers = headers
        # Store the raw input so refresh keeps any |options
        # (load uses normalized url + extracted headers)

        self.cfg["last_url"] = raw_input
        self.last_source = {"type": "m3u_url", "value": raw_input}
        self.cfg["last_source"] = self.last_source
        self._save_cfg()

        self.startLoading(_("Pobieranie playlisty (URL) ...", self.lang))

        def _load():
            # PlaylistLoader ma cache i parsowanie
            content = self.loader.load_m3u_url(url, progress_callback=self.updateProgress, headers=getattr(self, "_m3u_url_headers", None))
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
            base = host if host.startswith(("http://", "https://")) else "http://%s" % host
            base = base.rstrip("/")
            query = urlencode({"username": user, "password": pwd, "type": "m3u_plus", "output": "ts"})
            url = "%s/get.php?%s" % (base, query)
            r = http_get(url, timeout=(int(self.cfg.get('net_timeout_connect',7)), int(self.cfg.get('net_timeout_read',30))), retries=int(self.cfg.get('net_retries',2)), backoff=float(self.cfg.get('net_backoff',0.8)), verify=bool(self.cfg.get('ssl_verify', False)), debug=bool(self.cfg.get('debug', False)), log_file=self.cfg.get('log_file','/tmp/iptvdream.log'))
            return r.content

        def _done(data, err):
            if err:
                self.onPlaylistLoaded(None, None, err)
                return
            playlist = self.loader.parse_m3u_content(data, progress_callback=self.updateProgress, content_filter=content_type)
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
            items.append(("🔑 %s | %s" % (host, (mac or "").upper()), ("mac_pick", p)))
        items.append((_("🗑️ Usuń portal", self.lang), "mac_delete"))
        items.append((_("⬅️ Powrót", self.lang), "back_main"))
        self.menu_context = "mac_menu"
        self["menu_list"].setList(items)
        self._onMenuSelectionChanged()
        self["status_bar"].setText(_("MAC Portal", self.lang))

    def _mac_menu_dispatch(self, action):
        # helper unused: kept for readability
        return

    def addMacPortal(self):
        self.session.openWithCallback(
            self.onMacJson,
            VirtualKeyBoard,
            title=_("Wklej JSON: {", self.lang).rstrip("{").strip(),
            text='{"host":"...","mac":"..."}'
        )

    def onMacJson(self, txt):
        if not txt:
            return
        try:
            data = parse_json_flexible_mac(txt)
            if isinstance(data, list):
                data = data[0] if data else {}
            host = ((data or {}).get("host") or (data or {}).get("url") or (data or {}).get("portal") or "").strip()
            mac = ((data or {}).get("mac") or (data or {}).get("mac_address") or "").strip()
            if not host or not mac:
                example = "\n\nPrzykład:\n{\"host\":\"http://portal/c\",\"mac\":\"00:11:22:33:44:55\"}"
                self.session.open(MessageBox, _("Brak host/mac w JSON.", self.lang) + example, MessageBox.TYPE_ERROR)
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
        opts = [("LIVE", 'live'), ("VOD", 'vod'), ("SERIALE", 'series'), (_("mac_adult", self.lang), 'adult')]
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
            msg = (_("Pobieranie z MAC Portal ...", self.lang) + _("mac_large_library", self.lang))
        self.startLoading(msg, timeout_ms=tmo)

        def _load():
            # tools/mac_portal.py w repozytorium przyjmuje (host, mac) bez progress_callback.
            # Progress pokazujemy na poziomie GUI (start/stop + status), a parsowanie nie blokuje GUI.
            playlist = parse_mac_playlist(host, mac, content_type=content_type, progress_callback=self.updateProgress)
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
        suffix = 'LIVE' if content_type == 'live' else ('VOD' if content_type == 'vod' else ('ADULT' if content_type == 'adult' else 'SERIES'))
        pl_name = 'MAC-%s-%s' % (_mk_id(), suffix)
        run_in_thread(_load, lambda res, err: self.onPlaylistLoaded(res, pl_name, err))

    def deleteMacPortal(self):
        portals = load_mac_json() or []
        if not portals:
            self.session.open(MessageBox, _("Brak zapisanych portali.", self.lang), MessageBox.TYPE_INFO)
            return
        items = []
        for idx, p in enumerate(portals):
            items.append((_("Usuń: %s | %s", self.lang) % (p.get("host", ""), (p.get("mac", "") or "").upper()), idx))
        self.session.openWithCallback(self.onMacDeletePicked, ChoiceBox, title=_("Wybierz portal do usunięcia", self.lang), list=items)

    def onMacDeletePicked(self, choice):
        if not choice:
            return
        idx = choice[1]
        portals = load_mac_json() or []
        if 0 <= idx < len(portals):
            portals.pop(idx)
            save_mac_json(portals)
            if not portals:
                clear_mac_backups()
            self.session.open(MessageBox, _("Usunięto portal.", self.lang), MessageBox.TYPE_INFO, timeout=3)
        self.openMacMenu()

    # ---------- WebIF ----------

    def toggleWebIf(self):
        try:
            if self.webif_enabled:
                self.webif_enabled = not bool(stop_web_server())
            else:
                self.webif_enabled = bool(start_web_server(WEBIF_PORT, self.onWebIfData))
                if not self.webif_enabled:
                    self.session.open(MessageBox, _("Nie udało się uruchomić WebIF. Port może być zajęty.", self.lang), MessageBox.TYPE_ERROR, timeout=4)

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
                if mode not in ('live','vod','series','adult'):
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
        # Ignore late worker callbacks after user cancel/watchdog timeout.
        if not getattr(self, "is_loading", False):
            return
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
        self._onMenuSelectionChanged()
        self["status_bar"].setText(_("Grupy", self.lang))

    def showPlaylistGroupItems(self, group_name):
        chs = self._playlist_groups_cache.get(group_name, [])
        self.menu_context = "playlist_group_items"
        items = []
        for ch in chs[:400]:
            items.append(("• %s" % ch.get("title", "Bez nazwy" if self.lang == "pl" else "No name"), ("pl_item", ch)))
        items.append((_("⬅️ Powrót", self.lang), ("pl_groups_back", None)))
        self["menu_list"].setList(items)
        self._onMenuSelectionChanged()
        self["status_bar"].setText(group_name)

    def addPlaylistToFavorites(self):
        if not self.current_playlist:
            return

        def _ask_group(answer):
            # Nie używamy nazwy argumentu "_", bo zasłania funkcję tłumaczeń i powoduje GSOD:
            # TypeError: 'bool' object is not callable
            if not answer:
                return
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

        # --- wybór miejsca zapisu picon ---
        def _list_destinations():
            dests = []
            # 1) tuner (domyślnie)
            dests.append((_('picon_receiver', self.lang), "/usr/share/enigma2/picon"))

            # 2) wykryj nośniki (/media/*) i zaproponuj /picon
            try:
                if os.path.isdir('/media'):
                    for n in sorted(os.listdir('/media')):
                        base = os.path.join('/media', n)
                        # pomiń śmieci
                        if n in ('.', '..'):
                            continue
                        if not os.path.isdir(base):
                            continue
                        # zwykle nośniki są zapisywalne
                        if not os.access(base, os.W_OK):
                            continue
                        pdir = os.path.join(base, 'picon')
                        # ładny opis
                        label = _("picon_media", self.lang) % (n, pdir)
                        dests.append((label, pdir))
            except Exception:
                pass

            # 3) dodatkowe typowe ścieżki
            for base in ('/mnt',):
                try:
                    if os.path.isdir(base) and os.access(base, os.W_OK):
                        pdir = os.path.join(base, 'picon')
                        dests.append(("Nośnik: %s" % pdir, pdir))
                except Exception:
                    pass

            # unikalne
            uniq = []
            seen = set()
            for lbl, p in dests:
                if p not in seen:
                    seen.add(p)
                    uniq.append((lbl, p))
            return uniq

        def _on_dest(choice):
            if not choice:
                return
            pdir = choice[1]
            if not pdir:
                return
            try:
                os.makedirs(pdir, exist_ok=True)
            except Exception:
                pass

            # ustaw na menadżerze i zapamiętaj
            try:
                self.picons.picon_dir = pdir
                try:
                    os.makedirs(self.picons.picon_dir, exist_ok=True)
                except Exception:
                    pass
            except Exception:
                pass

            try:
                self.cfg['picon_save_dir'] = pdir
                self._save_cfg()
            except Exception:
                pass

            self.startLoading(_("Pobieranie picon ...", self.lang) + "\n" + pdir)

            _start_download()

        def _start_download():
            # istniejąca logika pobierania (w wątku)
            def _work():
                """Pobiera pikony szybciej (wielowątkowo) i aktualizuje progress."""
                items = []
                seen = set()
                for ch in (self.current_playlist or []):
                    title = (ch.get("title") or ch.get("name") or "").strip()
                    purl = (ch.get("tvg-logo") or ch.get("tvg_logo") or ch.get("logo") or "").strip()
                    if title and purl:
                        key = (purl, title.lower())
                        if key not in seen:
                            seen.add(key)
                            items.append((purl, title))

                total = len(items)
                if total <= 0:
                    return 0

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

        # jeśli jest zapamiętana ścieżka, ustaw ją jako domyślny wybór
        try:
            last = (self.cfg.get('picon_save_dir') or '').strip()
        except Exception:
            last = ''
        dests = _list_destinations()
        if last and os.path.isabs(last):
            # dołóż "ostatnio używane" na górę
            dests = [(_("picon_last", self.lang) % last, last)] + [d for d in dests if d[1] != last]

        self.session.openWithCallback(
            _on_dest,
            ChoiceBox,
            title=_("select_picon_location", self.lang),
            list=dests
        )

        return

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
        items.append((_("language_menu_label", self.lang) % self._language_label(), "lang"))
        items.append((_("service_type_label", self.lang) % self.service_type, "stype"))
        items.append((_("epg_url_label", self.lang), "epgurl"))
        items.append((_("back", self.lang), "back"))

        self.session.openWithCallback(self.onSettingsChoice, ChoiceBox, title=_("Ustawienia", self.lang), list=items)

    def onSettingsChoice(self, choice):
        if not choice:
            return
        act = choice[1]
        if act == "lang":
            return self.openLanguageChoice()
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

    
    def deleteDreamBouquets(self):
        """Bulk-delete bouquets created by IPTV Dream (by #NAME base)."""
        try:
            import glob
            bq_files = sorted(glob.glob("/etc/enigma2/userbouquet.iptv_dream_*.tv"))
        except Exception:
            bq_files = []

        if not bq_files:
            self.session.open(MessageBox, _("Brak bukietów IPTV Dream do usunięcia.", self.lang) if self.lang=="pl" else _("No IPTV Dream bouquets to delete.", self.lang), MessageBox.TYPE_INFO)
            return

        groups = {}
        for fp in bq_files:
            base = None
            try:
                with open(fp, "r", errors="ignore") as f:
                    first = (f.readline() or "").strip()
                if first.startswith("#NAME"):
                    nm = first.replace("#NAME", "", 1).strip()
                    base = nm.split(" - ", 1)[0].strip() if nm else None
            except Exception:
                base = None
            if not base:
                base = "IPTVDream"
            groups.setdefault(base, []).append(fp)

        choices = []
        for base, fps in sorted(groups.items(), key=lambda x: x[0].lower()):
            choices.append(("%s (%d)" % (base, len(fps)), base))

        def _picked(choice):
            if not choice:
                return
            base = choice[1]
            fps = groups.get(base, [])
            if not fps:
                return

            def _confirm(yes):
                if not yes:
                    return
                removed = 0
                # Remove entries from bouquets.tv and delete files
                try:
                    idx_path = "/etc/enigma2/bouquets.tv"
                    idx_lines = []
                    if os.path.exists(idx_path):
                        with open(idx_path, "r", errors="ignore") as f:
                            idx_lines = f.readlines()
                    # Build set of filenames
                    fnames = set([os.path.basename(x) for x in fps])
                    new_lines = []
                    for ln in idx_lines:
                        keep = True
                        for fn in fnames:
                            if ('FROM BOUQUET "%s"' % fn) in ln:
                                keep = False
                                break
                        if keep:
                            new_lines.append(ln)
                    if new_lines != idx_lines:
                        with open(idx_path, "w") as f:
                            f.writelines(new_lines)
                except Exception:
                    pass

                for fp in fps:
                    try:
                        os.remove(fp)
                        removed += 1
                    except Exception:
                        pass

                # Reload bouquets
                try:
                    if eDVBDB:
                        eDVBDB.getInstance().reloadBouquets()
                        eDVBDB.getInstance().reloadServicelist()
                except Exception:
                    pass

                msg = ("Usunięto %d bukietów." % removed) if self.lang=="pl" else ("Deleted %d bouquets." % removed)
                self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, timeout=4)

            prompt = ("Usunąć bukiety dla: %s ?" % base) if self.lang=="pl" else ("Delete bouquets for: %s ?" % base)
            self.session.openWithCallback(_confirm, MessageBox, prompt, MessageBox.TYPE_YESNO)

        self.session.openWithCallback(_picked, ChoiceBox, title=_("Wybierz zestaw bukietów", self.lang) if self.lang=="pl" else _("Select bouquet set", self.lang), list=choices)

    def clearCache(self):
        try:
            for cache_dir in (CACHE_DIR, LEGACY_CACHE_DIR):
                if os.path.exists(cache_dir):
                    for root, dirs, files in os.walk(cache_dir, topdown=False):
                        for fname in files:
                            try:
                                os.remove(os.path.join(root, fname))
                            except Exception:
                                pass
                        for dname in dirs:
                            try:
                                os.rmdir(os.path.join(root, dname))
                            except Exception:
                                pass
                if cache_dir == CACHE_DIR:
                    _safe_mkdir(cache_dir)
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

        # Budujemy listę kanałów tylko z zaznaczonych grup.
        final_list = []
        for k in selected_keys:
            try:
                final_list.extend(self.export_groups.get(k, []))
            except Exception:
                pass

        if not final_list:
            self.session.open(MessageBox, _("Nie wybrano kanałów do eksportu.", self.lang), MessageBox.TYPE_INFO, timeout=3)
            return

        # v7.0.0: szybki eksport jak wcześniej — bez ciężkiego paska 0%, bez EPG/Picon w tej samej operacji.
        try:
            self["progress_bar"].hide()
            self["progress_text"].hide()
        except Exception:
            pass
        try:
            self["status_bar"].setText(_("exporting_bouquets", self.lang))
        except Exception:
            pass

        try:
            total_bq, total_ch = export_bouquets(final_list, self.playlist_name, service_type=str(self.service_type))
        except Exception as e:
            try:
                self["status_bar"].setText("Export error")
            except Exception:
                pass
            self.session.open(MessageBox, "Export error: %s" % e, MessageBox.TYPE_ERROR)
            return

        try:
            if eDVBDB:
                eDVBDB.getInstance().reloadBouquets()
                eDVBDB.getInstance().reloadServicelist()
        except Exception:
            pass

        try:
            self["status_bar"].setText(_("exported_channels_bouquets", self.lang) % (total_ch, total_bq))
        except Exception:
            pass
        self.session.open(MessageBox, _("exported_channels_bouquets", self.lang) % (total_ch, total_bq), MessageBox.TYPE_INFO)

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
    """Backward-compatible wrapper around the production M3U parser."""
    try:
        return PlaylistLoader().parse_m3u_content(data, content_filter=content_filter)
    except Exception:
        return []
