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
from .tools.mac_portal    import (load_mac_json, save_mac_json,
                                  parse_mac_playlist, download_picon_url)
from .tools.updater       import check_update, do_update
from .tools.lang          import _
import os, json, urllib.request, requests

PROFILES      = "/etc/enigma2/iptvdream_profiles.json"
MY_LINKS_FILE = "/etc/enigma2/iptvdream_mylinks.json"

# ---------- pomocnicze ----------
def parse_m3u_bytes(data):
    out, last = [], None
    for raw in data.decode("utf-8", "ignore").splitlines():
        s = raw.strip()
        if not s or s.startswith("#EXTM3U"):
            continue
        if s.startswith("#EXTINF"):
            try:
                last = s.split(",", 1)[1].strip()
            except:
                last = "IPTV"
        elif "://" in s:
            out.append({"title": last or s, "url": s, "epg": "", "logo": ""})
            last = None
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
    <screen name="IPTVDreamMain" position="center,center" size="900,700" title="IPTV Dream v2.1">
        <!-- NAZWA I WERSJA – prawy górny róg -->
        <eLabel text="IPTV Dream v2.1" position="700,10" size="190,30" font="Regular;22" halign="right" valign="center" foregroundColor="yellow" backgroundColor="#1f771f" cornerRadius="8"/>

        <!-- 6 źródeł -->
        <eLabel text="1" position="90,90"  size="60,60" font="Regular;48" halign="center" valign="center" foregroundColor="white" backgroundColor="#1f771f" cornerRadius="12"/>
        <eLabel text="M3U URL"  position="170,90"  size="200,60" font="Regular;28" halign="left" valign="center"/>
        <eLabel text="2" position="90,170" size="60,60" font="Regular;48" halign="center" valign="center" foregroundColor="white" backgroundColor="#1f771f" cornerRadius="12"/>
        <eLabel text="M3U plik" position="170,170" size="200,60" font="Regular;28" halign="left" valign="center"/>
        <eLabel text="3" position="90,250" size="60,60" font="Regular;48" halign="center" valign="center" foregroundColor="white" backgroundColor="#1f771f" cornerRadius="12"/>
        <eLabel text="Xtream" position="170,250" size="200,60" font="Regular;28" halign="left" valign="center"/>
        <eLabel text="4" position="90,330" size="60,60" font="Regular;48" halign="center" valign="center" foregroundColor="white" backgroundColor="#1f771f" cornerRadius="12"/>
        <eLabel text="MAC Portal" position="170,330" size="200,60" font="Regular;28" halign="left" valign="center"/>
        <eLabel text="5" position="90,410" size="60,60" font="Regular;48" halign="center" valign="center" foregroundColor="white" backgroundColor="#555555" cornerRadius="12"/>
        <eLabel text="Własne M3U" position="170,410" size="200,60" font="Regular;28" halign="left" valign="center"/>
        <eLabel text="6" position="90,490" size="60,60" font="Regular;48" halign="center" valign="center" foregroundColor="white" backgroundColor="#800080" cornerRadius="12"/>
        <eLabel text="PL / EN" position="170,490" size="200,60" font="Regular;28" halign="left" valign="center"/>

        <widget name="lab1" position="400,90"  size="450,60" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab2" position="400,170" size="450,60" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab3" position="400,250" size="450,60" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab4" position="400,330" size="450,60" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab5" position="400,410" size="450,60" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab6" position="400,490" size="450,60" font="Regular;24" halign="left" valign="center"/>

        <widget name="info"   position="30,560" size="840,30" font="Regular;22" halign="center" valign="center" foregroundColor="yellow"/>
        <widget name="status" position="30,590" size="840,30" font="Regular;20" halign="center" valign="center"/>

        <!-- 4 standardowe przyciski -->
        <widget name="key_red"    position="0,625" size="225,25" font="Regular;20" halign="center" valign="center" foregroundColor="red"/>
        <widget name="key_green"  position="225,625" size="225,25" font="Regular;20" halign="center" valign="center" foregroundColor="green"/>
        <widget name="key_yellow" position="450,625" size="225,25" font="Regular;20" halign="center" valign="center" foregroundColor="yellow"/>
        <widget name="key_blue"   position="675,625" size="225,25" font="Regular;20" halign="center" valign="center" foregroundColor="blue"/>

        <!-- STOPKA – identyczna jak w Twojej wtyczce AIO 1.9r3 -->
        <widget name="foot" position="0,655" size="900,40" font="Regular;18" halign="center" valign="center" foregroundColor="grey"/>
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session   = session
        self.playlist  = []
        self.listname  = "IPTV-Dream"
        # JĘZYK SYSTEMOWY (PL domyślnie)
        self.lang      = language.getLanguage()[:2] or "pl"
        prof           = load_profiles()
        if prof.get("lang") in ("pl", "en"):
            self.lang = prof.get("lang")

        # etykiety – od razu w języku systemowym
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
        self["foot"]   = Label("IPTV Dream v2.1 | msisystem@t.pl | by: Paweł Pawełek")   # ← STOPKA

        self["actions"] = ActionMap(["ColorActions", "NumberActions", "OkCancelActions"], {
            "1": self.openUrl,
            "2": self.openFile,
            "3": self.openXtream,
            "4": self.openMac,
            "5": self.openMyLinks,
            "6": self.toggleLang,
            "red": self.close,
            "green": self.checkUpdates,
            "yellow": self.toggleAutoUpdate,
            "blue": self.exportBouquet,
            "ok": self.openUrl,
            "cancel": self.close
        }, -1)

    # ---------- 1) M3U URL ----------
    def openUrl(self):
        self.session.openWithCallback(self.onUrlReady, VKInputBox,
                                      title=_("load_url", self.lang),
                                      text="http://")

    def onUrlReady(self, url):
        if not url:
            return
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                data = r.read()
            playlist = parse_m3u_bytes(data)
            prof = load_profiles()
            prof["last_url"] = url
            save_profiles(prof)
            self.onListLoaded(playlist, "M3U-URL")
        except Exception as e:
            self.session.open(MessageBox, "URL error: " + str(e), MessageBox.TYPE_ERROR, timeout=5)

    # ---------- 2) M3U file ----------
    def openFile(self):
        self.session.openWithCallback(self.onFileReady, M3UFilePick, start_dir="/tmp/")

    def onFileReady(self, path):
        if not path:
            return
        try:
            with open(path, "rb") as f:
                data = f.read()
            playlist = parse_m3u_bytes(data)
            name = os.path.splitext(os.path.basename(path))[0] or "M3U-File"
            self.onListLoaded(playlist, name)
        except Exception as e:
            self.session.open(MessageBox, "File error: " + str(e), MessageBox.TYPE_ERROR, timeout=5)

    # ---------- 3) Xtream ----------
    def openXtream(self):
        self.session.openWithCallback(self.xtreamHost, VKInputBox,
                                      title=_("xtream", self.lang),
                                      text="http://example.com")

    def xtreamHost(self, host):
        if not host:
            return
        self.x_host = host.rstrip("/")
        self.session.openWithCallback(self.xtreamUser, VKInputBox,
                                      title=_("xtream", self.lang) + " – user:",
                                      text="")

    def xtreamUser(self, user):
        if not user:
            return
        self.x_user = user
        self.session.openWithCallback(self.xtreamPass, VKInputBox,
                                      title=_("xtream", self.lang) + " – password:",
                                      text="")

    def xtreamPass(self, pwd):
        if not pwd:
            return
        m3u = f"{self.x_host}/get.php?username={self.x_user}&password={pwd}&type=m3u_plus&output=ts"
        try:
            with urllib.request.urlopen(m3u, timeout=15) as r:
                data = r.read()
            playlist = parse_m3u_bytes(data)
            prof = load_profiles()
            prof["last_url"] = m3u
            save_profiles(prof)
            self.onListLoaded(playlist, f"Xtream-{self.x_user}")
        except Exception as e:
            self.session.open(MessageBox, "Xtream error: " + str(e), MessageBox.TYPE_ERROR, timeout=5)

    # ---------- 4) MAC ----------
    def openMac(self):
        data = load_mac_json()
        txt  = json.dumps(data, indent=2, ensure_ascii=False)
        self.session.openWithCallback(self.onMacJson, VKInputBox,
                                      title=_("mac_json", self.lang),
                                      text=txt)

    def onMacJson(self, txt):
        if txt is None:
            return
        try:
            data = json.loads(txt) if txt.strip() else {}
            if not data.get("host"):
                self.session.openWithCallback(self.onMacHost, VKInputBox,
                                              title=_("mac_json", self.lang) + " – host:",
                                              text="http://example.com")
            else:
                self.onMacHost(data["host"], data=data)
        except Exception as e:
            self.session.open(MessageBox, "JSON bad: " + str(e), MessageBox.TYPE_ERROR, timeout=5)

    def onMacHost(self, host, data=None):
        if not host:
            return
        if data is None:
            data = {}
        data["host"] = host
        self.data = data
        self.session.openWithCallback(self.onMacMac, VKInputBox,
                                      title=_("mac_json", self.lang) + " – MAC:",
                                      text=data.get("mac", ""))

    def onMacMac(self, mac):
        if not mac:
            return
        self.data["mac"] = mac
        try:
            playlist = parse_mac_playlist(self.data["host"], mac)
            for ch in playlist:
                ch["picon"] = download_picon_url(ch.get("logo", ""), ch["title"])
            save_mac_json(self.data)
            self.onListLoaded(playlist, "MAC-Portal")
        except Exception as e:
            self.session.open(MessageBox, "MAC error: " + str(e), MessageBox.TYPE_ERROR, timeout=5)

    # ---------- 5) Own M3U links ----------
    def openMyLinks(self):
        try:
            with open(MY_LINKS_FILE) as f:
                links = json.load(f)
        except Exception:
            links = []
        if not links:
            self.session.open(MessageBox, _("own_links", self.lang) + " – brak wpisów.",
                              MessageBox.TYPE_INFO, timeout=4)
            return
        menu = [(x["name"], x["url"]) for x in links]
        self.session.openWithCallback(self.onMyLink, ChoiceBox,
                                      title=_("own_links", self.lang),
                                      list=menu)

    def onMyLink(self, choice):
        if choice:
            self.onUrlReady(choice[1])

    # ---------- 6) Language ----------
    def toggleLang(self):
        self.lang = "en" if self.lang == "pl" else "pl"
        prof = load_profiles()
        prof["lang"] = self.lang
        save_profiles(prof)
        # odśwież WSZYSTKIE etykiety
        self["lab1"].setText(_("load_url", self.lang))
        self["lab2"].setText(_("pick_file", self.lang))
        self["lab3"].setText(_("xtream", self.lang))
        self["lab4"].setText(_("mac_json", self.lang))
        self["lab5"].setText(_("own_links", self.lang))
        self["lab6"].setText(_("toggle_lang", self.lang))
        self["key_red"].setText(_("exit", self.lang))
        self["key_green"].setText(_("check_upd", self.lang))
        self["key_yellow"].setText(_("auto_up", self.lang))
        self["key_blue"].setText(_("export", self.lang))
        self["info"].setText(_("press_1_6", self.lang))
        self["foot"].setText("IPTV Dream v2.1 | msisystem@t.pl | GitHub: OliOli2013")
        self.session.open(MessageBox, _("lang_changed", self.lang) + " " + self.lang.upper(),
                          MessageBox.TYPE_INFO, timeout=2)

    # ---------- GREEN – check updates ----------
    def checkUpdates(self):
        newer, local, remote = check_update()
        if not newer:
            self.session.open(MessageBox,
                              _("no_update", self.lang) + "\n" +
                              _("local_ver", self.lang) + ": " + local + "\n" +
                              _("remote_ver", self.lang) + ": " + remote,
                              MessageBox.TYPE_INFO, timeout=5)
        else:
            self.session.openWithCallback(self.confirmedUpdate, MessageBox,
                                          _("local_ver", self.lang) + ": " + local + "\n" +
                                          _("remote_ver", self.lang) + ": " + remote + "\n\n" +
                                          _("update_ask", self.lang),
                                          MessageBox.TYPE_YESNO)

    def confirmedUpdate(self, answer):
        if answer:
            try:
                if do_update():
                    self.session.openWithCallback(self.restartGUI, MessageBox,
                                                  _("update_ok", self.lang),
                                                  MessageBox.TYPE_YESNO)
            except Exception as e:
                self.session.open(MessageBox, _("update_fail", self.lang) + "\n" + str(e),
                                  MessageBox.TYPE_ERROR, timeout=5)

    def restartGUI(self, answer):
        if answer:
            from enigma import quitMainloop
            quitMainloop(3)

    # ---------- BLUE – export ----------
    def exportBouquet(self):
        if not self.playlist:
            self.session.open(MessageBox, _("load_first", self.lang),
                              MessageBox.TYPE_WARNING, timeout=4)
            return
        export_bouquets(self.playlist, bouquet_name=self.listname, keep_groups=True)
        self.session.open(MessageBox, _("exported", self.lang),
                          MessageBox.TYPE_INFO, timeout=5)

    # ---------- YELLOW – cron ----------
    def toggleAutoUpdate(self):
        cron = "/etc/cron/crontabs/root"
        os.makedirs(os.path.dirname(cron), exist_ok=True)
        enabled = False
        if os.path.exists(cron):
            enabled = "IPTVDREAM_AUTO" in open(cron).read()
        if enabled:
            lines = [l for l in open(cron).read().splitlines() if "IPTVDREAM_AUTO" not in l]
            open(cron, "w").write("\n".join(lines) + ("\n" if lines else ""))
            self["status"].setText(_("auto_off", self.lang))
        else:
            script = "/usr/lib/enigma2/python/Plugins/Extensions/IPTVDream/auto_update.sh"
            with open(cron, "a") as f:
                f.write('0 5 * * * %s # IPTVDREAM_AUTO\n' % script)
            self["status"].setText(_("auto_on", self.lang))

    # ---------- common ----------
    def onListLoaded(self, playlist, name):
        self.playlist = playlist
        self.listname = name
        self["status"].setText(_("loaded", self.lang) % len(playlist))
