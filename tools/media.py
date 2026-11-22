# -*- coding: utf-8 -*-
"""Receiver-independent media filtering, paging, and recent items."""
import unicodedata
from .storage import read_json, write_json


def search_key(value):
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(ch for ch in text if not unicodedata.combining(ch)).replace("ł", "l")


def filter_media(channels, query="", kind="all"):
    words = search_key(query).split()
    result = []
    for channel in channels:
        media_kind = channel.get("type", "")
        vod = bool(channel.get("is_vod") or media_kind in ("vod", "movie", "series"))
        if kind == "live" and vod or kind == "vod" and not vod:
            continue
        text = search_key("%s %s" % (channel.get("title") or channel.get("name", ""), channel.get("group", "")))
        if all(word in text for word in words):
            result.append(channel)
    return result


def page_items(channels, page, page_size=100):
    pages = max(1, (len(channels) + page_size - 1) // page_size)
    page = min(max(0, page), pages - 1)
    return channels[page * page_size:(page + 1) * page_size], page, pages


class RecentMedia:
    def __init__(self, path="/etc/enigma2/iptvdream_recent.json"):
        self.path = path

    def items(self):
        return [item for item in read_json(self.path, []) if isinstance(item, dict) and item.get("url")][:50]

    def add(self, channel):
        fields = ("title", "name", "url", "group", "type", "is_vod", "epg_id", "tvg-id", "headers")
        item = {key: channel[key] for key in fields if key in channel}
        items = [old for old in self.items() if old.get("url") != channel.get("url")]
        write_json(self.path, ([item] + items)[:50])
