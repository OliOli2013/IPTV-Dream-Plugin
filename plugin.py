# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Components.Language import language
from .tools.lang import _
from .dream_v6 import IPTVDreamMain

def main(session, **kwargs):
    session.open(IPTVDreamMain)

def Plugins(**kwargs):
    lang = (language.getLanguage() or "en")[:2]
    name = _("title", lang)
    desc = "Wtyczka IPTV - M3U / Xtream / MAC / EPG / Pikony / WebIF" if lang == "pl" else "IPTV plugin - M3U / Xtream / MAC / EPG / Picons / WebIF"
    return PluginDescriptor(name=name, description=desc, where=PluginDescriptor.WHERE_PLUGINMENU, icon="icon.png", fnc=main)
