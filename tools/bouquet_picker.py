# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Label import Label
from enigma import ePoint

POS_BQT   = (5, 5)
POS_CH    = (425, 5)

class BouquetPicker(Screen):
    skin = """
    <screen name="BouquetPicker" position="center,center" size="1100,620" title="Wybór bukietów">
        <widget name="hlight" position="5,5" size="410,460" zPosition="-1" backgroundColor="#1f771f" cornerRadius="8"/>
        <widget name="bqt_list" position="10,10" size="400,450" scrollbarMode="showOnDemand"/>
        <widget name="ch_list"  position="430,10" size="650,450" scrollbarMode="showOnDemand"/>
        <widget name="sum" position="10,480" size="1080,30" font="Regular;22" halign="center" valign="center" foregroundColor="yellow"/>
        <eLabel text="CZERWONY: Anuluj  |  ZIELONY: Zaznacz  |  NIEBIESKI: Eksportuj" position="10,560" size="1080,40" font="Regular;20" halign="center" valign="center" />
    </screen>
    """

    def __init__(self, session, groups):
        Screen.__init__(self, session)
        self.session = session
        self.groups  = groups
        self.group_keys = sorted(groups.keys()) # Utrzymujemy stałą kolejność
        self.selected = set()
        
        self["bqt_list"] = MenuList([], enableWrapAround=True, content=list)
        self["ch_list"]  = MenuList([], enableWrapAround=True, content=list)
        self["sum"]      = Label("Wybierz grupy do eksportu")
        self["hlight"]   = Label("")
        
        self.focus_left = True # True = lewa lista, False = prawa

        self["actions"] = ActionMap(["ColorActions", "OkCancelActions", "DirectionActions"], {
            "ok":     self.toggleSelect, # OK działa jak zaznacz
            "green":  self.toggleSelect,
            "blue":   self.save,
            "red":    self.cancel,
            "cancel": self.cancel,
            "up":     self.moveUp,
            "down":   self.moveDown,
            "left":   self.setLeft,
            "right":  self.setRight,
        }, -1)

        self.refreshList()
        self.updatePreview()

    def refreshList(self):
        # Budowanie listy wyświetlanej
        list_items = []
        for g in self.group_keys:
            prefix = "[x]" if g in self.selected else "[ ]"
            count  = len(self.groups[g])
            list_items.append(f"{prefix} {g} ({count})")
        
        self["bqt_list"].setList(list_items)
        # Przywrócenie starego indeksu jeśli możliwy
        # (MenuList w Enigmie czasem resetuje index przy setList, więc warto uważać)

    def updatePreview(self):
        idx = self["bqt_list"].getSelectedIndex()
        if 0 <= idx < len(self.group_keys):
            key = self.group_keys[idx]
            chans = [c.get("title","") for c in self.groups[key]]
            self["ch_list"].setList(chans)
        else:
            self["ch_list"].setList([])
            
        # Highlight update
        if self.focus_left:
            self["hlight"].instance.move(ePoint(POS_BQT[0], POS_BQT[1]))
            self["hlight"].instance.resize(self["bqt_list"].instance.size())
        else:
            self["hlight"].instance.move(ePoint(POS_CH[0], POS_CH[1]))
            self["hlight"].instance.resize(self["ch_list"].instance.size())
            
        cnt = sum(len(self.groups[k]) for k in self.selected)
        self["sum"].setText(f"Wybrano: {len(self.selected)} grup, {cnt} kanałów")

    def toggleSelect(self):
        idx = self["bqt_list"].getSelectedIndex()
        if 0 <= idx < len(self.group_keys):
            key = self.group_keys[idx]
            if key in self.selected:
                self.selected.remove(key)
            else:
                self.selected.add(key)
            self.refreshList()
            self["bqt_list"].setSelectedIndex(idx) # Przywróć kursor
            self.updatePreview()

    def moveUp(self):
        if self.focus_left:
            self["bqt_list"].up()
            self.updatePreview()
        else:
            self["ch_list"].up()

    def moveDown(self):
        if self.focus_left:
            self["bqt_list"].down()
            self.updatePreview()
        else:
            self["ch_list"].down()
            
    def setLeft(self):
        self.focus_left = True
        self.updatePreview()
        
    def setRight(self):
        self.focus_left = False
        self.updatePreview()

    def save(self):
        self.close(list(self.selected))

    def cancel(self):
        self.close(None)
