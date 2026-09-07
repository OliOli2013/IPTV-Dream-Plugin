# -*- coding: utf-8 -*-
"""Lightweight tools package for IPTV Dream.

Do not eagerly import optional/runtime modules here. Importing IPTVDream.tools.net
must not initialize Xtream/WebIF/EPG screens or fail because an unrelated module
is unavailable on a particular Enigma2 image.
"""

TOOLS_VERSION = "8.0.1"

__all__ = ['TOOLS_VERSION']
