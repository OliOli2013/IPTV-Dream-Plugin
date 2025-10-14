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
from .tools.xtream_one_window import XtreamOneWindow
from .tools.bouquet_picker    import BouquetPicker
from .tools.epg_picon         import fetch_epg_for_playlist, download_picon_url
import os, json, urllib.request, requests

PROFILES      = "/etc/enigma2/iptvdream_profiles.json"
MY_LINKS_FILE = "/etc/enigma2/iptvdream_mylinks.json"
USER_M3U_FILE = "/etc/enigma2/iptvdream_user_m3u.json"

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
    <screen name="IPTVDreamMain" position="center,center" size="950,680" title="IPTV Dream v2.2">
        <!-- NAGŁÓWEK -->
        <eLabel text="IPTV Dream v2.2" position="700,10" size="230,35" font="Regular;28" halign="right" valign="center" foregroundColor="yellow" backgroundColor="#1f771f" cornerRadius="8"/>

        <!-- 6 ŹRÓDEŁ – kompaktowe -->
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

        <!-- OPISY PO PRAWEJ -->
        <widget name="lab1" position="380,80"  size="520,70" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab2" position="380,160" size="520,70" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab3" position="380,240" size="520,70" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab4" position="380,320" size="520,70" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab5" position="380,400" size="520,70" font="Regular;24" halign="left" valign="center"/>
        <widget name="lab6" position="380,480" size="520,70" font="Regular;24" halign="left" valign="center"/>

        <!-- STATUS -->
        <widget name="info"   position="30,560" size="890,30" font="Regular;22" halign="center" valign="center" foregroundColor="yellow"/>
        <widget name="status" position="30,590" size="890,25" font="Regular;20" halign="center" valign="center"/>

        <!-- PRZYCISKI -->
        <widget name="key_red"    position="0,620" size="237,25" font="Regular;20" halign="center" valign="center" foregroundColor="red"/>
        <widget name="key_green"  position="237,620" size="237,25" font="Regular;20" halign="center" valign="center" foregroundColor="green"/>
        <widget name="key_yellow" position="474,620" size="237,25" font="Regular;20" halign="center" valign="center" foregroundColor="yellow"/>
        <widget name="key_blue"   position="711,620" size="237,25" font="Regular;20" halign="center" valign="center" foregroundColor="blue"/>

        <!-- STOPKA -->
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
        self["foot"]   = Label("IPTV Dream v2.2 | by Paweł Pawelek | msisystem@t.pl")

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

    # 1) M3U URL ----------------------------------------------------------
    def openUrl(self):
        self.session.openWithCallback(self.onUrlOrJson, VKInputBox,
                                      title=_("Wklej link M3U lub JSON:", self.lang),
                                      text="")
    def onUrlOrJson(self, txt):
        if not txt:
            self.session.openWithCallback(self.onUrlReady, VKInputBox,
                                          title=_("load_url", self.lang),
                                          text="http://")
            return
        try:
            data = json.loads(txt)
            if isinstance(data, list) and all("url" in x for x in data):
                menu = [(x["name"], x["url"]) for x in data]
                self.session.openWithCallback(self.onMyLink, ChoiceBox,
                                              title=_("Wybierz link:", self.lang),
                                              list=menu)
                return
        except Exception:
            pass
        self.onUrlReady(txt.strip())

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

    # 2) M3U plik ---------------------------------------------------------
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

    # 3) Xtream -----------------------------------------------------------
    def openXtream(self):
        # ===== AUTOMATYCZNE wczytanie pliku =====
        xtream_file = "/etc/enigma2/iptvdream_xtream.json"
        if os.path.isfile(xtream_file):
            try:
                with open(xtream_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if all(k in cfg for k in ("host", "user", "pass")):
                    # od razu przekazujemy dane – użytkownik tylko ENTER
                    self.onXtreamOne((cfg["host"], cfg["user"], cfg["pass"]))
                    return
            except Exception:
                pass
        # ===== standardowo – okno ręczne =====
        self.session.openWithCallback(self.onXtreamOne, XtreamOneWindow)

    def onXtreamOne(self, data):
        if not data:
            return
        host, user, pwd = data
        try:
            with urllib.request.urlopen(f"{host}/get.php?username={user}&password={pwd}&type=m3u_plus&output=ts", timeout=15) as r:
                data = r.read()
            playlist = parse_m3u_bytes(data)
            fetch_epg_for_playlist(playlist)
            for ch in playlist:
                ch["picon"] = download_picon_url(ch.get("logo", ""), ch["title"])
            self.onListLoaded(playlist, f"Xtream-{user}")
        except Exception as e:
            self.session.open(MessageBox, "Xtream error: " + str(e), MessageBox.TYPE_ERROR, timeout=5)

    # 4) MAC Portal -------------------------------------------------------
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
            fetch_epg_for_playlist(playlist)
            for ch in playlist:
                ch["picon"] = download_picon_url(ch.get("logo", ""), ch["title"])
            save_mac_json(self.data)
            self.onListLoaded(playlist, "MAC-Portal")
        except Exception as e:
            self.session.open(MessageBox, "MAC error: " + str(e), MessageBox.TYPE_ERROR, timeout=5)

    # 5) Własne linki -----------------------------------------------------
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

    # 6) Zmiana języka ----------------------------------------------------
    def toggleLang(self):
        self.lang = "en" if self.lang == "pl" else "pl"
        prof = load_profiles()
        prof["lang"] = self.lang
        save_profiles(prof)
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
        self["foot"].setText("IPTV Dream v2.2 | by Paweł Pawelek | msisystem@t.pl")
        self.session.open(MessageBox, _("lang_changed", self.lang) + " " + self.lang.upper(),
                          MessageBox.TYPE_INFO, timeout=2)

    # ---------- GREEN – check updates -----------------------------------
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

    # ---------- YELLOW – auto-update cron -------------------------------
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

    # ---------- BLUE – export z wyborem bukietów ------------------------
    def exportBouquet(self):
        if not self.playlist:
            self.session.open(MessageBox, _("load_first", self.lang),
                              MessageBox.TYPE_WARNING, timeout=4)
            return

        # 1. tworzymy SŁOWNIK:  {nazwa_bukietu: [kanały]}
        groups = {}
        for ch in self.playlist:
            g = ch.get("group", "").strip() or (ch["title"].split()[0] if ch["title"] else "Inne")
            groups.setdefault(g, []).append(ch)

        if groups:
            # 2. otwieramy OKNO – przekazujemy SŁOWNIK
            self.session.openWithCallback(self.onBouquetsChosen, BouquetPicker, groups)
            self._groups = groups          # zachowujemy do odczytu
            self._name   = self.listname
        else:
            self.finishLoad(self.playlist, self.listname)

    # 3. odbieramy LISTĘ NAZW (string-i) – bezpieczne klucze
    def onBouquetsChosen(self, selected):
        """
        selected = lista NAZW bukietów (str) zaznaczonych przez użytkownika
        BEZPIECZNIE – pomijamy elementy które nie są stringami
        """
        if not selected:
            return
        final = []
        for g in selected:
            # ➜ ZABEZPIECZENIE: tylko stringi mogą być kluczami
            if isinstance(g, str) and g in self._groups:
                final.extend(self._groups[g])
        self.finishLoad(final, self._name)

    def finishLoad(self, playlist, name):
        self.playlist = playlist
        self.listname = name
        self["status"].setText(_("loaded", self.lang) % len(playlist))
        # osobny plik dla każdej grupy – zachowujemy oryginalne nazwy
        export_bouquets(playlist, bouquet_name=None, keep_groups=True)
        self.session.open(MessageBox, f"Eksport zakończony!\n{len(playlist)} kanałów w {len(set(ch.get('group','') for ch in playlist))} bukietach.",
                          MessageBox.TYPE_INFO, timeout=3)

    # -------------  UNIWERSALNA METODA – OTWIERA OKNO WYBORU  -------------
    def onListLoaded(self, playlist, name):
        """wywoływana gdy lista M3U/MAC/Xtream została pobrana i sparsowana"""
        if not playlist:
            self.session.open(MessageBox,
                              "Plik nie zawiera kanałów lub błędny format.",
                              MessageBox.TYPE_WARNING, timeout=4)
            return
        self.playlist = playlist
        self.listname = name
        self["status"].setText("Załadowano {} kanałów – NIEBIESKI=eksport".format(len(playlist)))
        # ➜ automatycznie otwiera OKNO WYBORU BUKIETÓW dla źródeł 1-4
        self.exportBouquet()

    # ---------- wyjście ----------
    def cancel(self):
        self.close()
