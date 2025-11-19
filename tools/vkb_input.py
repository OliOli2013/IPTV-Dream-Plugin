# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.Input import Input
from Components.Label import Label
from Components.ActionMap import ActionMap
from twisted.internet import reactor # <--- NOWY, KLUCZOWY IMPORT

class VKInputBox(Screen):
    # Używamy skinu dla stabilności Enigmy, ale ekran zostanie natychmiast ukryty przez klawiaturę
    skin = """
    <screen name="VKInputBox" position="center,center" size="900,400" title="Wprowadź dane">
        <widget name="text"   position="20,20"  size="860,60"  font="Regular;28" halign="center" valign="center"/>
        <widget name="input"  position="20,100" size="860,60"  font="Regular;24" halign="left" valign="center" transparent="0" backgroundColor="#202020"/>
        <widget name="help"   position="20,200" size="860,40"  font="Regular;22" halign="center" valign="center" foregroundColor="grey"/>
        <eLabel text="Automatyczne otwieranie klawiatury... Proszę czekać." position="20,320" size="860,40" font="Regular;24" halign="center" valign="center" foregroundColor="yellow"/>
    </screen>
    """

    def __init__(self, session, title="", text=""):
        Screen.__init__(self, session)
        self.setTitle(title)
        self.input = Input(text)
        self["text"]  = Label(title)
        self["input"] = self.input
        self["help"]  = Label("") # Usuwamy stary tekst pomocy
        
        # Blokujemy akcje OK i ZIELONY, ponieważ klawiatura otworzy się automatycznie.
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok":     lambda: None, # Zablokowane, aby uniknąć podwójnego otwarcia
            "cancel": self.cancel,  # EXIT/Czerwony działa, aby anulować
            "green":  lambda: None, # Zablokowane
            "red":    self.cancel,
        }, -1)
        
        # Kluczowa zmiana: natychmiast otwieramy VirtualKeyBoard po minimalnym opóźnieniu
        reactor.callLater(0.1, self.autoOpenVKB)

    def autoOpenVKB(self):
        # Sprawdzamy, czy okno jest wciąż aktywne, by uniknąć błędów
        if self.session.current_dialog is self: 
            self.session.openWithCallback(self.vkbDone, VirtualKeyBoard,
                                          title=self["text"].getText(),
                                          text=self.input.getText())

    def vkbDone(self, text):
        # Ta funkcja jest wywoływana, gdy VirtualKeyBoard się zamknie.
        if text is not None:
            # Wprowadzono tekst: zamykamy nasz "przejściowy" ekran i zwracamy wynik.
            self.close(text)
        else:
            # Anulowano: zamykamy ekran.
            self.close(None)

    # Funkcje ok i cancel muszą pozostać, aby zamknąć nasz ekran.
    def ok(self):
        # Nie powinno być wywoływane przez blokadę, ale dla pewności zamyka
        self.close(self.input.getText())

    def cancel(self):
        # Anulowanie (EXIT/Czerwony)
        self.close(None)
