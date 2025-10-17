# -*- coding: utf-8 -*-
from Screens.Screen       import Screen
from Screens.MessageBox   import MessageBox
from Screens.ChoiceBox    import ChoiceBox
from Components.ActionMap import ActionMap
from Components.Label     import Label
from Components.Language  import language
from .export              import export_bouquets
from .vkb_input           import VKInputBox
from .file_pick           import M3UFilePick
from .tools.mac_portal    import (load_mac_json, save_mac_json, parse_mac_playlist)
from .tools.updater       import check_update, do_update
from .tools.lang          import _
from .tools.xtream_one_window import XtreamOneWindow
from .tools.bouquet_picker    import BouquetPicker
from .tools.epg_picon         import fetch_epg_for_playlist, download_picon_url
import os, json, urllib.request, re, threading
from enigma import eTimer

# === Helper do uruchamiania zadań w tle, aby uniknąć blokowania UI ===
def run_in_thread(blocking_func, on_done_callback, *args, **kwargs):
    """
    Uruchamia blokującą funkcję w osobnym wątku.
    Po zakończeniu, wywołuje `on_done_callback` w głównym wątku Enigmy.
    Callback otrzymuje dwa argumenty: (wynik, błąd).
    """
    def thread_target():
        try:
            result = blocking_func(*args, **kwargs)
            # Używamy eTimer, aby bezpiecznie wrócić do głównego wątku Enigmy
            eTimer().start(0, True, lambda: on_done_callback(result, None))
        except Exception as e:
            eTimer().start(0, True, lambda: on_done_callback(None, e))

    thread = threading.Thread(target=thread_target)
    thread.daemon = True
    thread.start()

PROFILES      = "/etc/enigma2/iptvdream_profiles.json"
MY_LINKS_FILE = "/etc/enigma2/iptvdream_mylinks.json"
USER_M3U_FILE = "/etc/enigma2/iptvdream_user_m3u.json"
PLUGIN_VERSION = "2.3" # Ulepszona wersja

# ---------- pomocnicze ----------
# === Ulepszony parser M3U, który poprawnie odczytuje group-title i tvg-logo ===
def parse_m3u_bytes_improved(data):
    out = []
    current_attrs = {}

    for line in data.decode("utf-8", "ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#EXTM3U"):
            continue

        if line.startswith("#EXTINF"):
            parts = line.split(',', 1)
            title = parts[1] if len(parts) > 1 else "No Title"
            
            group_match = re.search(r'group-title="([^"]+)"', line)
            logo_match = re.search(r'tvg-logo="([^"]+)"', line)
            
            current_attrs = {
                "title": title.strip(),
                "group": group_match.group(1).strip() if group_match else "",
                "logo": logo_match.group(1).strip() if logo_match else ""
            }

        elif "://" in line:
            if "title" in current_attrs:
                channel_data = {
                    "title": current_attrs.get("title"),
                    "url": line,
                    "group": current_attrs.get("group"),
                    "logo": current_attrs.get("logo", ""),
                    "epg": ""
                }
                out.append(channel_data)
                current_attrs = {} # Reset po dodaniu kanału
            else:
                # Fallback dla linków bez #EXTINF
                out.append({
                    "title": line.split('/')[-1],
                    "url": line,
                    "group": "Inne",
                    "logo": "",
                    "epg": ""
                })
    return out

def load_profiles():
    try:
        with open(PROFILES, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_profiles(data):
    with open(PROFILES, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ---------- główne okno ----------
class IPTVDreamMain(Screen):
    skin = """
    <screen name="IPTVDreamMain" position="center,center" size="950,680" title="IPTV Dream">
        <widget name="version_label" position="700,10" size="230,35" font="Regular;28" halign="right" valign="center" foregroundColor="yellow" backgroundColor="#1f771f" cornerRadius="8"/>

        <eLabel text="1" position="40,80"  size="70,70" font="Regular;55" halign="center" valign="center" foregroundColor="white" backgroundColor="#1f771f" cornerRadius="12"/>
        <eLabel text="M3U URL"  position="130,80"  size="220,70" font="Regular;28" halign="left" valign="center"/>
        <eLabel text="2" position="40,160" size="70,70" font="Regular;55" halign="center" valign="center" foregroundColor="white" backgroundColor="#1f771f" cornerRadius="12"/>
        <eLabel text="M3U plik" position="130,160" size="220,70" font="Regular;28" halign="left" valign="center"/>
        <eLabel text="3" position="40,240" size="70,70" font="Regular;55" halign="center" valign="center" foregroundColor="white" backgroundColor="#1f771f" cornerRadius="12"/>
        <eLabel text="Xtream" position="130,240" size="220,70" font="Regular;28" halign="left" valign="center"/>
        <eLabel text="4" position="40,320" size="70,70" font="Regular;55" halign="center" valign="center" foregroundColor="white" backgroundColor="#1f771f" cornerRadius="12"/>
        <eLabel text="MAC Portal" position="130,320" size="220,70" font="Regular;28" halign="left" valign="center"/>
        <eLabel text="5" position="40,400" size="70,70" font="Regular;55" halign="center" valign="center" foregroundColor="white" backgroundColor="#555555" cornerRadius="12"/>
        <eLabel text="Własne M3U" position="130,400" size="220,70" font="Regular;28" halign="left" valign="center"/>
        <eLabel text="6" position="40,480" size="70,70" font="Regular;55" halign="center" valign="center" foregroundColor="white" backgroundColor="#800080" cornerRadius="12"/>
        <eLabel text="PL / EN" position="130,480" size="220,70" font="Regular;28" halign="left" valign="center"/>

        <widget name="lab1" position="380,80"  size="520,70" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab2" position="380,160" size="520,70" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab3" position="380,240" size="520,70" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab4" position="380,320" size="520,70" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab5" position="380,400" size="520,70" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab6" position="380,480" size="520,70" font="Regular;24" halign="left" valign="center"/>

        <widget name="info"   position="30,560" size="890,30" font="Regular;22" halign="center" valign="center" foregroundColor="yellow"/>
        <widget name="status" position="30,590" size="890,25" font="Regular;20" halign="center" valign="center"/>

        <widget name="key_red"    position="0,620" size="237,25" font="Regular;20" halign="center" valign="center" foregroundColor="red"/>
        <widget name="key_green"  position="237,620" size="237,25" font="Regular;20" halign="center" valign="center" foregroundColor="green"/>
        <widget name="key_yellow" position="474,620" size="237,25" font="Regular;20" halign="center" valign="center" foregroundColor="yellow"/>
        <widget name="key_blue"   position="711,620" size="237,25" font="Regular;20" halign="center" valign="center" foregroundColor="blue"/>

        <widget name="foot" position="0,650" size="950,20" font="Regular;16" halign="center" valign="center" foregroundColor="grey"/>
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session   = session
        self.playlist  = []
        self.listname  = "IPTV-Dream"
        self.lang      = language.getLanguage()[:2] or "pl"
        prof           = load_profiles()
        if prof.get("lang") in ("pl", "en"):
            self.lang = prof.get("lang")

        self.setTitle(f"IPTV Dream v{PLUGIN_VERSION}")
        self["version_label"] = Label(f"IPTV Dream v{PLUGIN_VERSION}")
        self["foot"]   = Label(f"IPTV Dream v{PLUGIN_VERSION} | by Paweł Pawelek | msisystem@t.pl")
        
        self.updateLangStrings()

        self["actions"] = ActionMap(["ColorActions", "NumberActions", "OkCancelActions"], {
            "1": self.openUrl, "2": self.openFile, "3": self.openXtream,
            "4": self.openMac, "5": self.openMyLinks, "6": self.toggleLang,
            "red": self.close, "green": self.checkUpdates, "yellow": self.toggleAutoUpdate,
            "blue": self.exportBouquet, "cancel": self.close
        }, -1)
    
    def updateLangStrings(self):
        self["key_red"]    = Label(_("exit", self.lang))
        self["key_green"]  = Label(_("check_upd", self.lang))
        self["key_yellow"] = Label(_("auto_up", self.lang))
        self["key_blue"]   = Label(_("export", self.lang))

        self["lab1"] = Label(_("load_url", self.lang))
        self["lab2"] = Label(_("pick_file", self.lang))
        self["lab3"] = Label(_("xtream", self.lang))
        self["lab4"] = Label(_("mac_json", self.lang))
        self["lab5"] = Label(_("own_links", self.lang))
        self["lab6"] = Label(_("toggle_lang", self.lang))

        self["info"]   = Label(_("press_1_6", self.lang))
        self["status"] = Label("")

    # 1) M3U URL ----------------------------------------------------------
    def openUrl(self):
        last_url = load_profiles().get("last_url", "http://")
        self.session.openWithCallback(self.onUrlReady, VKInputBox,
                                      title=_("Wklej link M3U:", self.lang),
                                      text=last_url)

    def onUrlReady(self, url):
        if not url or not url.startswith(('http://', 'https://')):
            return
        self._current_url = url
        self["status"].setText(_("downloading", self.lang))
        
        def do_download(url_to_fetch):
            # Używamy requests dla lepszej obsługi timeoutów i nagłówków
            headers = {'User-Agent': f'IPTVDream/{PLUGIN_VERSION}'}
            r = requests.get(url_to_fetch, timeout=20, headers=headers)
            r.raise_for_status() # Rzuci wyjątkiem dla kodów 4xx/5xx
            return r.content

        run_in_thread(do_download, self.onDataDownloaded, url)

    def onDataDownloaded(self, data, error):
        if error:
            self["status"].setText(_("download_fail", self.lang))
            self.session.open(MessageBox, f"URL error: {error}", MessageBox.TYPE_ERROR, timeout=5)
            return

        playlist = parse_m3u_bytes_improved(data)
        prof = load_profiles()
        prof["last_url"] = self._current_url
        save_profiles(prof)
        self.onListLoaded(playlist, "M3U-URL")

    # 2) M3U plik ---------------------------------------------------------
    def openFile(self):
        self.session.openWithCallback(self.onFileReady, M3UFilePick, start_dir="/tmp/")

    def onFileReady(self, path):
        if not path: return
        try:
            with open(path, "rb") as f:
                data = f.read()
            playlist = parse_m3u_bytes_improved(data)
            name = os.path.splitext(os.path.basename(path))[0] or "M3U-File"
            self.onListLoaded(playlist, name)
        except Exception as e:
            self.session.open(MessageBox, f"File error: {e}", MessageBox.TYPE_ERROR, timeout=5)

    # 3) Xtream -----------------------------------------------------------
    def openXtream(self):
        xtream_file = "/etc/enigma2/iptvdream_xtream.json"
        if os.path.isfile(xtream_file):
            try:
                with open(xtream_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if all(k in cfg for k in ("host", "user", "pass")):
                    self.onXtreamOne((cfg["host"], cfg["user"], cfg["pass"]))
                    return
            except Exception: pass
        self.session.openWithCallback(self.onXtreamOne, XtreamOneWindow)

    def onXtreamOne(self, data):
        if not data: return
        host, user, pwd = data
        self["status"].setText("Pobieranie listy Xtream...")
        
        def do_download_xtream():
            url = f"{host}/get.php?username={user}&password={pwd}&type=m3u_plus&output=ts"
            r = requests.get(url, timeout=20, headers={'User-Agent': f'IPTVDream/{PLUGIN_VERSION}'})
            r.raise_for_status()
            return r.content
        
        # Przekazujemy 'user' do callbacka za pomocą functools.partial
        callback = lambda result, error: self.onXtreamDataDownloaded(result, error, user)
        run_in_thread(do_download_xtream, callback)

    def onXtreamDataDownloaded(self, data, error, user):
        if error:
            self["status"].setText("Błąd pobierania Xtream.")
            self.session.open(MessageBox, f"Xtream error: {error}", MessageBox.TYPE_ERROR, timeout=5)
            return
        
        playlist = parse_m3u_bytes_improved(data)
        self.onListLoaded(playlist, f"Xtream-{user}")

    # 4) MAC Portal -------------------------------------------------------
    def openMac(self):
        data = load_mac_json()
        txt  = json.dumps(data, indent=2, ensure_ascii=False)
        self.session.openWithCallback(self.onMacJson, VKInputBox, title=_("mac_json", self.lang), text=txt)

    def onMacJson(self, txt):
        if txt is None: return
        try:
            self.data = json.loads(txt) if txt.strip() else {}
            self.session.openWithCallback(self.onMacHost, VKInputBox, title=_("mac_json", self.lang) + " – host:", text=self.data.get("host", "http://"))
        except json.JSONDecodeError as e:
            self.session.open(MessageBox, f"JSON bad: {e}", MessageBox.TYPE_ERROR, timeout=5)

    def onMacHost(self, host):
        if not host: return
        self.data["host"] = host
        self.session.openWithCallback(self.onMacMac, VKInputBox, title=_("mac_json", self.lang) + " – MAC:", text=self.data.get("mac", ""))

    def onMacMac(self, mac):
        if not mac: return
        self.data["mac"] = mac
        self["status"].setText("Pobieranie listy MAC Portal...")

        def do_parse_mac():
            return parse_mac_playlist(self.data["host"], self.data["mac"])

        run_in_thread(do_parse_mac, self.onMacDataDownloaded)

    def onMacDataDownloaded(self, playlist, error):
        if error:
            self["status"].setText("Błąd pobierania MAC.")
            self.session.open(MessageBox, f"MAC error: {error}", MessageBox.TYPE_ERROR, timeout=5)
            return

        save_mac_json(self.data)
        self.onListLoaded(playlist, "MAC-Portal")

    # 5) Własne linki -----------------------------------------------------
    def openMyLinks(self):
        try:
            with open(MY_LINKS_FILE) as f:
                links = json.load(f)
        except Exception:
            links = []
        if not links:
            self.session.open(MessageBox, _("own_links", self.lang) + " – brak wpisów.", MessageBox.TYPE_INFO, timeout=4)
            return
        menu = [(x["name"], x["url"]) for x in links]
        self.session.openWithCallback(self.onMyLink, ChoiceBox, title=_("own_links", self.lang), list=menu)

    def onMyLink(self, choice):
        if choice:
            self.onUrlReady(choice[1])

    # 6) Zmiana języka ----------------------------------------------------
    def toggleLang(self):
        self.lang = "en" if self.lang == "pl" else "pl"
        prof = load_profiles()
        prof["lang"] = self.lang
        save_profiles(prof)
        self.updateLangStrings() # Wywołujemy jedną metodę do aktualizacji wszystkich tekstów
        self.session.open(MessageBox, _("lang_changed", self.lang) + " " + self.lang.upper(), MessageBox.TYPE_INFO, timeout=2)

    # ---------- Ujednolicona obsługa załadowanej listy i EPG/Piconów ----------
    def onListLoaded(self, playlist, name):
        if not playlist:
            self.session.open(MessageBox, "Plik nie zawiera kanałów lub ma błędny format.", MessageBox.TYPE_WARNING, timeout=4)
            self["status"].setText("")
            return

        self.session.openWithCallback(
            lambda choice: self.onPostProcessChoice(playlist, name, choice),
            MessageBox,
            f"Załadowano {len(playlist)} kanałów.\nCzy chcesz spróbować pobrać EPG i ikony (picony)?\nMoże to zająć dłuższą chwilę.",
            MessageBox.TYPE_YESNO,
            default=False
        )

    def onPostProcessChoice(self, playlist, name, answer):
        if answer:
            self["status"].setText("Pobieranie EPG i Piconów... To może potrwać.")
            run_in_thread(self._post_process_playlist, self.onPostProcessDone, playlist, name)
        else:
            # Uruchamiamy callback z pustym błędem, aby zachować spójność
            self.onPostProcessDone((playlist, name), None)

    def _post_process_playlist(self, playlist, name):
        # Ta funkcja działa w tle
        fetch_epg_for_playlist(playlist) # Pobiera EPG
        for i, ch in enumerate(playlist):
            logo_url = ch.get("logo", "")
            if logo_url:
                # picon_path nie jest już potrzebny, bo export tego nie używa
                download_picon_url(logo_url, ch["title"])
        return (playlist, name)

    def onPostProcessDone(self, result, error):
        if error:
            self.session.open(MessageBox, f"Błąd podczas pobierania EPG/Picon: {error}", MessageBox.TYPE_ERROR)
            if result is None:
                self["status"].setText("Błąd EPG/Picon. Przerwano.")
                return

        playlist, name = result
        self.playlist = playlist
        self.listname = name
        self["status"].setText(f"Gotowe. Naciśnij NIEBIESKI, aby wybrać bukiety i eksportować.")
        # Automatycznie otwiera okno wyboru bukietów
        self.exportBouquet()

    # ---------- GREEN – check updates -----------------------------------
    def checkUpdates(self):
        newer, local, remote = check_update()
        if not newer:
            self.session.open(MessageBox, f"{_('no_update', self.lang)}\n{_('local_ver', self.lang)}: {local}\n{_('remote_ver', self.lang)}: {remote}", MessageBox.TYPE_INFO, timeout=5)
        else:
            self.session.openWithCallback(self.confirmedUpdate, MessageBox, f"{_('local_ver', self.lang)}: {local}\n{_('remote_ver', self.lang)}: {remote}\n\n{_('update_ask', self.lang)}", MessageBox.TYPE_YESNO)

    def confirmedUpdate(self, answer):
        if answer:
            try:
                if do_update():
                    self.session.openWithCallback(self.restartGUI, MessageBox, _("update_ok", self.lang), MessageBox.TYPE_YESNO)
            except Exception as e:
                self.session.open(MessageBox, f"{_('update_fail', self.lang)}\n{e}", MessageBox.TYPE_ERROR, timeout=5)

    def restartGUI(self, answer):
        if answer:
            from enigma import quitMainloop
            quitMainloop(3)

    # ---------- YELLOW – auto-update cron -------------------------------
    def toggleAutoUpdate(self):
        cron = "/etc/cron/crontabs/root"
        os.makedirs(os.path.dirname(cron), exist_ok=True)
        enabled = False
        if os.path.exists(cron):
            with open(cron) as f:
                enabled = "IPTVDREAM_AUTO" in f.read()
        
        if enabled:
            with open(cron) as f:
                lines = [l for l in f.read().splitlines() if "IPTVDREAM_AUTO" not in l]
            with open(cron, "w") as f:
                f.write("\n".join(lines) + ("\n" if lines else ""))
            self["status"].setText(_("auto_off", self.lang))
        else:
            script = "/usr/lib/enigma2/python/Plugins/Extensions/IPTVDream/auto_update.sh"
            with open(cron, "a") as f:
                f.write(f'0 5 * * * {script} # IPTVDREAM_AUTO\n')
            self["status"].setText(_("auto_on", self.lang))

    # ---------- BLUE – export z wyborem bukietów ------------------------
    def exportBouquet(self):
        if not self.playlist:
            self.session.open(MessageBox, _("load_first", self.lang), MessageBox.TYPE_WARNING, timeout=4)
            return

        groups = {}
        for ch in self.playlist:
            g = ch.get("group", "").strip() or "Inne" # Grupa pobrana z parsera
            groups.setdefault(g, []).append(ch)

        if groups:
            self.session.openWithCallback(self.onBouquetsChosen, BouquetPicker, groups)
            self._groups = groups
            self._name   = self.listname
        else:
            self.finishLoad(self.playlist, self.listname)

    def onBouquetsChosen(self, selected):
        if not selected:
            return
        final_playlist = []
        for group_name in selected:
            if isinstance(group_name, str) and group_name in self._groups:
                final_playlist.extend(self._groups[group_name])
        self.finishLoad(final_playlist, self._name)

    def finishLoad(self, playlist, name):
        if not playlist:
            self.session.open(MessageBox, "Nie wybrano żadnych kanałów do eksportu.", MessageBox.TYPE_INFO, timeout=3)
            return
            
        # keep_groups=True, aby każdy bukiet był w osobnym pliku
        num_bouquets, num_channels = export_bouquets(playlist, bouquet_name=name, keep_groups=True)
        self.session.open(MessageBox, f"Eksport zakończony!\n{num_channels} kanałów w {num_bouquets} bukietach.", MessageBox.TYPE_INFO, timeout=4)

    # ---------- wyjście ----------
    def cancel(self):
        self.close()
