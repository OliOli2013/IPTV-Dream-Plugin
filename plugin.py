# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Components.Language import language
from .tools.lang import _
def main(session, **kwargs):
    # Lazy import: keep plugin listing lightweight and resilient on images
    # where optional runtime dependencies are missing.
    from .dream_v6 import IPTVDreamMain
    session.open(IPTVDreamMain)

def Plugins(**kwargs):
    lang = (language.getLanguage() or "en")[:2]
    name = _("title", lang)
    desc = "Wtyczka IPTV - M3U / Xtream / MAC / EPG / Pikony / WebIF" if lang == "pl" else "IPTV plugin - M3U / Xtream / MAC / EPG / Picons / WebIF"
    return PluginDescriptor(name=name, description=desc, where=PluginDescriptor.WHERE_PLUGINMENU, icon="icon.png", fnc=main)
