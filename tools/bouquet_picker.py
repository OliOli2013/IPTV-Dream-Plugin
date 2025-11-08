# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.MenuList import MenuList
from Components.Label import Label
from Components.ActionMap import ActionMap

class BouquetPicker(Screen):
    skin = """
    <screen position="center,center" size="500,440" title="Wybór bukietów do eksportu">
        <widget name="list" position="10,10" size="480,350" scrollbarMode="showOnDemand"/>
        <widget name="key_red"   position="0,390" size="250,30" font="Regular;20" halign="center" foregroundColor="red"/>
        <widget name="key_green" position="250,390" size="250,30" font="Regular;20" halign="center" foregroundColor="green"/>
    </screen>"""

    def __init__(self, session, groups_dict):
        Screen.__init__(self, session)
        self.setTitle("Zaznacz bukiety do eksportu")
        self.groups = sorted(groups_dict.keys())
        self["list"] = MenuList([ (g, g) for g in self.groups ], enableWrapAround=True)
        self["key_red"]   = Label("Anuluj")
        self["key_green"] = Label("Eksportuj zaznaczone")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.toggle, "cancel": self.cancel,
            "red": self.cancel, "green": self.ok
        }, -1)
        self.selected = set()

    def toggle(self):
        cur = self["list"].getCurrent()
        if not cur: return
        g = cur[0]
        if g in self.selected:
            self.selected.remove(g)
        else:
            self.selected.add(g)
        self.rebuild_list()

    def rebuild_list(self):
        items = []
        for g in self.groups:
            mark = "[✓] " if g in self.selected else "[  ] "
            items.append((mark + g, g))
        self["list"].setList(items)

    def ok(self):
        self.close(list(self.selected))

    def cancel(self):
        self.close(None)
