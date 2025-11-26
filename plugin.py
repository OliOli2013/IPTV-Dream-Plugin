# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from .dream import IPTVDreamMain

def main(session, **kwargs):
    session.open(IPTVDreamMain)

def Plugins(**kwargs):
    return [
        PluginDescriptor(name="IPTV Dream", description="Wczytaj M3U i eksportuj do bukietów (v3.3)", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main),
        PluginDescriptor(name="IPTV Dream", description="Wczytaj M3U i eksportuj do bukietów (v3.3)", where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main),
    ]
