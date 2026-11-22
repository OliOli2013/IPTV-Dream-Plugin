# -*- coding: utf-8 -*-
"""Native paged media browser using the image's own MoviePlayer."""
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from .tools.media import filter_media, page_items
from .tools.ui import fit_skin


class MediaBrowser(Screen):
    skin = """
    <screen name="DreamMediaBrowser" position="center,center" size="1200,670" title="IPTV Dream - Media">
        <eLabel position="0,0" size="1200,670" backgroundColor="#06111d" zPosition="-5" />
        <widget name="heading" position="28,18" size="1144,44" font="Regular;28" foregroundColor="#20d8ff" transparent="1" />
        <widget name="status" position="28,68" size="1144,32" font="Regular;19" foregroundColor="#b8ccd8" transparent="1" />
        <widget name="items" position="28,112" size="1144,444" font="Regular;23" itemHeight="36" scrollbarMode="showOnDemand" enableWrapAround="1" backgroundColor="#081725" foregroundColor="#ffffff" backgroundColorSelected="#0b5a6b" />
        <widget name="details" position="28,563" size="1144,34" font="Regular;18" foregroundColor="#9eb9c9" transparent="1" />
        <widget name="keys" position="28,611" size="1144,40" font="Regular;19" foregroundColor="#20d8ff" transparent="1" />
    </screen>
    """

    def __init__(self, session, channels, play, favorite, lang="en", title="IPTV Dream"):
        self.skin = fit_skin(self.skin)
        Screen.__init__(self, session)
        self.channels = channels
        self.play_callback = play
        self.favorite_callback = favorite
        self.lang = lang
        self.query, self.kind, self.page = "", "all", 0
        self["heading"] = Label(title)
        self["status"] = Label("")
        self["items"] = MenuList([])
        self["details"] = Label("")
        self["keys"] = Label(self.text("OK: odtwarzaj | CZERWONY: wróć | ZIELONY: szukaj | ŻÓŁTY: filtr | NIEBIESKI: ulubione",
                                       "OK: play | RED: back | GREEN: search | YELLOW: filter | BLUE: favorite"))
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "InfobarChannelSelection"], {
            "ok": self.play, "cancel": self.close, "red": self.close,
            "green": self.search, "yellow": self.cycle_filter, "blue": self.favorite,
            "left": lambda: self.change_page(-1), "right": lambda: self.change_page(1),
            "up": lambda: self["items"].up(), "down": lambda: self["items"].down(),
            "channelUp": lambda: self.change_page(-1), "channelDown": lambda: self.change_page(1),
        }, -1)
        self["items"].onSelectionChanged.append(self.selection_changed)
        self.onLayoutFinish.append(self.refresh)

    def text(self, pl, en):
        return pl if self.lang == "pl" else en

    def refresh(self):
        matches = filter_media(self.channels, self.query, self.kind)
        items, self.page, self.pages = page_items(matches, self.page)
        self["items"].setList([(item.get("title") or item.get("name") or "Stream", item) for item in items])
        label = {"all": self.text("Wszystko", "All"), "live": "LIVE", "vod": "VOD / Series"}[self.kind]
        self["status"].setText(self.text("%d pozycji | %s | Strona %d/%d | LEWO/PRAWO: strony | Szukaj: %s",
                                           "%d items | %s | Page %d/%d | LEFT/RIGHT: pages | Search: %s") % (
            len(matches), label, self.page + 1, self.pages, self.query or "-"))
        self.selection_changed()

    def selection_changed(self):
        current = self["items"].getCurrent()
        self["details"].setText(str(current[1].get("group", "")) if current else self.text("Brak wyników", "No matches"))

    def change_page(self, direction):
        self.page = (self.page + direction) % max(1, getattr(self, "pages", 1))
        self.refresh()

    def search(self):
        self.session.openWithCallback(self.search_done, VirtualKeyBoard, title=self.text("Szukaj nazwy lub grupy", "Search title or group"), text=self.query)

    def search_done(self, query):
        if query is not None:
            self.query, self.page = query.strip(), 0
            self.refresh()

    def cycle_filter(self):
        kinds = ("all", "live", "vod")
        self.kind, self.page = kinds[(kinds.index(self.kind) + 1) % len(kinds)], 0
        self.refresh()

    def play(self):
        current = self["items"].getCurrent()
        if current:
            self.play_callback(current[1])

    def favorite(self):
        current = self["items"].getCurrent()
        if current:
            self.favorite_callback(current[1])
