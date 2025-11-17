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
        <eLabel text="STRZAŁKI: Nawigacja | OK/ZIELONY: Zaznacz | NIEBIESKI: Eksportuj | LEWO/PRAWO: Zmień listę" position="10,560" size="1080,40" font="Regular;20" halign="center" valign="center" />
    </screen>
    """

    def __init__(self, session, groups):
        Screen.__init__(self, session)
        self.session = session
        self.groups  = groups
        self.group_keys = sorted(groups.keys())
        self.selected = set()
        
        self["bqt_list"] = MenuList([], enableWrapAround=True)
        self["ch_list"]  = MenuList([], enableWrapAround=True)
        
        self["sum"]      = Label("Wybierz grupy do eksportu")
        self["hlight"]   = Label("")
        
        self.focus_left = True # True = lewa lista

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
        # Ustawiamy domyślnie selekcję na 0 (pierwszy element)
        self["bqt_list"].selectionEnabled(1)
        self["ch_list"].selectionEnabled(1)
        self.updatePreview()

    def refreshList(self):
        # Zachowaj aktualną pozycję kursora, jeśli to możliwe
        old_idx = self["bqt_list"].getSelectedIndex()
        
        list_items = []
        for g in self.group_keys:
            prefix = "[x]" if g in self.selected else "[ ]"
            count  = len(self.groups[g])
            list_items.append(f"{prefix} {g} ({count})")
        
        self["bqt_list"].setList(list_items)
        
        # Przywróć kursor na stare miejsce
        if old_idx is not None and old_idx < len(list_items):
            self["bqt_list"].moveToIndex(old_idx)

    def updatePreview(self):
        idx = self["bqt_list"].getSelectedIndex()
        if 0 <= idx < len(self.group_keys):
            key = self.group_keys[idx]
            # Pokazujemy tylko nazwy kanałów
            chans = [c.get("title", "No Name") for c in self.groups[key]]
            self["ch_list"].setList(chans)
        else:
            self["ch_list"].setList([])
            
        # Aktualizacja podświetlenia
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
        self["sum"].setText(f"Wybrano: {len(self.selected)} grup, {cnt} kanałów")

    def toggleSelect(self):
        # Działa tylko gdy jesteśmy na lewej liście (bukietów)
        if not self.focus_left:
            return

        idx = self["bqt_list"].getSelectedIndex()
        if 0 <= idx < len(self.group_keys):
            key = self.group_keys[idx]
            if key in self.selected:
                self.selected.remove(key)
            else:
                self.selected.add(key)
            
            # Odświeżamy listę, co zaktualizuje [x] / [ ]
            self.refreshList()
            # Update preview też odświeży licznik
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
        if not self.selected:
             # Jeśli nic nie wybrano, a użytkownik klika eksport, 
             # możemy albo nic nie robić, albo zapytać "czy wszystko?"
             # Tutaj dla bezpieczeństwa zwracamy pustą listę = anuluj
             pass
        self.close(list(self.selected))

    def cancel(self):
        self.close(None)
