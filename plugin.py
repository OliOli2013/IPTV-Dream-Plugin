# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor
from Components.Language import language
from .tools.lang import _, normalize_lang

_DESCRIPTIONS = {
    "pl": "Wtyczka IPTV - M3U / Xtream / MAC / Stalker / EPG / Pikony / WebIF",
    "en": "IPTV plugin - M3U / Xtream / MAC / Stalker / EPG / Picons / WebIF",
    "de": "IPTV-Plugin - M3U / Xtream / MAC / Stalker / EPG / Picons / WebIF",
    "es": "Plugin IPTV - M3U / Xtream / MAC / Stalker / EPG / Picons / WebIF",
    "ar": "إضافة IPTV - M3U / Xtream / MAC / Stalker / EPG / Picons / WebIF",
    "ru": "IPTV-плагин - M3U / Xtream / MAC / Stalker / EPG / пиконы / WebIF",
}

def _system_lang():
    try:
        return normalize_lang((language.getLanguage() or "en")[:2], "en")
    except Exception:
        return "en"

def main(session, **kwargs):
    # Lazy import: keep plugin listing lightweight and resilient on images
    # where optional runtime dependencies are missing.
    def open_main(continue_start=True):
        if not continue_start:
            return
        try:
            from .dream_v6 import IPTVDreamMain
            session.open(IPTVDreamMain)
        except Exception as exc:
            from Screens.MessageBox import MessageBox
            from .tools.logger import mask_sensitive
            session.open(MessageBox, "IPTV Dream: %s" % mask_sensitive(exc), MessageBox.TYPE_ERROR)

    try:
        from .tools.storage import read_json
        config = read_json("/etc/enigma2/iptvdream_v6_config.json", {})
        if config.get("intro_enabled", True):
            from .intro import DreamIntro
            session.openWithCallback(open_main, DreamIntro, _system_lang())
        else:
            open_main()
    except Exception:
        open_main()

def Plugins(**kwargs):
    lang = _system_lang()
    name = _("title", lang)
    desc = _DESCRIPTIONS.get(lang, _DESCRIPTIONS["en"])
    return PluginDescriptor(name=name, description=desc, where=PluginDescriptor.WHERE_PLUGINMENU, icon="icon.png", fnc=main)
