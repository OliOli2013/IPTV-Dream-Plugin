"""Exercise real screen classes with strict UI-thread stubs, without a tuner."""
import importlib
import json
from pathlib import Path
import queue
import sys
import tempfile
import threading
import types

ROOT = Path(__file__).resolve().parent.parent
OWNER = threading.get_ident()
CALLS = queue.Queue()


def ui_only():
    assert threading.get_ident() == OWNER, "Enigma2 widget accessed from a worker thread"


class Widget:
    def __init__(self, value="", *args, **kwargs):
        self.value = value
        self.instance = self
        self.onSelectionChanged = []
        self.list = value if isinstance(value, list) else []
        self.index = 0

    def setText(self, value):
        ui_only()
        self.value = value

    def getText(self):
        return self.value

    def setList(self, value):
        ui_only()
        self.list = value
        self.index = 0

    def getCurrent(self):
        return self.list[self.index] if self.list else None

    def moveToIndex(self, index):
        self.index = index

    def getSelectedIndex(self):
        return self.index

    def up(self):
        self.index = max(0, self.index - 1)

    def down(self):
        self.index = min(max(0, len(self.list) - 1), self.index + 1)

    def setRange(self, value):
        ui_only()

    def setValue(self, value):
        ui_only()
        self.value = value

    def show(self):
        ui_only()

    def hide(self):
        ui_only()

    def setPixmap(self, pixmap):
        ui_only()

    def selectionEnabled(self, enabled):
        ui_only()


class Screen(dict):
    def __init__(self, session, *args, **kwargs):
        dict.__init__(self)
        self.session = session
        self.onLayoutFinish, self.onClose, self.onFirstExecBegin = [], [], []
        self.closed_result = None

    def setTitle(self, title):
        ui_only()

    def close(self, *args):
        ui_only()
        self.closed_result = args
        for callback in self.onClose:
            callback()


class MessageBox(Screen):
    TYPE_INFO, TYPE_ERROR, TYPE_YESNO = 1, 2, 3


class Timer:
    def __init__(self):
        self.callback = []

    def start(self, *args):
        ui_only()

    def stop(self):
        ui_only()


class ServiceReference:
    def __init__(self, reference):
        self.reference = reference

    def setName(self, title):
        self.title = title


class PluginDescriptor:
    WHERE_PLUGINMENU = 1

    def __init__(self, **kwargs):
        self.kwargs = kwargs


def module(name, **attributes):
    obj = types.ModuleType(name)
    obj.__dict__.update(attributes)
    sys.modules[name] = obj
    return obj


module('IPTVDream', __path__=[str(ROOT)])
module('Plugins.Plugin', PluginDescriptor=PluginDescriptor)
module('Screens.Screen', Screen=Screen)
module('Screens.MessageBox', MessageBox=MessageBox)
module('Screens.ChoiceBox', ChoiceBox=Screen)
module('Screens.VirtualKeyBoard', VirtualKeyBoard=Screen)
module('Screens.InfoBar', MoviePlayer=Screen)
for kind in ('Label', 'Pixmap', 'ProgressBar', 'MenuList', 'FileList', 'ActionMap', 'Input'):
    module('Components.' + kind, **{kind: Widget})
module('Components.Language', language=types.SimpleNamespace(getLanguage=lambda: 'pl_PL'))
module('Components.Sources.StaticText', StaticText=Widget)
module('Tools.LoadPixmap', LoadPixmap=lambda **kwargs: object())
desktop_size = types.SimpleNamespace(width=lambda: 1280, height=lambda: 720)
module('enigma', eTimer=Timer, eDVBDB=None, ePoint=lambda x, y: (x, y), eServiceReference=ServiceReference,
       getDesktop=lambda n: types.SimpleNamespace(size=lambda: desktop_size))
module('twisted', __path__=[])
module('twisted.internet', reactor=types.SimpleNamespace(callFromThread=lambda fn, *args: CALLS.put((fn, args))))


class Session:
    def __init__(self):
        self.opened = []

    def open(self, cls, *args, **kwargs):
        ui_only()
        self.opened.append((cls, args, kwargs))
        if cls is not MessageBox:
            return cls(self, *args, **kwargs)

    def openWithCallback(self, callback, cls, *args, **kwargs):
        self.last_callback = callback
        return self.open(cls, *args, **kwargs)


def pump(screen):
    while screen.is_loading:
        fn, args = CALLS.get(timeout=3)
        fn(*args)


with tempfile.TemporaryDirectory() as directory:
    directory = Path(directory)
    dream = importlib.import_module('IPTVDream.dream_v6')
    dream.CONFIG_FILE = str(directory / 'config.json')
    Path(dream.CONFIG_FILE).write_text(json.dumps({'language': 'pl', 'log_file': str(directory / 'test.log')}))
    dream.get_lan_ip = lambda: '192.0.2.1'
    dream.PiconManager = lambda: types.SimpleNamespace(picon_dir=str(directory / 'picon'))
    dream.EPGManager = lambda: None
    dream.PlaylistLoader.__init__.__globals__['DEFAULT_CONFIG'] = dream.CONFIG_FILE
    dream.PlaylistLoader.__init__.__globals__['CACHE_DIR'] = str(directory / 'cache')
    for name in ('FavoritesManager', 'StatisticsManager', 'HistoryManager'):
        manager = getattr(dream, name)
        setattr(dream, name, lambda manager=manager: manager(str(directory / (manager.__name__ + '.json'))))
    session = Session()
    main = dream.IPTVDreamMain(session)
    main.recent_media.path = str(directory / 'recent.json')
    for callback in main.onLayoutFinish:
        callback()
    assert len(main['menu_list'].list) == 10
    main.showManagementMenu()
    main._dispatch('intro_toggle')
    assert json.loads(Path(dream.CONFIG_FILE).read_text())['intro_enabled'] is False
    main.showDiagnostics()

    playlist = '#EXTM3U\n#EXTINF:-1 group-title="Test",TV One\nhttps://example.test/live/1.ts'
    fixture = directory / 'list.m3u'
    fixture.write_text(playlist)
    main.onFileReady(str(fixture))
    pump(main)
    assert len(main.current_playlist) == 1
    assert main['menu_list'].list[0][1] == 'media'

    parse_threads = []
    actual_parse = main.loader.parse_m3u_content
    main.loader.load_m3u_url = lambda *args, **kwargs: playlist.encode()
    def parse(*args, **kwargs):
        parse_threads.append(threading.get_ident())
        return actual_parse(*args, **kwargs)
    main.loader.parse_m3u_content = parse
    main.xtream_data = ('https://example.test', 'user', 'pass')
    main.onXtreamTypeSelected(('ALL', 'all'))
    pump(main)
    assert parse_threads and all(thread != OWNER for thread in parse_threads)

    main.openMediaBrowser(main.current_playlist, 'Test')
    browser_type, args, kwargs = session.opened[-1]
    browser = browser_type(session, *args, **kwargs)
    browser.refresh()
    browser.search_done('TV One')
    browser.play()
    assert session.opened[-1][0].__name__ == 'DreamMoviePlayer'
    player = importlib.import_module('IPTVDream.player')
    class ATVPlayer:
        def __init__(self, session, service, fromMovieSelection=True):
            pass
    class PLiPlayer:
        def __init__(self, session, service, slist=None, lastservice=None, infobar=None):
            pass
    assert player.player_options(ATVPlayer) == {'fromMovieSelection': False}
    assert player.player_options(PLiPlayer) == {}
    main.addMediaFavorite(main.current_playlist[0])
    assert main.favorites.get_favorites_in_group('IPTV Dream')

    intro = importlib.import_module('IPTVDream.intro').DreamIntro(session, 'pl')
    intro._start()
    for n in range(30):
        intro._tick()
    assert intro.closed_result == (True,)
    assert intro.finished

    main.startLoading('Mutation', cancellable=False)
    main.close()
    assert not main._closed
    main.stopLoading()
    main.close()
    assert main._tasks.closed
    print('Receiver UI smoke: OK (startup, menus, file, Xtream worker, browser, player handoff, favorites, intro, close)')
