# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.Sources.StaticText import StaticText
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Input import Input
from enigma import ePoint
from ..vkb_input import VKInputBox 
from ..tools.lang import _
from Components.Language import language

# współrzędne ramki dla każdego pola
POS = [(225, 15),   # host
       (225, 65),   # user
       (225, 115)]  # pass

class XtreamOneWindow(Screen):
    """Okno dla Xtream Codes"""
    
    skin = """
    <screen name="XtreamOneWindow" position="center,center" size="600,380" title="Xtream Codes – nawigacja">

        <eLabel text="Host (z portem):" position="20,20"  size="200,30" font="Regular;22" halign="left"  valign="center"/>
        <eLabel text="Username:"        position="20,70"  size="200,30" font="Regular;22" halign="left"  valign="center"/>
        <eLabel text="Password:"        position="20,120" size="200,30" font="Regular;22" halign="left"  valign="center"/>

        <widget name="host" position="230,20"  size="350,35" font="Regular;22" halign="left" valign="center" transparent="1"/>
        <widget name="user" position="230,70"  size="350,35" font="Regular;22" halign="left" valign="center" transparent="1"/>
        <widget name="pass" position="230,120" size="350,35" font="Regular;22" halign="left" valign="center" transparent="1"/>

        <widget name="hlight" position="225,15" size="360,45" zPosition="-1"
                font="Regular;1" halign="center" valign="center"
                backgroundColor="#1f771f" cornerRadius="8"/>

        <ePixmap pixmap="buttons/red.png"   position="20,320" size="140,40" alphatest="on"/>
        <ePixmap pixmap="buttons/green.png" position="440,320" size="140,40" alphatest="on"/>
        <widget source="key_red"   render="Label" position="20,320"  size="140,40" zPosition="1"
                font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1"/>
        <widget source="key_green" render="Label" position="440,320" size="140,40" zPosition="1"
                font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1"/>

        <widget name="help" position="20,270" size="560,40" font="Regular;18"
                halign="center" valign="center" foregroundColor="yellow"/>
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.lang = language.getLanguage()[:2] or "pl"
        
        self.setTitle(_("xtream_title", self.lang))
        self["key_red"]   = StaticText(_("cancel", self.lang))
        self["key_green"] = StaticText(_("save", self.lang))
        self["help"]      = Label(_("xtream_help", self.lang))

        # 3 pola wejściowe
        self["host"] = Input("http://example.com:8080")
        self["user"] = Input("")
        self["pass"] = Input("")

        # ramka – placeholder (używamy tylko koloru i geometrii)
        self["hlight"] = Label("")

        self.current = 0  # 0-host, 1-user, 2-pass
        self.fields  = ["host", "user", "pass"]

        self["actions"] = ActionMap(["ColorActions", "OkCancelActions", "DirectionActions"],
        {
            "ok"     : self.openVKB,
            "cancel" : self.cancel,
            "green"  : self.save,
            "red"    : self.cancel,
            "up"     : self.prevField,
            "down"   : self.nextField
        }, -1)

        self.onFirstExecBegin.append(self.highlight)

    # ---------- podświetlenie – przesuwamy ramkę ----------
    def highlight(self):
        x, y = POS[self.current]
        self["hlight"].instance.move(ePoint(x, y))

    def prevField(self):
        self.current = (self.current - 1) % 3
        self.highlight()

    def nextField(self):
        self.current = (self.current + 1) % 3
        self.highlight()

    # ---------- klawiatura ----------
    def openVKB(self):
        field = self.fields[self.current]
        self.session.openWithCallback(self.onVkbDone, VKInputBox,
                                      title=f"{_('enter', self.lang)} {field}:",
                                      text=self[field].getText())

    def onVkbDone(self, text):
        if text is not None:
            self[self.fields[self.current]].setText(text)

    # ---------- akcje ----------
    def save(self):
        host = self["host"].getText().strip()
        user = self["user"].getText().strip()
        pwd  = self["pass"].getText().strip()
        if not host or not user:
            self.session.open(MessageBox, _("xtream_fill_host_user", self.lang),
                              MessageBox.TYPE_ERROR, timeout=3)
            return
        self.close((host, user, pwd))

    def cancel(self):
        self.close(None)

# Alias dla zgodności z importami
XtreamWindow = XtreamOneWindow