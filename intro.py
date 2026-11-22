# -*- coding: utf-8 -*-
"""Local logo intro; does not stop TV or require a video decoder/network."""
import os
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from enigma import eTimer
from .tools.ui import fit_skin


class DreamIntro(Screen):
    skin = """
    <screen name="DreamIntro" position="center,center" size="1280,720" flags="wfNoBorder" backgroundColor="#030b22">
        <widget name="brand" position="0,0" size="1280,720" scale="1" zPosition="1" />
        <widget name="fallback" position="80,280" size="1120,160" font="Regular;44" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />
        <widget name="progress" position="310,655" size="660,4" backgroundColor="#0c2845" foregroundColor="#00d7ff" zPosition="2" />
        <widget name="hint" position="200,670" size="880,28" font="Regular;17" halign="center" foregroundColor="#91b5d5" transparent="1" zPosition="2" />
    </screen>
    """

    def __init__(self, session, lang="en"):
        self.skin = fit_skin(self.skin)
        Screen.__init__(self, session)
        self["brand"] = Pixmap()
        self["fallback"] = Label("IPTV DREAM\nAIO Hub Enigma 2")
        self["progress"] = ProgressBar()
        self["progress"].setRange((0, 100))
        self["hint"] = Label("OK: pomiń   |   EXIT: zamknij" if lang == "pl" else "OK: skip   |   EXIT: close")
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": lambda: self.close(True), "cancel": lambda: self.close(False),
            "red": lambda: self.close(False),
        }, -1)
        self.ticks = 0
        self.finished = False
        self.timer = eTimer()
        try:
            self.timer.callback.append(self._tick)
        except AttributeError:
            self.timer_connection = self.timer.timeout.connect(self._tick)
        self.onLayoutFinish.append(self._start)
        self.onClose.append(self._cleanup)

    def _start(self):
        try:
            from Tools.LoadPixmap import LoadPixmap
            path = os.path.join(os.path.dirname(__file__), "pic", "intro.png")
            pixmap = LoadPixmap(path=path)
            if pixmap is not None:
                self["brand"].instance.setPixmap(pixmap)
                self["fallback"].hide()
        except Exception:
            pass
        self.timer.start(80, False)

    def _tick(self):
        if self.finished:
            return
        self.ticks += 1
        self["progress"].setValue(min(100, self.ticks * 100 // 30))
        if self.ticks >= 30:
            self.close(True)

    def _cleanup(self):
        self.finished = True
        self.timer.stop()
