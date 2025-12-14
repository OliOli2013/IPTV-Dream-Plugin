# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from .dream_v6 import IPTVDreamMain

def main(session, **kwargs):
    session.open(IPTVDreamMain)

def Plugins(**kwargs):
    return [
        PluginDescriptor(name="IPTV Dream v6.0", description="Ultra-szybka wtyczka IPTV - REWOLUCJA! (v6.0)", where=PluginDescriptor.WHERE_PLUGINMENU, icon="plugin.png", fnc=main),
        PluginDescriptor(name="IPTV Dream v6.0", description="Ultra-szybka wtyczka IPTV - REWOLUCJA! (v6.0)", where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main),
    ]