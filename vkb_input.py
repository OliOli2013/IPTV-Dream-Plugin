# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard   # <<== correct import
from Components.Input import Input
from Components.Label import Label
from Components.ActionMap import ActionMap

class VKInputBox(Screen):
    skin = """
    <screen name="VKInputBox" position="center,center" size="600,300" title="Wprowadź dane">
        <widget name="text"   position="30,20"  size="540,60"  font="Regular;24" halign="center" valign="center"/>
        <widget name="input"  position="30,100" size="540,40"  font="Regular;26" halign="center" valign="center" transparent="0"/>
        <widget name="help"   position="30,160" size="540,30"  font="Regular;20" halign="center" valign="center" foregroundColor="grey"/>
    </screen>
    """

    def __init__(self, session, title="", text=""):
        Screen.__init__(self, session)
        self.setTitle(title)
        self.input = Input(text)
        self["text"]  = Label(title)
        self["input"] = self.input
        self["help"]  = Label("OK=zapisz  EXIT=anuluj  ←→=znaki  ↕=kursor")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok":     self.ok,
            "cancel": self.cancel,
            "green":  self.ok,
            "red":    self.cancel,
        }, -1)
        self.onFirstExecBegin.append(self.openVKB)

    def openVKB(self):
        self.session.openWithCallback(self.vkbDone, VirtualKeyBoard,
                                      title=self["text"].getText(),
                                      text=self.input.getText())

    def vkbDone(self, text):
        if text is not None:
            self.input.setText(text)
            self.close(text)
        else:
            self.cancel()

    def ok(self):
        self.close(self.input.getText())

    def cancel(self):
        self.close(None)
