# -*- coding: utf-8 -*-
from Screens.Screen       import Screen
from Screens.MessageBox   import MessageBox
from Screens.ChoiceBox    import ChoiceBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.ActionMap import ActionMap
from Components.Label     import Label
from Components.Language  import language
from .export              import export_bouquets, add_to_bouquets_index
from .vkb_input           import VKInputBox
from .file_pick           import M3UFilePick
from .tools.mac_portal    import (load_mac_json, save_mac_json, parse_mac_playlist)
from .tools.updater       import check_update, do_update
from .tools.lang          import _
from .tools.xtream_one_window import XtreamOneWindow
from .tools.bouquet_picker    import BouquetPicker
from .tools.epg_picon         import fetch_epg_for_playlist, download_picon_url, install_epg_sources, EPG_URL_KEY
import os, json, re, threading
import requests
from twisted.internet import reactor
from enigma import quitMainloop
from datetime import date 
from Components.SystemInfo import SystemInfo
from enigma import eDVBDB 

PROFILES      = "/etc/enigma2/iptvdream_profiles.json"
MY_LINKS_FILE = "/etc/enigma2/iptvdream_mylinks.json"
PLUGIN_VERSION = "3.3" 

def run_in_thread(blocking_func, on_done_callback, *args, **kwargs):
    def thread_target():
        try:
            result = blocking_func(*args, **kwargs)
            reactor.callFromThread(on_done_callback, result, None)
        except Exception as e:
            reactor.callFromThread(on_done_callback, None, str(e))
    t = threading.Thread(target=thread_target)
    t.daemon = True
    t.start()

def parse_m3u_bytes_improved(data):
    out = []
    try: text = data.decode("utf-8", "ignore")
    except: text = str(data)
    current_attrs = {}
    rx_group = re.compile(r'group-title="([^"]+)"')
    rx_logo  = re.compile(r'tvg-logo="([^"]+)"')
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#EXTM3U"): continue
        if line.startswith("#EXTINF"):
            parts = line.split(',', 1)
            title = parts[1].strip() if len(parts) > 1 else "No Title"
            g_match = rx_group.search(line)
            l_match = rx_logo.search(line)
            current_attrs = {
                "title": title,
                "group": g_match.group(1).strip() if g_match else "Inne",
                "logo":  l_match.group(1).strip() if l_match else ""
            }
        elif "://" in line and not line.startswith("#"):
            url = line.strip()
            if current_attrs:
                out.append({
                    "title": current_attrs.get("title", "No Name"),
                    "url":   url,
                    "group": current_attrs.get("group", "Inne"),
                    "logo":  current_attrs.get("logo", ""),
                    "epg":   ""
                })
                current_attrs = {} 
            else:
                out.append({"title": url.split('/')[-1], "url": url, "group": "Inne", "logo": "", "epg": ""})
    return out

def load_profiles():
    try:
        if os.path.exists(PROFILES):
            with open(PROFILES, "r") as f: return json.load(f)
    except: pass
    return {}

def save_profiles(data):
    try:
        with open(PROFILES, "w") as f: json.dump(data, f, indent=2, ensure_ascii=False)
    except: pass

class IPTVDreamMain(Screen):
    skin = """
    <screen name="IPTVDreamMain" position="center,center" size="950,750" title="IPTV Dream">
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
        
        <eLabel text="7" position="40,560" size="70,70" font="Regular;55" halign="center" valign="center" foregroundColor="white" backgroundColor="#ff8000" cornerRadius="12"/>
        <eLabel text="EPG URL" position="130,560" size="220,70" font="Regular;28" halign="left" valign="center"/>
        
        <widget name="lab1" position="380,80"  size="520,70" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab2" position="380,160" size="520,70" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab3" position="380,240" size="520,70" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab4" position="380,320" size="520,70" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab5" position="380,400" size="520,70" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab6" position="380,480" size="520,70" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab7" position="380,560" size="520,70" font="Regular;24" halign="left" valign="center"/> 
        
        <widget name="info"   position="30,640" size="890,30" font="Regular;22" halign="center" valign="center" foregroundColor="yellow"/>
        
        <widget name="status" position="30,670" size="890,30" font="Regular;26" halign="center" valign="center" foregroundColor="#00ff00"/>
        
        <widget name="key_red"    position="0,700" size="237,25" font="Regular;20" halign="center" valign="center" foregroundColor="red"/>
        <widget name="key_green"  position="237,700" size="237,25" font="Regular;20" halign="center" valign="center" foregroundColor="green"/>
        <widget name="key_yellow" position="474,700" size="237,25" font="Regular;20" halign="center" valign="center" foregroundColor="yellow"/>
        <widget name="key_blue"   position="711,700" size="237,25" font="Regular;20" halign="center" valign="center" foregroundColor="blue"/>
        
        <widget name="foot" position="0,730" size="950,20" font="Regular;16" halign="center" valign="center" foregroundColor="grey"/>
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session   = session
        self.playlist  = []
        self.listname  = "IPTV-Dream"
        self.prof = load_profiles()
        
        # Ustalanie języka (Systemowy priorytetem)
        sys_lang = language.getLanguage()[:2] 
        self.lang = "pl" if sys_lang == "pl" else "en"
        
        self.setTitle(f"IPTV Dream v{PLUGIN_VERSION}")
        self["version_label"] = Label(f"IPTV Dream v{PLUGIN_VERSION}")
        self["foot"] = Label("") # Inicjalizacja przed updateLangStrings
        
        self.updateLangStrings()
        self["actions"] = ActionMap(["ColorActions", "NumberActions", "OkCancelActions"], {
            "1": self.openUrl, "2": self.openFile, "3": self.openXtream,
            "4": self.openMac, "5": self.openMyLinks, "6": self.toggleLang,
            "7": self.openEpgUrl,
            "red": self.close, "green": self.checkUpdates, 
            "yellow": self.forceInstallEPG,
            "blue": self.exportBouquet, "cancel": self.close
        }, -1)
        self.onLayoutFinish.append(self.startAutoCheck)

    def startAutoCheck(self):
        if self.prof.get("auto_update", False):
            self.checkUpdates(silent=True)

    def updateLangStrings(self):
        self["key_red"]    = Label(_("exit", self.lang))
        self["key_green"]  = Label(_("check_upd", self.lang))
        self["key_yellow"] = Label(_("epg_install", self.lang))
        self["key_blue"]   = Label(_("export", self.lang))
        self["lab1"] = Label(_("load_url", self.lang))
        self["lab2"] = Label(_("pick_file", self.lang))
        self["lab3"] = Label(_("xtream", self.lang))
        self["lab4"] = Label(_("mac_json", self.lang))
        self["lab5"] = Label(_("own_links", self.lang))
        self["lab6"] = Label(_("toggle_lang", self.lang))
        self["lab7"] = Label(_("url_epg", self.lang))
        self["info"]   = Label(_("press_1_6", self.lang))
        self["status"] = Label("")
        
        today_date = date.today().strftime("%Y-%m-%d")
        foot_text = _("foot", self.lang).replace("{date}", today_date)
        self["foot"].setText(f"{foot_text} v{PLUGIN_VERSION}")

    # === FUNKCJE BEZ POP-UPÓW (Teraz używają dużego statusu) ===

    def openEpgUrl(self):
        current_url = self.prof.get(EPG_URL_KEY, "http://")
        self.session.openWithCallback(self.onEpgUrlReady, VirtualKeyBoard, title=_("Wklej URL EPG:", self.lang), text=current_url)

    def onEpgUrlReady(self, url):
        if not url: return
        self.prof[EPG_URL_KEY] = url
        save_profiles(self.prof)
        self.session.open(MessageBox, _("epg_url_saved_info", self.lang), MessageBox.TYPE_INFO)

    def forceInstallEPG(self):
        custom_url = self.prof.get(EPG_URL_KEY)
        success, msg = install_epg_sources(custom_url=custom_url)
        if success:
            self.session.open(MessageBox, f"{msg}\n\n{_('epg_install_success_info', self.lang)}", MessageBox.TYPE_INFO)
        else:
            self.session.open(MessageBox, f"{_('error', self.lang)}: {msg}", MessageBox.TYPE_ERROR)

    def openUrl(self):
        last_url = self.prof.get("last_url", "http://")
        self.session.openWithCallback(self.onUrlReady, VirtualKeyBoard, title=_("Wklej link M3U:", self.lang), text=last_url)

    def onUrlReady(self, url):
        if not url or not url.startswith(('http://', 'https://')): return
        self._current_url = url
        # STATUS: Wyświetlamy informację przed uruchomieniem wątku
        self["status"].setText(_("downloading", self.lang)) 
        
        def do_download(target_url):
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(target_url, timeout=30, headers=headers, verify=False)
            r.raise_for_status()
            return r.content
        run_in_thread(do_download, self.onDataDownloaded, url)

    def onDataDownloaded(self, data, error):
        if error:
            self["status"].setText(_("download_error", self.lang)) # STATUS: Błąd
            self.session.open(MessageBox, f"URL Error: {error}", MessageBox.TYPE_ERROR)
            return
        playlist = parse_m3u_bytes_improved(data)
        self.prof["last_url"] = self._current_url
        save_profiles(self.prof)
        self.onListLoaded(playlist, "M3U-URL")

    def openFile(self):
        self.session.openWithCallback(self.onFileReady, M3UFilePick, start_dir="/tmp/")

    def onFileReady(self, path):
        if not path: return
        try:
            with open(path, "rb") as f: data = f.read()
            playlist = parse_m3u_bytes_improved(data)
            name = os.path.splitext(os.path.basename(path))[0]
            self.onListLoaded(playlist, name)
        except Exception as e:
            self.session.open(MessageBox, f"File error: {e}", MessageBox.TYPE_ERROR)

    def openXtream(self):
        self.session.openWithCallback(self.onXtreamOne, XtreamOneWindow)

    def onXtreamOne(self, data):
        if not data: return
        host, user, pwd = data
        # STATUS: Informacja widoczna
        self["status"].setText(_("downloading_xtream", self.lang))
        
        def do_dl():
            base = host if host.startswith("http") else f"http://{host}"
            url = f"{base}/get.php?username={user}&password={pwd}&type=m3u_plus&output=ts"
            r = requests.get(url, timeout=30, verify=False)
            r.raise_for_status()
            return r.content
        run_in_thread(do_dl, lambda res, err: self.onXtreamDone(res, err, user))

    def onXtreamDone(self, data, error, user):
        if error:
            self["status"].setText(_("xtream_error", self.lang)) # STATUS: Błąd
            self.session.open(MessageBox, f"Xtream Error: {error}", MessageBox.TYPE_ERROR)
            return
        self.onListLoaded(parse_m3u_bytes_improved(data), f"Xtream-{user}")

    def openMac(self):
        data = load_mac_json()
        txt  = json.dumps(data, indent=2)
        self.session.openWithCallback(self.onMacJson, VirtualKeyBoard, title="JSON", text=txt)
    
    def onMacJson(self, txt):
        if not txt: return
        try:
            self.data = json.loads(txt)
            if self.data.get("host") and self.data.get("mac"):
                # STATUS: Wyraźna informacja dla użytkownika
                self["status"].setText(_("downloading_mac", self.lang))
                reactor.callInThread(self._mac_thread_worker, self.data["host"], self.data["mac"])
            else:
                self.session.open(MessageBox, _("mac_no_host_mac", self.lang), MessageBox.TYPE_ERROR)
        except Exception as e:
            self.session.open(MessageBox, f"JSON Error: {e}", MessageBox.TYPE_ERROR)

    def _mac_thread_worker(self, host, mac):
        try:
            playlist = parse_mac_playlist(host, mac)
            reactor.callFromThread(self._mac_thread_done, playlist, None)
        except Exception as e:
            reactor.callFromThread(self._mac_thread_done, None, str(e))

    def _mac_thread_done(self, playlist, error):
        if error:
            self["status"].setText(_("mac_error", self.lang)) # STATUS: Błąd
            self.session.open(MessageBox, str(error), MessageBox.TYPE_ERROR)
            return
        try:
            save_mac_json(self.data)
            if not playlist:
                self.session.open(MessageBox, _("portal_returned_zero", self.lang), MessageBox.TYPE_ERROR)
                self.onListLoaded([], "MAC-Portal")
                return
        except Exception as e:
            print(f"[IPTVDream] Błąd: {e}")
        self.onListLoaded(playlist, "MAC-Portal")

    def openMyLinks(self):
        if os.path.exists(MY_LINKS_FILE):
            with open(MY_LINKS_FILE) as f: links = json.load(f)
            if links:
                self.session.openWithCallback(lambda c: c and self.onUrlReady(c[1]), 
                                              ChoiceBox, title=_("pick_link", self.lang), list=[(x["name"], x["url"]) for x in links])
                return
        self.session.open(MessageBox, _("no_saved_links", self.lang), MessageBox.TYPE_INFO)

    def toggleLang(self):
        self.lang = "en" if self.lang == "pl" else "pl"
        self.updateLangStrings()
        self["status"].setText(f"{_('lang_changed', self.lang)} {self.lang.upper()}")

    def onListLoaded(self, playlist, name):
        if not playlist:
            self["status"].setText("")
            return
        self.playlist = playlist
        self.listname = name
        self["status"].setText(f"{_('loaded', self.lang) % len(playlist)}")
        
        custom_url = self.prof.get(EPG_URL_KEY)
        install_epg_sources(custom_url=custom_url)
        
        self["status"].setText(_("epg_generating", self.lang))
        run_in_thread(self._bg_worker, self.onPostProcessDone, self.playlist)

    def _bg_worker(self, pl):
        from .export import create_epg_xml
        import zlib
        epg_mapping = []
        for ch in pl:
            title = ch.get("title", "No Name")
            url   = ch.get("url", "")
            if not url: continue
            unique_sid = zlib.crc32(url.encode()) & 0xffff
            if unique_sid == 0: unique_sid = 1
            sid_hex = f"{unique_sid:X}"
            ref_dvb  = f"1:0:1:{sid_hex}:0:0:0:0:0:0"
            ref_iptv = f"4097:0:1:{sid_hex}:0:0:0:0:0:0"
            ref_ext  = f"5002:0:1:{sid_hex}:0:0:0:0:0:0"
            epg_mapping.append((ref_dvb, title))
            epg_mapping.append((ref_iptv, title))
            epg_mapping.append((ref_ext, title))
        create_epg_xml(epg_mapping)
        fetch_epg_for_playlist(pl)
        return pl

    def onPostProcessDone(self, result, error):
        self["status"].setText(_("epg_done_opening", self.lang))
        self.exportBouquet()

    def exportBouquet(self):
        if not self.playlist: return
        groups = {}
        for ch in self.playlist:
            g = ch.get("group", "Inne") or "Inne"
            groups.setdefault(g, []).append(ch)
        self._groups = groups
        self.session.openWithCallback(self.onBouquetsSelected, BouquetPicker, groups)

    def onBouquetsSelected(self, selected_keys):
        if not selected_keys: return
        final_list = []
        for k in selected_keys:
            if k in self._groups:
                final_list.extend(self._groups[k])
        res, chans = export_bouquets(final_list, self.listname)
        try:
             eDVBDB.getInstance().reloadBouquets()
             eDVBDB.getInstance().reloadServicelist()
        except Exception: pass
        
        self.session.openWithCallback(
            self.onExportFinished,
            MessageBox,
            f"{_('exported_channels_bouquets', self.lang) % (chans, res)}", 
            MessageBox.TYPE_INFO
        )

    def onExportFinished(self, answer=None):
        self.close()

    def checkUpdates(self, silent=False):
        if not silent:
            self["status"].setText(_("checking_update", self.lang))
        run_in_thread(check_update, lambda res, err: self.onUpdateCheck(res, err, silent))

    def onUpdateCheck(self, result, error, silent):
        if error or not result:
            if not silent:
                self["status"].setText(_("update_check_error", self.lang))
                self.session.open(MessageBox, _("update_check_fail_msg", self.lang), MessageBox.TYPE_ERROR)
            return

        has_new, local_ver, remote_ver, changelog = result

        if has_new:
            msg = f"{_('remote_ver', self.lang)}: v{remote_ver}\n"
            msg += f"{_('local_ver', self.lang)}: v{local_ver}\n\n"
            msg += f"{_('changes', self.lang)}:\n"
            msg += f"{changelog}\n\n"
            msg += _("update_ask", self.lang)
            
            self.session.openWithCallback(self.doUpdateConfirm, MessageBox, msg, MessageBox.TYPE_YESNO)
        else:
            if not silent:
                self["status"].setText(f"{_('no_update', self.lang)} (v{local_ver}).")
                self.session.open(MessageBox, f"{_('no_update_msg', self.lang)} (v{local_ver}).", MessageBox.TYPE_INFO)

    def doUpdateConfirm(self, ans):
        if ans: run_in_thread(do_update, self.onUpdateDone)

    def onUpdateDone(self, res, err):
        if err:
            self.session.open(MessageBox, f"{_('update_fail', self.lang)}: {err}", MessageBox.TYPE_ERROR)
        else:
            self.session.openWithCallback(lambda x: x and quitMainloop(3), MessageBox, 
                                          _("update_ok_restart_msg", self.lang), 
                                          MessageBox.TYPE_YESNO)

    def toggleAutoUpdate(self):
        current_state = self.prof.get("auto_update", False)
        new_state = not current_state
        self.prof["auto_update"] = new_state
        save_profiles(self.prof)
        self.updateLangStrings()
        msg = _("auto_on_full", self.lang) if new_state else _("auto_off_full", self.lang)
        self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)

    def close(self):
        Screen.close(self)
