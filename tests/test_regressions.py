# -*- coding: utf-8 -*-
"""Regression tests that run without an Enigma2 receiver."""
from __future__ import absolute_import

import importlib
import os
import sys
import tempfile
import types
import unittest
from urllib.parse import unquote
from unittest import mock
import xml.etree.ElementTree as ET


# The receiver package declares python3-requests as a dependency.  Keep this
# test suite runnable in a minimal build container as no test performs network I/O.
try:
    import requests  # noqa: F401
except ImportError:
    requests_stub = types.ModuleType("requests")

    class _RequestError(Exception):
        pass

    class _Session(object):
        def __init__(self):
            self.headers = {}

        def get(self, *args, **kwargs):
            raise _RequestError("network disabled in unit tests")

    requests_stub.Session = _Session
    requests_stub.get = _Session().get
    requests_stub.exceptions = types.SimpleNamespace(
        Timeout=_RequestError,
        RequestException=_RequestError,
    )
    sys.modules["requests"] = requests_stub


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if "IPTVDream" not in sys.modules:
    package = types.ModuleType("IPTVDream")
    package.__path__ = [ROOT]
    package.__file__ = os.path.join(ROOT, "__init__.py")
    sys.modules["IPTVDream"] = package

exporter = importlib.import_module("IPTVDream.export_v2")
mac_portal = importlib.import_module("IPTVDream.tools.mac_portal")
playlist_loader = importlib.import_module("IPTVDream.core.playlist_loader")
webif = importlib.import_module("IPTVDream.tools.webif")
logger = importlib.import_module("IPTVDream.tools.logger")


def decode_service_line(line):
    assert line.startswith("#SERVICE ")
    fields = line[len("#SERVICE "):].split(':', 10)
    if len(fields) != 11:
        raise AssertionError("invalid technical service reference")
    url_field, name_field = fields[10].split(':', 1)
    return fields[:10], unquote(url_field), unquote(name_field)


class ExportRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bouquet_dir = os.path.join(self.tmp.name, "enigma2")
        self.epg_dir = os.path.join(self.tmp.name, "epgimport")
        os.makedirs(self.bouquet_dir)
        self.old = {
            "BOUQUET_DIR": exporter.BOUQUET_DIR,
            "EPG_DIR": exporter.EPG_DIR,
            "EPG_CHANNEL_FILE": exporter.EPG_CHANNEL_FILE,
            "EPG_SOURCE_FILE": exporter.EPG_SOURCE_FILE,
            "eDVBDB": exporter.eDVBDB,
        }
        exporter.BOUQUET_DIR = self.bouquet_dir
        exporter.EPG_DIR = self.epg_dir
        exporter.EPG_CHANNEL_FILE = os.path.join(self.epg_dir, "iptvdream.channels.xml")
        exporter.EPG_SOURCE_FILE = os.path.join(self.epg_dir, "iptvdream.sources.xml")
        exporter.eDVBDB = None

    def tearDown(self):
        for key, value in self.old.items():
            setattr(exporter, key, value)
        self.tmp.cleanup()

    def test_export_has_playable_url_and_nonempty_service_name(self):
        original_index = (
            '#NAME User - bouquets (TV)\n'
            '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet\n'
            '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.iptv_dream_missing.tv" ORDER BY bouquet\n'
        )
        with open(os.path.join(self.bouquet_dir, "bouquets.tv"), "w", encoding="utf-8") as f:
            f.write(original_index)

        channels = [
            {
                "title": "[PL] TVP 1: HD",
                "group": "|PL| Wiadomości",
                "epg_id": "TVP1.pl",
                "url": "https://user:secret@example.test/live path.ts?token=a:b&x=one%20two|User-Agent=Custom Agent",
            },
            {
                "title": "News\n#SERVICE injected",
                "group": "|PL| Wiadomości\n#NAME injected",
                "url": "https://example.test/live/2.ts\n#SERVICE injected",
            },
            {
                "title": "Multicast",
                "group": "Techniczne",
                "url": "udp://@239.1.2.3:1234",
            },
            {
                "title": "Invalid",
                "group": "Techniczne",
                "url": "javascript:alert(1)",
            },
        ]

        bouquets, count = exporter.export_bouquets(
            channels, "M3U-example-a1b2c3d4", service_type="4097"
        )
        self.assertEqual((bouquets, count), (3, 3))

        files = sorted(
            name for name in os.listdir(self.bouquet_dir)
            if name.startswith("userbouquet.iptv_dream_")
        )
        self.assertEqual(len(files), 3)
        decoded = []
        for filename in files:
            with open(os.path.join(self.bouquet_dir, filename), "r", encoding="utf-8") as f:
                text = f.read()
            self.assertNotIn("\n#NAME injected", text)
            self.assertIn("#IPTVDREAM_SOURCE M3U-example-a1b2c3d4", text)
            service_lines = [line for line in text.splitlines() if line.startswith("#SERVICE ")]
            description_lines = [line for line in text.splitlines() if line.startswith("#DESCRIPTION ")]
            self.assertEqual(len(service_lines), len(description_lines))
            for line in service_lines:
                technical, url, name = decode_service_line(line)
                self.assertEqual(technical[0], "4097")
                self.assertTrue(url.startswith(("https://", "udp://")))
                self.assertTrue(name and name != "N/A")
                self.assertNotIn("\n", name)
                decoded.append((url, name))

        first_url = next(url for url, name in decoded if "TVP 1" in name)
        self.assertIn("https://user:secret@example.test/", first_url)
        self.assertIn("token=a:b", first_url)
        self.assertIn("x=one two", first_url)
        self.assertNotIn("MAG200", first_url)
        multicast_url = next(url for url, name in decoded if name == "Multicast")
        self.assertNotIn("User-Agent", multicast_url)

        index_path = os.path.join(self.bouquet_dir, "bouquets.tv")
        with open(index_path, "r", encoding="utf-8") as f:
            index_text = f.read()
        self.assertIn("userbouquet.favourites.tv", index_text)
        self.assertNotIn("userbouquet.iptv_dream_missing.tv", index_text)
        self.assertEqual(index_text.count("userbouquet.iptv_dream_"), 3)
        with open(index_path + ".iptvdream.bak", "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), original_index)

        ET.parse(exporter.EPG_CHANNEL_FILE)
        ET.parse(exporter.EPG_SOURCE_FILE)

    def test_invalid_playlist_does_not_leave_empty_bouquet(self):
        with self.assertRaisesRegex(Exception, "No channels exported"):
            exporter.export_bouquets(
                [{"title": "bad", "group": "bad", "url": "not-a-stream"}],
                "Bad",
            )
        leftovers = [name for name in os.listdir(self.bouquet_dir) if name.endswith('.tv')]
        self.assertEqual(leftovers, [])

    def test_index_failure_is_not_reported_as_success(self):
        channel = [{"title": "One", "group": "Main", "url": "https://example.test/one.ts"}]
        with mock.patch.object(exporter, "add_to_bouquets_index", return_value=False):
            with self.assertRaisesRegex(Exception, "cannot add"):
                exporter.export_bouquets(channel, "Source")
        leftovers = [name for name in os.listdir(self.bouquet_dir) if name.startswith('userbouquet.')]
        self.assertEqual(leftovers, [])

    def test_reference_encoder_preserves_valid_escapes(self):
        line = exporter._build_service_line(
            "5002:0:1:1:2:3:4:0:0:0",
            "https://example.test/a%2fpath/100%?q=a:b",
            "Kanał: HD",
        )
        technical, url, name = decode_service_line(line)
        self.assertEqual(technical[0], "5002")
        self.assertEqual(url, "https://example.test/a/path/100%?q=a:b")
        self.assertEqual(name, "Kanał: HD")


class MacPortalRegressionTests(unittest.TestCase):
    def test_loopback_detection_with_ports_and_ipv6(self):
        for value in (
            "http://127.0.0.1:8080/ch/1",
            "https://127.10.20.30/link",
            "http://localhost:88/a",
            "http://[::1]:8000/a",
            "http://0.0.0.0/a",
        ):
            self.assertTrue(mac_portal._is_local_url(value), value)
        self.assertFalse(mac_portal._is_local_url("https://example.test/localhost/a"))
        self.assertFalse(mac_portal._is_local_url("https://128.0.0.1/a"))

    def test_local_command_is_resolved_even_for_large_playlist_fast_path(self):
        class Client(object):
            portal_root = "https://portal.test/stalker_portal"

            def __init__(self):
                self.calls = []

            def link(self, cmd, kind):
                self.calls.append((cmd, kind))
                return "ffmpeg https://cdn.test/live/123.ts?token=ok"

        client = Client()
        result = mac_portal._play_url(
            client,
            {"cmd": "ffmpeg http://127.0.0.1:88/ch/123", "id": "123"},
            resolve=False,
        )
        self.assertEqual(result, "https://cdn.test/live/123.ts?token=ok")
        self.assertEqual(len(client.calls), 1)


class LoaderAndUtilityTests(unittest.TestCase):
    def test_m3u_quoted_comma_extgrp_and_unicode(self):
        loader = playlist_loader.PlaylistLoader()
        m3u = (
            '#EXTM3U\n'
            '#EXTINF:-1 tvg-id="TVP1.pl" tvg-name="TVP 1, HD" group-title="|PL| News",TVP 1, HD\n'
            '#EXTGRP:|PL| Wiadomości\n'
            'https://example.test/live/1.ts\n'
        )
        channels = loader.parse_m3u_content(m3u)
        self.assertEqual(len(channels), 1)
        self.assertIn("TVP 1", channels[0]["title"])
        self.assertEqual(channels[0]["epg_id"], "TVP1.pl")
        self.assertEqual(channels[0]["url"], "https://example.test/live/1.ts")

    def test_webif_url_validation(self):
        self.assertTrue(webif.is_valid_url("https://example.test:8443/get.php?a=1"))
        self.assertTrue(webif.is_valid_url("http://[2001:db8::1]:8080/list.m3u"))
        self.assertTrue(webif.is_valid_url("http://receiver/list.m3u"))
        self.assertFalse(webif.is_valid_url("javascript://example.test/x"))
        self.assertFalse(webif.is_valid_url("https://example.test:99999/x"))
        self.assertFalse(webif.is_valid_url("https://example.test/x\nInjected"))

    def test_webif_uses_next_port_when_9999_is_busy(self):
        class Listener(object):
            def __init__(self):
                self.stopped = False

            def stopListening(self):
                self.stopped = True

        class Reactor(object):
            def __init__(self):
                self.attempts = []
                self.listener = Listener()

            def listenTCP(self, port, site):
                self.attempts.append(port)
                if port == 9999:
                    raise OSError("busy")
                return self.listener

        reactor = Reactor()
        webif._server_port = None
        webif._server_listen_port = None
        with mock.patch.object(webif, "WEBIF_AVAILABLE", True), \
                mock.patch.object(webif, "reactor", reactor), \
                mock.patch.object(webif, "Site", lambda root: root):
            self.assertTrue(webif.start_web_server(9999, lambda data: None))
            self.assertEqual(reactor.attempts, [9999, 10000])
            self.assertEqual(webif.get_web_server_port(), 10000)
            self.assertTrue(webif.stop_web_server())
            self.assertTrue(reactor.listener.stopped)
            self.assertIsNone(webif.get_web_server_port())

    def test_log_masking_covers_common_iptv_credentials(self):
        value = (
            "https://alice:secret@example.test/live/bob/pass123/1.ts?"
            "username=bob&password=pass123&token=abc"
        )
        masked = logger.mask_sensitive(value)
        for secret in ("alice", "secret", "bob", "pass123", "abc"):
            self.assertNotIn(secret, masked)


if __name__ == "__main__":
    unittest.main(verbosity=2)
