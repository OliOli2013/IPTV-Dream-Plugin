# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Label import Label
from enigma import ePoint

POS_BQT   = (5, 5)
POS_CH    = (425, 5)
SIZE      = (410, 460)
CLR_ACT   = "#1f771f"   # zielony – aktywna lista
CLR_SEL   = "#800080"   # fiolet – zaznaczony bukiet
CLR_CH    = "#555555"   # szary – tło kanałów

class BouquetPicker(Screen):
    skin = """
    <screen name="BouquetPicker" position="center,center" size="1100,620" title="Wybór bukietów i kanałów">
        <widget name="hlight" position="5,5" size="410,460" zPosition="-1"
                font="Regular;1" halign="center" valign="center"
                backgroundColor="#1f771f" cornerRadius="8"/>

        <widget name="bqt_list" position="10,10" size="400,450" scrollbarMode="showOnDemand"/>
        <widget name="ch_list"  position="430,10" size="650,450" scrollbarMode="showOnDemand"/>

        <widget name="sum" position="10,480" size="1080,30" font="Regular;22" halign="center" valign="center" foregroundColor="yellow"/>

        <ePixmap pixmap="buttons/red.png"    position="20,560" size="140,40" alphatest="on"/>
        <ePixmap pixmap="buttons/green.png"  position="180,560" size="140,40" alphatest="on"/>
        <ePixmap pixmap="buttons/yellow.png" position="340,560" size="140,40" alphatest="on"/>
        <ePixmap pixmap="buttons/blue.png"   position="900,560" size="140,40" alphatest="on"/>

        <widget source="key_red"    render="Label" position="20,560"  size="140,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1"/>
        <widget source="key_green"  render="Label" position="180,560" size="140,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1"/>
        <widget source="key_yellow" render="Label" position="340,560" size="140,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1"/>
        <widget source="key_blue"   render="Label" position="900,560" size="140,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1"/>

        <widget name="help" position="10,520" size="1080,30" font="Regular;18" halign="center" valign="center" foregroundColor="grey"/>
    </screen>
    """

    def __init__(self, session, groups):
        Screen.__init__(self, session)
        self.session = session
        self.groups  = groups
        self.setTitle("Wybór bukietów i kanałów")

        self["key_red"]    = Label("Anuluj")
        self["key_green"]  = Label("Zaznacz")
        self["key_yellow"] = Label("Odznacz")
        self["key_blue"]   = Label("Dodaj zaznaczone")
        self["help"]       = Label("↑/↓ – nawigacja, ←/→ – przełącz listę, Zielony/Żółty – zaznacz/odznacz, Niebieski – zatwierdź")
        self["sum"]        = Label("")

        self["bqt_list"] = MenuList([])
        self["ch_list"]  = MenuList([])

        # ruchoma ramka
        self["hlight"] = Label("")
        self.sel   = set()
        self.focus = "left"

        self["actions"] = ActionMap(["ColorActions", "OkCancelActions", "DirectionActions"],
        {
            "ok":     self.swapFocus,
            "left":   self.moveLeft,
            "right":  self.moveRight,
            "up":     self.moveUp,
            "down":   self.moveDown,
            "green":  self.markBouquet,
            "yellow": self.unmarkBouquet,
            "blue":   self.accept,
            "red":    self.cancel,
            "cancel": self.cancel
        }, -1)

        self.reloadBouquets()
        self.previewChannels()
        self.updateSummary()
        self.updateHighlight()

    # ---------- podświetlenie + podsumowanie ----------
    def updateHighlight(self):
        x, y = (POS_BQT if self.focus == "left" else POS_CH)
        if self["hlight"].instance:
            self["hlight"].instance.move(ePoint(x, y))

    def updateSummary(self):
        cnt = sum(len(self.groups[b]) for b in self.sel)
        buq = len(self.sel)
        self["sum"].setText(f"Zaznaczono: {buq} bukiet(-ów), {cnt} kanał(-ów)")

    # ---------- nawigacja ----------
    def swapFocus(self):
        self.focus = "right" if self.focus == "left" else "left"
        self.updateHighlight()

    # === ZMIANA: Poprawiono logikę - lewo/prawo tylko przełącza fokus ===
    def moveLeft(self):
        if self.focus == "right":
            self.focus = "left"
            self.updateHighlight()
            self.previewChannels() # Aktualizujemy podgląd po zmianie fokusu na listę bukietów

    def moveRight(self):
        if self.focus == "left":
            self.focus = "right"
            self.updateHighlight()
    # === KONIEC ZMIANY ===

    def moveUp(self):
        if self.focus == "left":
            self["bqt_list"].up()
            self.previewChannels()
        else:
            self["ch_list"].up()

    def moveDown(self):
        if self.focus == "left":
            self["bqt_list"].down()
            self.previewChannels()
        else:
            self["ch_list"].down()

    # ---------- logika ----------
    def reloadBouquets(self):
        items = []
        # Sortowanie kluczy (nazw grup) alfabetycznie dla porządku
        sorted_groups = sorted(self.groups.keys())
        for b in sorted_groups:
            mark = "☑" if b in self.sel else "☐"
            # Używamy `len(self.groups[b])` aby pokazać liczbę kanałów
            items.append(f"{mark} {b} ({len(self.groups[b])})")
        self["bqt_list"].setList(items)

    def previewChannels(self):
        idx = self["bqt_list"].getSelectedIndex()
        sorted_groups = sorted(self.groups.keys())
        if idx >= len(sorted_groups):
            self["ch_list"].setList([])
            return
        
        b = sorted_groups[idx]
        ch = [c['title'] for c in self.groups.get(b, [])]
        self["ch_list"].setList(ch)

    def markBouquet(self):
        idx = self["bqt_list"].getSelectedIndex()
        sorted_groups = sorted(self.groups.keys())
        if idx < len(sorted_groups):
            b = sorted_groups[idx]
            self.sel.add(b)
            self.reloadBouquets()
            self.previewChannels()
            self.updateSummary()

    def unmarkBouquet(self):
        idx = self["bqt_list"].getSelectedIndex()
        sorted_groups = sorted(self.groups.keys())
        if idx < len(sorted_groups):
            b = sorted_groups[idx]
            self.sel.discard(b)
            self.reloadBouquets()
            self.previewChannels()
            self.updateSummary()

    # ➜ ZWRACAMY TYLKO NAZWY BUKIETÓW (string-i) – bezpieczne klucze
    def accept(self):
        selected = list(self.sel)        # ⬅ string-i, nie dict-y
        self.close(selected)

    def cancel(self):
        self.close([])
