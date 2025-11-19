# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.Input import Input
from Components.Label import Label
from Components.ActionMap import ActionMap

class VKInputBox(Screen):
    # Jeszcze większe okno (900x400)
    skin = """
    <screen name="VKInputBox" position="center,center" size="900,400" title="Wprowadź dane">
        <widget name="text"   position="20,20"  size="860,60"  font="Regular;28" halign="center" valign="center"/>
        <widget name="input"  position="20,100" size="860,60"  font="Regular;24" halign="left" valign="center" transparent="0" backgroundColor="#202020"/>
        <widget name="help"   position="20,200" size="860,40"  font="Regular;22" halign="center" valign="center" foregroundColor="grey"/>
        <eLabel text="OK: Edytuj (Klawiatura) | ZIELONY: Zapisz | EXIT: Anuluj" position="20,320" size="860,40" font="Regular;24" halign="center" valign="center" foregroundColor="yellow"/>
    </screen>
    """

    def __init__(self, session, title="", text=""):
        Screen.__init__(self, session)
        self.setTitle(title)
        self.input = Input(text)
        self["text"]  = Label(title)
        self["input"] = self.input
        # Zmieniamy komunikat pomocy na bardziej sensowny:
        self["help"]  = Label("Naciśnij OK, aby otworzyć pełną klawiaturę i edytować dane.") 
        
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok":     self.openVKB,
            "cancel": self.cancel,
            "green":  self.ok,
            "red":    self.cancel,
        }, -1)
        
        # USUNIĘTO: self.onLayoutFinish.append(lambda: reactor.callLater(0.1, self.openVKB))

    def openVKB(self):
        self.session.openWithCallback(self.vkbDone, VirtualKeyBoard,
                                      title=self["text"].getText(),
                                      text=self.input.getText())

    def vkbDone(self, text):
        if text is not None:
            self.input.setText(text)
            self.close(text)

    def ok(self):
        self.close(self.input.getText())

    def cancel(self):
        self.close(None)
