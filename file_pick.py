# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.FileList import FileList
from Components.Label import Label
from Components.ActionMap import ActionMap
import os

class M3UFilePick(Screen):
    skin = """
    <screen name="M3UFilePick" position="center,center" size="700,520" title="Wybierz plik M3U">
        <widget name="filelist" position="10,10" size="680,400" scrollbarMode="showOnDemand" enableWrapAround="1"/>
        <widget name="path"     position="10,430" size="680,30" font="Regular;22" halign="left" valign="center"/>
        <widget name="help"     position="10,470" size="680,30" font="Regular;20" halign="center" valign="center" foregroundColor="grey"/>
    </screen>
    """

    def __init__(self, session, start_dir="/tmp/"):
        Screen.__init__(self, session)
        self.setTitle("Wybierz plik M3U")
        self["path"]  = Label(start_dir)
        self["help"]  = Label("▲/▼=nawigacja  OK=wybór/wejdź  EXIT=wstecz")
        self["filelist"] = FileList(start_dir, matchingPattern="(?i)^.*\\.(m3u|m3u8)$", useServiceRef=False)
        self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], {
            "ok":     self.ok,
            "cancel": self.cancel,
            "up":     self.up,
            "down":   self.down,
            "left":   self.left,
            "right":  self.right,
        }, -1)

    def up(self):
        self["filelist"].up()

    def down(self):
        self["filelist"].down()

    def left(self):
        self["filelist"].pageUp()

    def right(self):
        self["filelist"].pageDown()

    def ok(self):
        if self["filelist"].canDescent():
            self["filelist"].descent()
            self["path"].setText(self["filelist"].getCurrentDirectory() or "")
        else:
            file = self["filelist"].getFilename()
            if file:
                self.close(file)

    def cancel(self):
        self.close(None)
