# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Label import Label
from Screens.VirtualKeyBoard import VirtualKeyBoard
from enigma import ePoint
from .lang import _

POS_BQT   = (20, 80)
POS_CH    = (450, 80)

class BouquetPicker(Screen):
    skin = """
    <screen name="BouquetPicker" position="center,center" size="1100,650" title="Bouquet Picker">
        <eLabel position="0,0" size="1100,60" backgroundColor="#202020" zPosition="-1" />
        <widget name="title_lbl" position="0,10" size="1100,40" font="Regular;30" halign="center" valign="center" foregroundColor="#ffcc00" backgroundColor="#202020" transparent="1" />
        <eLabel position="0,60" size="1100,2" backgroundColor="#333333" />

        <widget name="lbl_groups" position="20,70" size="300,30" font="Regular;22" foregroundColor="#00ccff" transparent="1" />
        <widget name="filter_lbl" position="200,70" size="230,30" font="Regular;20" halign="right" foregroundColor="yellow" transparent="1" />
        
        <widget name="lbl_channels" position="450,70" size="400,30" font="Regular;22" foregroundColor="#00ccff" transparent="1" />

        <widget name="bqt_list" position="20,110" size="410,450" scrollbarMode="showOnDemand" transparent="1" />
        <widget name="ch_list"  position="450,110" size="630,450" scrollbarMode="showOnDemand" transparent="1" />

        <eLabel position="0,570" size="1100,2" backgroundColor="#333333" />
        
        <widget name="sum" position="20,580" size="1060,30" font="Regular;22" halign="center" valign="center" foregroundColor="yellow"/>
        
        <widget name="lbl_ok" position="20,620" size="250,30" font="Regular;20" foregroundColor="#00ff00" />
        <widget name="lbl_blue" position="280,620" size="250,30" font="Regular;20" foregroundColor="#00ccff" />
        <widget name="lbl_yellow" position="540,620" size="250,30" font="Regular;20" foregroundColor="#ffff00" />
        <widget name="lbl_lr" position="800,620" size="250,30" font="Regular;20" foregroundColor="white" />

    </screen>
    """

    def __init__(self, session, groups):
        Screen.__init__(self, session)
        self.session = session
        from Components.Language import language
        self.lang = language.getLanguage()[:2] or "pl"
        
        self.groups  = groups
        self.all_group_keys = sorted(groups.keys()) # Pełna lista
        self.current_keys = list(self.all_group_keys) # Lista filtrowana
        self.selected = set()
        self.filter_text = ""
        
        self["title_lbl"] = Label(_("IPTV Dream - Wybór Bukietów", self.lang))
        self["lbl_groups"] = Label(_("Grupy (Zaznacz OK):", self.lang))
        self["lbl_channels"] = Label(_("Kanały w grupie:", self.lang))
        self["lbl_ok"] = Label(_("OK / ZIELONY = Zaznacz", self.lang))
        self["lbl_blue"] = Label(_("NIEBIESKI = Eksportuj", self.lang))
        self["lbl_yellow"] = Label(_("ŻÓŁTY = Szukaj", self.lang))
        self["lbl_lr"] = Label(_("LEWO/PRAWO = Zmień listę", self.lang))
        self["filter_lbl"] = Label("")
        self["bqt_list"] = MenuList([], enableWrapAround=True)
        self["ch_list"]  = MenuList([], enableWrapAround=True)
        
        self["sum"]      = Label(_("picker_sum", self.lang))
        self["hlight"]   = Label("") 
        
        self.focus_left = True 

        self["actions"] = ActionMap(["ColorActions", "OkCancelActions", "DirectionActions"], {
            "ok":     self.toggleSelect,
            "green":  self.toggleSelect,
            "blue":   self.save,
            "yellow": self.openSearch, # NOWOŚĆ
            "red":    self.cancel,
            "cancel": self.cancel,
            "up":     self.moveUp,
            "down":   self.moveDown,
            "left":   self.setLeft,
            "right":  self.setRight,
        }, -1)

        self.onLayoutFinish.append(self.startLayout)

    def startLayout(self):
        self.refreshList()
        self["bqt_list"].selectionEnabled(1)
        self["ch_list"].selectionEnabled(1)
        self.updatePreview()

    def openSearch(self):
        """Otwiera wyszukiwanie grup."""
        self.session.openWithCallback(self.onSearchDone, VirtualKeyBoard, 
                                     title=_("picker_search", self.lang), 
                                     text=self.filter_text)

    def onSearchDone(self, text):
        """Obsługuje wynik wyszukiwania."""
        if text is not None:
            self.filter_text = text.lower()
            self.applyFilter()

    def applyFilter(self):
        """Stosuje filtr do listy grup."""
        if not self.filter_text:
            self.current_keys = list(self.all_group_keys)
            self["filter_lbl"].setText("")
        else:
            self.current_keys = [k for k in self.all_group_keys if self.filter_text in k.lower()]
            self["filter_lbl"].setText(_("Filtr: %s", self.lang) % self.filter_text)
        
        self.refreshList()
        self.updatePreview()

    def refreshList(self):
        """Odświeża listę grup."""
        list_items = []
        for g in self.current_keys:
            prefix = "[ X ]" if g in self.selected else "[   ]"
            count  = len(self.groups[g])
            list_items.append(f"{prefix} {g} ({count})")
        self["bqt_list"].setList(list_items)
        self["bqt_list"].moveToIndex(0)

    def updatePreview(self):
        """Aktualizuje podgląd kanałów."""
        idx = self["bqt_list"].getSelectedIndex()
        if 0 <= idx < len(self.current_keys):
            key = self.current_keys[idx]
            chans = [c.get("title", "No Name") for c in self.groups[key]]
            self["ch_list"].setList(chans)
        else:
            self["ch_list"].setList([])
            
        if self.focus_left:
            self["bqt_list"].selectionEnabled(1)
            self["ch_list"].selectionEnabled(0)
        else:
            self["bqt_list"].selectionEnabled(0)
            self["ch_list"].selectionEnabled(1)
            
        cnt = sum(len(self.groups[k]) for k in self.selected)
        sum_txt = _("picker_sum_text", self.lang) % (len(self.selected), cnt)
        self["sum"].setText(sum_txt)

    def toggleSelect(self):
        """Zaznacza/odznacza grupę."""
        if not self.focus_left: 
            return
            
        idx = self["bqt_list"].getSelectedIndex()
        if 0 <= idx < len(self.current_keys):
            key = self.current_keys[idx]
            if key in self.selected: 
                self.selected.remove(key)
            else: 
                self.selected.add(key)
            
            # Odświeżamy widok
            self.refreshList()
            self["bqt_list"].moveToIndex(idx)
            self.updatePreview()

    def moveUp(self):
        """Przesuwa w górę."""
        if self.focus_left: 
            self["bqt_list"].up()
            self.updatePreview()
        else: 
            self["ch_list"].up()

    def moveDown(self):
        """Przesuwa w dół."""
        if self.focus_left: 
            self["bqt_list"].down()
            self.updatePreview()
        else: 
            self["ch_list"].down()
            
    def setLeft(self): 
        """Ustawia fokus na lewą listę."""
        self.focus_left = True
        self.updatePreview()
        
    def setRight(self): 
        """Ustawia fokus na prawą listę."""
        self.focus_left = False
        self.updatePreview()

    def save(self):
        """Zapisuje wybrane grupy."""
        self.close(list(self.selected))

    def cancel(self):
        """Anuluje wybór."""
        self.close(None)