# -*- coding: utf-8 -*-
"""Use native audio/subtitle/seek controls and return directly to IPTV Dream."""
import inspect
from Screens.InfoBar import MoviePlayer


def player_options(player_class):
    try:
        if "fromMovieSelection" in inspect.signature(player_class.__init__).parameters:
            return {"fromMovieSelection": False}
    except (ValueError, TypeError):
        pass
    return {}


class DreamMoviePlayer(MoviePlayer):
    def __init__(self, session, service):
        self.skinName = "MoviePlayer"
        MoviePlayer.__init__(self, session, service, **player_options(MoviePlayer))

    def handleLeave(self, *args):
        self.close()

    def leavePlayer(self):
        self.close()

    def leavePlayerOnExit(self):
        self.close()
