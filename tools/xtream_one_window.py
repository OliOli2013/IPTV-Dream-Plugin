# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Input import Input
from ..vkb_input import VKInputBox

class XtreamOneWindow(Screen):
    skin = """
    <screen position="center,center" size="600,320" title="Xtream-Codes – dane logowania">
        <widget name="head"  position="30,20"  size="540,40" font="Regular;26" halign="center"/>
        <widget name="host_l" position="30,80"  size="100,30" font="Regular;22" halign="left"  valign="center"/>
        <widget name="host"   position="140,80" size="430,30" font="Regular;22" halign="left"/>
        <widget name="user_l" position="30,130" size="100,30" font="Regular;22" halign="left"  valign="center"/>
        <widget name="user"   position="140,130" size="430,30" font="Regular;22" halign="left"/>
        <widget name="pass_l" position="30,180" size="100,30" font="Regular;22" halign="left"  valign="center"/>
        <widget name="pass"   position="140,180" size="430,30" font="Regular;22" halign="left"/>
        <widget name="key_red"   position="0,280" size="300,30" font="Regular;20" halign="center" foregroundColor="red"/>
        <widget name="key_green" position="300,280" size="300,30" font="Regular;20" halign="center" foregroundColor="green"/>
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self["head"]   = Label("Wprowadź dane Xtream-Codes")
        self["host_l"] = Label("Host:")
        self["user_l"] = Label("User:")
        self["pass_l"] = Label("Pass:")
        self["host"]   = Input("")
        self["user"]   = Input("")
        self["pass"]   = Input("")
        self["key_red"]   = Label("Anuluj")
        self["key_green"] = Label("Zapisz")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "red": self.cancel, "green": self.ok, "cancel": self.cancel
        }, -1)
        self.onExecBegin.append(self.open_vkb_host)

    def open_vkb_host(self):
        self.session.openWithCallback(self.set_host, VKInputBox, title="Host (http...):", text=self["host"].getText())

    def set_host(self, txt):
        if txt:
            self["host"].setText(txt)
            self.open_vkb_user()
        else:
            self.cancel()

    def open_vkb_user(self):
        self.session.openWithCallback(self.set_user, VKInputBox, title="Username:", text=self["user"].getText())

    def set_user(self, txt):
        if txt:
            self["user"].setText(txt)
            self.open_vkb_pass()
        else:
            self.cancel()

    def open_vkb_pass(self):
        self.session.openWithCallback(self.set_pass, VKInputBox, title="Password:", text=self["pass"].getText())

    def set_pass(self, txt):
        if txt:
            self["pass"].setText(txt)
        else:
            self.cancel()

    def ok(self):
        self.close((self["host"].getText(), self["user"].getText(), self["pass"].getText()))

    def cancel(self):
        self.close(None)
