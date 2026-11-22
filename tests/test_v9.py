# -*- coding: utf-8 -*-
"""Behavior regressions for the stability and media release."""
import importlib
import os
from pathlib import Path
import queue
import sys
import tempfile
import threading
import types
import unittest
from unittest import mock
from urllib.parse import unquote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
if "IPTVDream" not in sys.modules:
    package = types.ModuleType("IPTVDream")
    package.__path__ = [str(ROOT)]
    sys.modules["IPTVDream"] = package

tasks = importlib.import_module("IPTVDream.tools.tasks")
media = importlib.import_module("IPTVDream.tools.media")
storage = importlib.import_module("IPTVDream.tools.storage")
config = importlib.import_module("IPTVDream.core.config_manager")
loader_module = importlib.import_module("IPTVDream.core.playlist_loader")
exporter = importlib.import_module("IPTVDream.export_v2")
runtime = importlib.import_module("IPTVDream.tools.runtime_package")


class BackgroundOperationTests(unittest.TestCase):
    def setUp(self):
        self.queue = queue.Queue()
        self.scope = tasks.TaskScope(lambda fn, *args: self.queue.put((fn, args)))
        self.results = []

    def drain(self):
        while not self.queue.empty():
            fn, args = self.queue.get_nowait()
            fn(*args)

    def test_cancelled_old_worker_cannot_overwrite_new_result(self):
        self.scope.begin()
        release = threading.Event()
        first = self.scope.run(lambda: (release.wait(2), "old")[1], lambda *args: self.results.append(args))
        self.scope.cancel()
        self.scope.begin()
        second = self.scope.run(lambda: "new", lambda *args: self.results.append(args))
        second.join(2)
        release.set()
        first.join(2)
        self.drain()
        self.assertEqual(self.results, [("new", None)])

    def test_queued_progress_cannot_update_replaced_operation(self):
        self.scope.begin()
        progress = self.scope.progress(lambda *args: self.results.append(args))
        progress(90, "old")
        self.scope.begin()
        self.drain()
        self.assertEqual(self.results, [])
        with self.assertRaises(tasks.TaskCancelled):
            progress(100, "late")

    def test_close_drops_both_success_and_error_callbacks(self):
        self.scope.begin()
        thread = self.scope.run(lambda: 1 / 0, lambda *args: self.results.append(args))
        thread.join(2)
        self.scope.close()
        self.drain()
        self.assertEqual(self.results, [])

    def test_callback_runs_on_dispatcher_thread(self):
        main_thread = threading.get_ident()
        worker_threads, callback_threads = [], []
        self.scope.begin()
        thread = self.scope.run(lambda: worker_threads.append(threading.get_ident()),
                                lambda *args: callback_threads.append(threading.get_ident()))
        thread.join(2)
        self.assertEqual(callback_threads, [])
        self.drain()
        self.assertNotEqual(worker_threads, [main_thread])
        self.assertEqual(callback_threads, [main_thread])


class PersistenceAndMediaTests(unittest.TestCase):
    def test_loading_configuration_never_writes_or_overwrites_gui_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            storage.write_json(str(path), {"language": "pl", "last_url": "https://example.test/new.m3u"})
            original = path.read_bytes()
            with mock.patch.object(config, "write_json", side_effect=AssertionError("unexpected write")):
                manager = config.ConfigManager(str(path))
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(manager.get("language"), "pl")

    def test_corrupt_shape_is_recovered_and_credentials_are_private(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text('["bad"]')
            self.assertEqual(storage.read_json(str(path), {}), {})
            storage.write_json(str(path), {"password": "secret"})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(Path(directory).glob('.iptvdream-*')), [])

    def test_search_matches_polish_letters_and_group(self):
        channels = [{"title": "Łódź Żółw HD", "group": "Nauka", "url": "https://example.test/1"},
                    {"title": "Film", "group": "Kino", "is_vod": True, "url": "https://example.test/2"}]
        self.assertEqual(media.filter_media(channels, "lodz zolw nauka"), channels[:1])
        self.assertEqual(media.filter_media(channels, kind="vod"), channels[1:])
        self.assertEqual(media.filter_media(channels, kind="live"), channels[:1])

    def test_every_item_above_old_400_item_limit_can_be_reached(self):
        channels = [{"title": str(n)} for n in range(10037)]
        result = []
        for page in range(101):
            items, current, pages = media.page_items(channels, page)
            result.extend(items)
        self.assertEqual(result, channels)
        self.assertEqual(pages, 101)

    def test_recent_media_is_deduplicated_and_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            recent = media.RecentMedia(str(Path(directory) / "recent.json"))
            for number in range(55):
                recent.add({"title": str(number), "url": "https://example.test/%d" % number})
            recent.add({"title": "Updated", "url": "https://example.test/54"})
            self.assertEqual(len(recent.items()), 50)
            self.assertEqual(recent.items()[0]["title"], "Updated")


class PlaylistV9Tests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        with mock.patch.object(loader_module, "DEFAULT_CONFIG", str(Path(self.directory.name) / "config.json")), \
             mock.patch.object(loader_module, "CACHE_DIR", self.directory.name):
            self.loader = loader_module.PlaylistLoader()

    def tearDown(self):
        if hasattr(self.loader.session, 'close'):
            self.loader.session.close()
        self.directory.cleanup()

    def test_extvlcopt_headers_are_preserved_in_player_and_export(self):
        channels = self.loader.parse_m3u_content('#EXTM3U\n#EXTINF:-1,Test\n#EXTVLCOPT:http-user-agent=My Player\n#EXTVLCOPT:http-referrer=https://example.test/\nhttps://cdn.test/1.ts\n')
        reference, _prefix, title = exporter.playback_reference(channels[0])
        decoded = unquote(reference)
        self.assertIn('User-Agent=My Player', decoded)
        self.assertIn('Referer=https://example.test/', decoded)
        self.assertEqual(title, "Test")

    def test_hls_is_one_stream_instead_of_fragments(self):
        channels = self.loader.parse_m3u_content('#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:6,\na.ts\n#EXTINF:6,\nb.ts', base_url='https://example.test/live.m3u8')
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0]['url'], 'https://example.test/live.m3u8')

    def test_relative_urls_and_single_quoted_attributes(self):
        channels = self.loader.parse_m3u_content("#EXTM3U\n#EXTINF:-1 tvg-name='Kanał, HD' group-title='Grupa 1',Name\n../live/1.ts", base_url='https://example.test/lists/list.m3u')
        self.assertEqual(channels[0]['title'], 'Kanał, HD')
        self.assertEqual(channels[0]['group'], 'Grupa 1')
        self.assertEqual(channels[0]['url'], 'https://example.test/live/1.ts')

    def test_force_refresh_does_not_hide_failure_with_stale_cache(self):
        url = 'https://example.test/list.m3u'
        self.loader.cache_content(url, b'#EXTM3U\n#EXTINF:-1,Old\nhttps://example.test/old')
        with mock.patch.object(loader_module, 'http_get', side_effect=RuntimeError('provider down')):
            old = self.loader.load_m3u_url(url)
            self.assertIn(b'Old', old)
            self.assertTrue(self.loader.last_warning)
            with self.assertRaisesRegex(Exception, 'provider down'):
                self.loader.load_m3u_url(url, force_refresh=True)

    def test_cancel_is_not_swallowed_by_parser_or_download_fallback(self):
        def cancelled(*args):
            raise tasks.TaskCancelled()
        with self.assertRaises(tasks.TaskCancelled):
            self.loader.parse_m3u_content('#EXTINF:-1,One\nhttps://example.test/1', progress_callback=cancelled)
        with mock.patch.object(loader_module, 'http_get') as get:
            with self.assertRaises(tasks.TaskCancelled):
                self.loader.load_m3u_url('https://example.test/1.m3u', progress_callback=cancelled)
            get.assert_not_called()


class RuntimeTests(unittest.TestCase):
    def test_only_runtime_files_are_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            files = runtime.copy_runtime(ROOT, directory)
            self.assertIn('intro.py', files)
            self.assertIn('pic/intro.png', files)
            self.assertNotIn('index.html', files)
            self.assertFalse(any(path.startswith(('tests/', 'packaging/', '.git/')) for path in files))
            self.assertFalse(any(path.endswith(('.ipk', '.deb')) for path in files))
            for relative in files:
                self.assertEqual((Path(directory) / relative).read_bytes(), (ROOT / relative).read_bytes())

    def test_skins_fit_sd_hd_and_fullhd(self):
        ui = importlib.import_module('IPTVDream.tools.ui')
        skin = '<screen position="center,center" size="1200,680"><widget position="30,130" size="1100,450" font="Regular;22" itemHeight="31" /></screen>'
        for width, height in ((720, 576), (1280, 720), (1920, 1080)):
            tree = ET.fromstring(ui.fit_skin(skin, (width, height)))
            screen_width, screen_height = map(int, tree.get('size').split(','))
            self.assertLessEqual(screen_width, width)
            self.assertLessEqual(screen_height, height)


if __name__ == '__main__':
    unittest.main()
