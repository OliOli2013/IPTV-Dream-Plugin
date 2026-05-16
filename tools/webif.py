# -*- coding: utf-8 -*-
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor
from .lang import _, normalize_lang, SUPPORTED_LANGS, LANGUAGE_NAMES
import os
import base64
import re
import json

# Shared plugin config (v6)
CONFIG_FILE = "/etc/enigma2/iptvdream_v6_config.json"

_server_port = None
_on_data_ready_callback = None


def is_valid_url(url):
    """Allow http/https URLs and optional IPTV pipe options after URL."""
    try:
        url = (url or '').split('|', 1)[0].strip()
    except Exception:
        pass
    regex = re.compile(
        r'^(?:http|https)://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,63}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None


def _img_base64(rel_path):
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        img_path = os.path.join(base_path, *rel_path.split('/'))
        if os.path.exists(img_path):
            with open(img_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception:
        pass
    return ""


def get_qr_base64():
    return _img_base64("pic/qrcode.png")


def get_logo_base64():
    return _img_base64("pic/pawel_logo.png")


def _read_plugin_version():
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ver_path = os.path.join(base_path, "VERSION")
        if os.path.exists(ver_path):
            with open(ver_path, "r", encoding="utf-8") as f:
                v = (f.read() or "").strip()
                return v or "6.6.0"
    except Exception:
        pass
    return "6.6.0"


def _detect_lang_from_system():
    try:
        from Components.Language import language
        l = (language.getLanguage() or "en")[:2].lower()
        return normalize_lang(l, "en")
    except Exception:
        pass
    return "en"


def _detect_lang_from_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f) or {}
            l = str(cfg.get("language", "auto")).strip().lower()
            if l == "auto":
                return _detect_lang_from_system()
            return normalize_lang(l, "en")
    except Exception:
        pass
    return None


def _html_escape(text):
    return (str(text or "")
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


def _lang_switch_html(current):
    items = []
    for code in SUPPORTED_LANGS:
        cls = "active" if code == current else ""
        label = LANGUAGE_NAMES.get(code, code.upper())
        items.append('<a class="lang %s" href="?lang=%s">%s</a>' % (cls, code, _html_escape(label)))
    return "".join(items)


def get_html_page(lang):
    lang = normalize_lang(lang, "en")
    version = _read_plugin_version()
    qr_b64 = get_qr_base64()
    logo_b64 = get_logo_base64()
    qr_html = '<img src="data:image/png;base64,%s" alt="QR" class="qr">' % qr_b64 if qr_b64 else ""
    logo_html = '<img src="data:image/png;base64,%s" alt="Paweł Pawełek" class="logo">' % logo_b64 if logo_b64 else ""

    try:
        support_txt = _html_escape(_("support_text_long", lang)).replace('\n', '<br>')
    except Exception:
        support_txt = "Support me!"

    ph_m3u = _html_escape(_('webif_ph_m3u', lang))
    ph_xt_host = _html_escape(_('webif_ph_xt_host', lang))
    ph_xt_user = _html_escape(_('webif_ph_xt_user', lang))
    ph_xt_pass = _html_escape(_('webif_ph_xt_pass', lang))
    ph_mac_host = _html_escape(_('webif_ph_mac_host', lang))
    ph_mac_addr = _html_escape(_('webif_ph_mac_addr', lang))

    html = """
<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IPTV Dream v{version} WebIF</title>
<style>
    body {{ font-family: Arial, sans-serif; background:#111827; color:#e5e7eb; text-align:center; padding:20px; }}
    .container {{ max-width:680px; margin:0 auto; background:#1f2937; padding:22px; border-radius:18px; box-shadow:0 0 28px rgba(0,0,0,.35); }}
    .logo {{ width:118px; max-width:35%; border-radius:10px; margin-bottom:10px; }}
    .qr {{ width:96px; border-radius:8px; margin-top:8px; }}
    input[type=text], input[type=password], select {{ box-sizing:border-box; width:100%; padding:11px; margin:10px 0; border-radius:8px; border:1px solid #4b5563; background:#111827; color:white; }}
    input[type=submit] {{ width:100%; padding:13px; background:#2563eb; color:white; border:0; border-radius:8px; cursor:pointer; font-weight:bold; }}
    input[type=submit]:hover {{ background:#1d4ed8; }}
    .tab {{ padding:10px 12px; cursor:pointer; display:inline-block; margin:5px; border-bottom:2px solid transparent; font-weight:bold; }}
    .tab.active {{ border-color:#60a5fa; color:#60a5fa; }}
    .form-section {{ display:none; }} .form-section.active {{ display:block; }}
    .support {{ margin-top:20px; color:#9ca3af; }}
    .warning {{ color:#facc15; font-weight:bold; margin:14px 0; }}
    h1 {{ color:#facc15; margin:4px 0 16px; }}
    .langs {{ margin:8px 0 14px; }}
    .lang {{ display:inline-block; margin:3px; padding:6px 9px; border-radius:999px; text-decoration:none; color:#d1d5db; background:#374151; font-size:13px; }}
    .lang.active {{ color:#111827; background:#facc15; }}
</style>
<script>
    function showTab(id, ev) {{
        document.querySelectorAll('.form-section').forEach(function(e) {{ e.classList.remove('active'); }});
        document.getElementById(id).classList.add('active');
        document.querySelectorAll('.tab').forEach(function(e) {{ e.classList.remove('active'); }});
        if (ev && ev.target) ev.target.classList.add('active');
    }}
</script>
</head>
<body>
<div class="container">
    {logo_html}
    <h1>IPTV Dream v{version}</h1>
    <div class="langs">{langs}</div>
    <div>
        <span class="tab active" onclick="showTab('m3u', event)">{tab_m3u}</span>
        <span class="tab" onclick="showTab('xtream', event)">{tab_xtream}</span>
        <span class="tab" onclick="showTab('mac', event)">{tab_mac}</span>
    </div>

    <div id="m3u" class="form-section active">
        <form method="POST">
            <input type="hidden" name="type" value="m3u">
            <input type="text" name="m3u_url" placeholder="{ph_m3u}" required>
            <input type="submit" value="{submit}">
        </form>
    </div>

    <div id="xtream" class="form-section">
        <form method="POST">
            <input type="hidden" name="type" value="xtream">
            <input type="text" name="xt_host" placeholder="{ph_xt_host}" required>
            <input type="text" name="xt_user" placeholder="{ph_xt_user}" required>
            <input type="password" name="xt_pass" placeholder="{ph_xt_pass}" required>
            <input type="submit" value="{submit}">
        </form>
    </div>

    <div id="mac" class="form-section">
        <form method="POST">
            <input type="hidden" name="type" value="mac">
            <input type="text" name="mac_host" placeholder="{ph_mac_host}" required>
            <input type="text" name="mac_addr" placeholder="{ph_mac_addr}" required>
            <select name="mac_mode">
                <option value="live">LIVE</option>
                <option value="vod">VOD</option>
                <option value="series">SERIES</option>
                <option value="adult">ADULT / XXX</option>
            </select>
            <input type="submit" value="{submit}">
        </form>
    </div>

    <div class="warning">{warning}</div>
    <div class="support">{qr_html}<br>{support_txt}</div>
</div>
</body>
</html>
""".format(
        lang=lang, version=version, logo_html=logo_html, langs=_lang_switch_html(lang),
        tab_m3u=_html_escape(_('webif_tab_m3u', lang)),
        tab_xtream=_html_escape(_('webif_tab_xtream', lang)),
        tab_mac=_html_escape(_('webif_tab_mac', lang)),
        ph_m3u=ph_m3u, ph_xt_host=ph_xt_host, ph_xt_user=ph_xt_user,
        ph_xt_pass=ph_xt_pass, ph_mac_host=ph_mac_host, ph_mac_addr=ph_mac_addr,
        submit=_html_escape(_('webif_submit', lang)), warning=_html_escape(_('webif_warning', lang)),
        qr_html=qr_html, support_txt=support_txt)
    return html.encode('utf-8')


class IPTVDreamWebIf(Resource):
    """HTTP WebIF for IPTV Dream."""
    isLeaf = True

    def __init__(self, callback):
        global _on_data_ready_callback
        _on_data_ready_callback = callback

    def render_GET(self, request):
        try:
            qlang = request.args.get(b"lang", [b""])[0].decode("utf-8", "ignore").strip().lower()
        except Exception:
            qlang = ""
        lang = normalize_lang(qlang, "") if qlang else ""
        if not lang:
            lang = _detect_lang_from_config() or _detect_lang_from_system()
        return get_html_page(lang)

    def render_POST(self, request):
        global _on_data_ready_callback
        try:
            req_type = request.args.get(b"type", [b""])[0].decode('utf-8', 'ignore').strip().lower()
            data = None

            if req_type == "m3u":
                url = request.args.get(b"m3u_url", [b""])[0].decode('utf-8', 'ignore').strip()
                if is_valid_url(url):
                    data = {"type": "m3u", "url": url}

            elif req_type == "xtream":
                host = request.args.get(b"xt_host", [b""])[0].decode('utf-8', 'ignore').strip()
                if host and not host.startswith(("http://", "https://")):
                    host = "http://" + host
                if is_valid_url(host):
                    user = request.args.get(b"xt_user", [b""])[0].decode('utf-8', 'ignore').strip()
                    pwd = request.args.get(b"xt_pass", [b""])[0].decode('utf-8', 'ignore').strip()
                    if user and pwd:
                        data = {"type": "xtream", "host": host, "user": user, "pass": pwd}

            elif req_type == "mac":
                host = request.args.get(b"mac_host", [b""])[0].decode('utf-8', 'ignore').strip()
                if host and not host.startswith(("http://", "https://")):
                    host = "http://" + host
                if is_valid_url(host):
                    mac = request.args.get(b"mac_addr", [b""])[0].decode('utf-8', 'ignore').strip().upper()
                    mode = request.args.get(b"mac_mode", [b"live"])[0].decode('utf-8', 'ignore').strip().lower()
                    if mode not in ("live", "vod", "series", "adult"):
                        mode = "live"
                    if mac:
                        data = {"type": "mac", "host": host, "mac": mac, "mode": mode}

            if data and _on_data_ready_callback:
                _on_data_ready_callback(data)
                return b"OK"

        except Exception as e:
            print("WEBIF ERROR: %s" % e)

        return b"Error"


def start_web_server(port, on_data_ready):
    """Start WebIF server."""
    global _server_port
    if _server_port:
        return
    try:
        root = IPTVDreamWebIf(on_data_ready)
        _server_port = reactor.listenTCP(port, Site(root))
        print("[IPTVDream] Web interface started on port %s" % port)
    except Exception as e:
        print("[IPTVDream] Failed to start web server: %s" % e)


def stop_web_server():
    """Stop WebIF server."""
    global _server_port
    if _server_port:
        try:
            _server_port.stopListening()
            _server_port = None
            print("[IPTVDream] Web interface stopped")
        except Exception as e:
            print("[IPTVDream] Failed to stop web server: %s" % e)
