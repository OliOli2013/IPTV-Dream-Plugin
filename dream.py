# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Label import Label
from Components.config import config
from .export import export_bouquets
from .vkb_input import VKInputBox
from .file_pick import M3UFilePick
import os, json, urllib.request

PROFILES = "/etc/enigma2/iptvdream_profiles.json"

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
    try:
        with open(PROFILES, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

class IPTVDreamMain(Screen):
    skin = """
    <screen name="IPTVDreamMain" position="center,center" size="900,520" title="IPTV Dream v2.0">
        <eLabel text="1" position="90,90"  size="60,60" font="Regular;48" halign="center" valign="center" foregroundColor="white" backgroundColor="#1f771f" cornerRadius="12"/>
        <eLabel text="M3U URL"  position="170,90"  size="200,60" font="Regular;28" halign="left" valign="center"/>
        <eLabel text="2" position="90,170" size="60,60" font="Regular;48" halign="center" valign="center" foregroundColor="white" backgroundColor="#1f771f" cornerRadius="12"/>
        <eLabel text="M3U plik" position="170,170" size="200,60" font="Regular;28" halign="left" valign="center"/>
        <eLabel text="3" position="90,250" size="60,60" font="Regular;48" halign="center" valign="center" foregroundColor="white" backgroundColor="#1f771f" cornerRadius="12"/>
        <eLabel text="Xtream Codes" position="170,250" size="200,60" font="Regular;28" halign="left" valign="center"/>

        <widget name="lab1" position="400,90"  size="450,60" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab2" position="400,170" size="450,60" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab3" position="400,250" size="450,60" font="Regular;24" halign="left" valign="center"/>

        <widget name="info"  position="30,340" size="840,40" font="Regular;22" halign="center" valign="center" foregroundColor="yellow"/>
        <widget name="status" position="30,390" size="840,30" font="Regular;20" halign="center" valign="center"/>

        <widget name="foot" position="30,460" size="840,35" font="Regular;20" halign="center" valign="center" foregroundColor="grey"/>
        <widget name="key_red"    position="0,495" size="225,25" font="Regular;20" halign="center" valign="center" foregroundColor="red"/>
        <widget name="key_green"  position="225,495" size="225,25" font="Regular;20" halign="center" valign="center" foregroundColor="green"/>
        <widget name="key_yellow" position="450,495" size="225,25" font="Regular;20" halign="center" valign="center" foregroundColor="yellow"/>
        <widget name="key_blue"   position="675,495" size="225,25" font="Regular;20" halign="center" valign="center" foregroundColor="blue"/>
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.playlist = []
        self.listname = "IPTV-Dream"

        self["key_red"] = Label("Zamknij")
        self["key_green"] = Label("EPG (Azman)")
        self["key_yellow"] = Label("Auto-aktualizacja")
        self["key_blue"] = Label("Eksport do bukietu")

        self["lab1"] = Label("Wczytaj listę z adresu URL")
        self["lab2"] = Label("Wskaż plik M3U z dysku")
        self["lab3"] = Label("Połącz się z API Xtream")

        self["info"] = Label("Naciśnij 1, 2 lub 3 aby wybrać źródło listy")
        self["status"] = Label("")
        self["foot"] = Label("IPTV Dream 2.0.0 | 2025-10-05 | by Paweł Pawelek | msisystem@t.pl")

        self["actions"] = ActionMap(["ColorActions", "NumberActions", "OkCancelActions"], {
            "1": self.openUrl,
            "2": self.openFile,
            "3": self.openXtream,
            "red": self.close,
            "green": self.installEPG,
            "yellow": self.toggleAutoUpdate,
            "blue": self.exportBouquet,
            "ok": self.openUrl,
            "cancel": self.close
        }, -1)

    # ----- źródła listy -----
    def openUrl(self):
        self.session.openWithCallback(self.onUrlReady, VKInputBox,
                                      title="Podaj adres listy M3U:",
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
            self.session.open(MessageBox, "Błąd pobierania: %s" % e, type=MessageBox.TYPE_ERROR, timeout=5)

    def openFile(self):
        self.session.openWithCallback(self.onFileReady, M3UFilePick, start_dir="/tmp/")

    def onFileReady(self, path):
        if not path:
            return
        try:
            with open(path, "rb") as f:
                data = f.read()
            playlist = parse_m3u_bytes(data)
            name = os.path.splitext(os.path.basename(path))[0] or "IPTV-Plik"
            self.onListLoaded(playlist, name)
        except Exception as e:
            self.session.open(MessageBox, "Błąd odczytu: %s" % e, type=MessageBox.TYPE_ERROR, timeout=5)

    def openXtream(self):
        self.session.openWithCallback(self.xtreamHost, VKInputBox,
                                      title="Xtream – host (http://...):",
                                      text="http://example.com")

    def xtreamHost(self, host):
        if not host:
            return
        self.xtream_host = host.rstrip("/")
        self.session.openWithCallback(self.xtreamUser, VKInputBox,
                                      title="Xtream – użytkownik:",
                                      text="")

    def xtreamUser(self, user):
        if not user:
            return
        self.xtream_user = user
        self.session.openWithCallback(self.xtreamPass, VKInputBox,
                                      title="Xtream – hasło:",
                                      text="")

    def xtreamPass(self, pwd):
        if not pwd:
            return
        m3u = f"{self.xtream_host}/get.php?username={self.xtream_user}&password={pwd}&type=m3u_plus&output=ts"
        try:
            with urllib.request.urlopen(m3u, timeout=15) as r:
                data = r.read()
            playlist = parse_m3u_bytes(data)
            prof = load_profiles()
            prof["last_url"] = m3u
            save_profiles(prof)
            self.onListLoaded(playlist, f"Xtream-{self.xtream_user}")
        except Exception as e:
            self.session.open(MessageBox, "Błąd Xtream: %s" % e, type=MessageBox.TYPE_ERROR, timeout=5)

    # ----- kolorowe akcje -----
    def exportBouquet(self):
        if not self.playlist:
            self.session.open(MessageBox, "Najpierw wczytaj listę (1/2/3)", type=MessageBox.TYPE_WARNING, timeout=4)
            return
        export_bouquets(self.playlist, bouquet_name=self.listname)
        self.session.open(MessageBox, "Bukiet wyeksportowany!\nZnajdziesz go w TV → Listy", type=MessageBox.TYPE_INFO, timeout=5)

    def installEPG(self):
        try:
            os.system("opkg update >/dev/null 2>&1")
            os.system("opkg install enigma2-plugin-extensions-xmltvimport epgimport >/dev/null 2>&1 || true")
            os.makedirs("/etc/epgimport", exist_ok=True)
            az_src = "/etc/epgimport/Azman.sources.xml"
            if not os.path.exists(az_src):
                with open(az_src, "w") as f:
                    f.write('<sources>\n\t<source type="gen_xmltv">http://example.com/azman.xml</source>\n</sources>\n')
            self.session.open(MessageBox, "EPG Import zainstalowany.\nUstaw źródło w Menu → EPG → EPG-Importer", type=MessageBox.TYPE_INFO, timeout=5)
        except Exception as e:
            self.session.open(MessageBox, "Błąd EPG: %s" % e, type=MessageBox.TYPE_ERROR, timeout=5)

    def toggleAutoUpdate(self):
        cron = "/etc/cron/crontabs/root"
        script = "/usr/lib/enigma2/python/Plugins/Extensions/IPTVDream/auto_update.sh"
        os.makedirs(os.path.dirname(cron), exist_ok=True)
        enabled = False
        if os.path.exists(cron):
            enabled = "IPTVDREAM_AUTO" in open(cron).read()
        if enabled:
            lines = [l for l in open(cron).read().splitlines() if "IPTVDREAM_AUTO" not in l]
            open(cron, "w").write("\n".join(lines) + ("\n" if lines else ""))
            self["status"].setText("Auto-aktualizacja wyłączona")
        else:
            with open(cron, "a") as f:
                f.write('0 5 * * * %s # IPTVDREAM_AUTO\n' % script)
            self["status"].setText("Auto-aktualizacja włączona (05:00)")

    def onListLoaded(self, playlist, name):
        self.playlist = playlist
        self.listname = name
        self["status"].setText("Wczytano %d kanałów – możesz wcisnąć NIEBIESKI by wyeksportować" % len(playlist))
