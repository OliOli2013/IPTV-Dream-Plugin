# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Label import Label
from enigma import ePoint
from .lang import _  # Import tłumaczeń

POS_BQT   = (5, 5)
POS_CH    = (425, 5)

class BouquetPicker(Screen):
    skin = """
    <screen name="BouquetPicker" position="center,center" size="1100,620" title="Wybór bukietów">
        <widget name="hlight" position="5,5" size="410,460" zPosition="-1" backgroundColor="#1f771f" cornerRadius="8"/>
        <widget name="bqt_list" position="10,10" size="400,450" scrollbarMode="showOnDemand"/>
        <widget name="ch_list"  position="430,10" size="650,450" scrollbarMode="showOnDemand"/>
        <widget name="sum" position="10,480" size="1080,30" font="Regular;22" halign="center" valign="center" foregroundColor="yellow"/>
        
        <widget name="key_help" position="10,560" size="1080,40" font="Regular;20" halign="center" valign="center" />
    </screen>
    """

    def __init__(self, session, groups):
        Screen.__init__(self, session)
        self.session = session
        from Components.Language import language
        self.lang = language.getLanguage()[:2] or "pl"
        
        self.groups  = groups
        self.group_keys = sorted(groups.keys())
        self.selected = set()
        
        self["bqt_list"] = MenuList([], enableWrapAround=True)
        self["ch_list"]  = MenuList([], enableWrapAround=True)
        
        self["sum"]      = Label(_("picker_sum", self.lang))
        self["hlight"]   = Label("")
        
        # TŁUMACZENIE POMOCY
        self["key_help"] = Label(_("picker_help", self.lang))
        
        self.focus_left = True 

        self["actions"] = ActionMap(["ColorActions", "OkCancelActions", "DirectionActions"], {
            "ok":     self.toggleSelect,
            "green":  self.toggleSelect,
            "blue":   self.save,
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

    def refreshList(self):
        old_idx = self["bqt_list"].getSelectedIndex()
        list_items = []
        for g in self.group_keys:
            prefix = "[x]" if g in self.selected else "[ ]"
            count  = len(self.groups[g])
            list_items.append(f"{prefix} {g} ({count})")
        self["bqt_list"].setList(list_items)
        if old_idx is not None and old_idx < len(list_items):
            self["bqt_list"].moveToIndex(old_idx)

    def updatePreview(self):
        idx = self["bqt_list"].getSelectedIndex()
        if 0 <= idx < len(self.group_keys):
            key = self.group_keys[idx]
            chans = [c.get("title", "No Name") for c in self.groups[key]]
            self["ch_list"].setList(chans)
        else:
            self["ch_list"].setList([])
            
        if self["hlight"].instance:
            if self.focus_left:
                self["hlight"].instance.move(ePoint(POS_BQT[0], POS_BQT[1]))
                if self["bqt_list"].instance:
                    self["hlight"].instance.resize(self["bqt_list"].instance.size())
            else:
                self["hlight"].instance.move(ePoint(POS_CH[0], POS_CH[1]))
                if self["ch_list"].instance:
                    self["hlight"].instance.resize(self["ch_list"].instance.size())
            
        cnt = sum(len(self.groups[k]) for k in self.selected)
        # Tłumaczenie podsumowania
        sum_txt = _("picker_sum_text", self.lang) % (len(self.selected), cnt)
        self["sum"].setText(sum_txt)

    def toggleSelect(self):
        if not self.focus_left: return
        idx = self["bqt_list"].getSelectedIndex()
        if 0 <= idx < len(self.group_keys):
            key = self.group_keys[idx]
            if key in self.selected: self.selected.remove(key)
            else: self.selected.add(key)
            self.refreshList()
            self.updatePreview()

    def moveUp(self):
        if self.focus_left: self["bqt_list"].up(); self.updatePreview()
        else: self["ch_list"].up()

    def moveDown(self):
        if self.focus_left: self["bqt_list"].down(); self.updatePreview()
        else: self["ch_list"].down()
            
    def setLeft(self): self.focus_left = True; self.updatePreview()
    def setRight(self): self.focus_left = False; self.updatePreview()

    def save(self):
        self.close(list(self.selected))

    def cancel(self):
        self.close(None)
