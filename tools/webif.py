# -*- coding: utf-8 -*-
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor, error
from .lang import _
import os
import base64
import re
import json

# Shared plugin config (v6)
CONFIG_FILE = "/etc/enigma2/iptvdream_v6_config.json"

_server_port = None
_on_data_ready_callback = None

def is_valid_url(url):
    # Allow optional |options after URL, e.g. URL|User-Agent=...
    try:
        url = (url or '').split('|', 1)[0].strip()
    except Exception:
        pass
    """Sprawdza czy URL jest poprawny."""
    regex = re.compile(
        r'^(?:http|https)://' 
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|' 
        r'localhost|' 
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' 
        r'(?::\d+)?' 
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None

def get_qr_base64():
    """Pobiera obraz QR jako base64."""
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        qr_path = os.path.join(base_path, "pic", "qrcode.png")
        if os.path.exists(qr_path):
            with open(qr_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
    except: 
        return ""
    return ""

def _read_plugin_version():
    """Reads plugin version from VERSION file (best-effort)."""
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ver_path = os.path.join(base_path, "VERSION")
        if os.path.exists(ver_path):
            with open(ver_path, "r", encoding="utf-8") as f:
                v = (f.read() or "").strip()
                return v or "6.4"
    except Exception:
        pass
    return "6.4"

def _detect_lang_from_system():
    """Returns 'pl' or 'en' based on Enigma2 system language."""
    try:
        from Components.Language import language
        l = (language.getLanguage() or "pl")[:2].lower()
        if l in ("pl", "en"):
            return l
    except Exception:
        pass
    return "pl"

def _detect_lang_from_config():
    """Returns 'pl' or 'en' based on plugin config file (best-effort)."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f) or {}
            l = str(cfg.get("language", "")).strip().lower()
            if l in ("pl", "en"):
                return l
    except Exception:
        pass
    return None

def get_html_page(lang):
    """Generuje stronę HTML dla interfejsu web."""
    version = _read_plugin_version()
    qr_b64 = get_qr_base64()
    qr_html = f'<img src="data:image/png;base64,{qr_b64}" alt="QR" style="width:100px;">' if qr_b64 else ""
    
    # POPRAWKA F-STRINGA: Pobieramy tekst przed wstawieniem
    try:
        support_txt = _("support_text_long", lang).replace('\n', '<br>')
    except:
        support_txt = "Support me!"

    # Localized placeholders
    ph_m3u = _('webif_ph_m3u', lang)
    ph_xt_host = _('webif_ph_xt_host', lang)
    ph_xt_user = _('webif_ph_xt_user', lang)
    ph_xt_pass = _('webif_ph_xt_pass', lang)
    ph_mac_host = _('webif_ph_mac_host', lang)
    ph_mac_addr = _('webif_ph_mac_addr', lang)

    html = f"""
    <!DOCTYPE html>
    <html lang="{lang}">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IPTV Dream v{version} WebIF</title>
    <style>
        body {{ font-family: sans-serif; background: #222; color: #eee; text-align: center; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #333; padding: 20px; border-radius: 10px; }}
        input[type=text], input[type=password] {{ width: 100%; padding: 10px; margin: 10px 0; border-radius: 5px; border: 1px solid #555; background: #444; color: white; }}
        input[type=submit] {{ width: 100%; padding: 12px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; }}
        input[type=submit]:hover {{ background: #45a049; }}
        .tab {{ padding: 10px; cursor: pointer; display: inline-block; margin: 5px; border-bottom: 2px solid transparent; font-weight: bold; }}
        .tab.active {{ border-color: #4CAF50; color: #4CAF50; }}
        .form-section {{ display: none; }}
        .form-section.active {{ display: block; }}
        .support {{ margin-top: 20px; color: #00ff00; }}
        .warning {{ color: #ffcc00; font-weight: bold; margin: 10px 0; }}
        h1 {{ color: #ffcc00; margin-bottom: 20px; }}
    </style>
    <script>
        function showTab(id) {{
            document.querySelectorAll('.form-section').forEach(e => e.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            
            // Zmiana aktywnej zakładki
            document.querySelectorAll('.tab').forEach(e => e.classList.remove('active'));
            event.target.classList.add('active');
        }}
        
        function showMessage(message) {{
            alert(message);
        }}
    </script>
    </head>
    <body>
        <div class="container">
            <h1>IPTV Dream v{version}</h1>
            <div>
                <span class="tab active" onclick="showTab('m3u')">{_('webif_tab_m3u', lang)}</span>
                <span class="tab" onclick="showTab('xtream')">{_('webif_tab_xtream', lang)}</span>
                <span class="tab" onclick="showTab('mac')">{_('webif_tab_mac', lang)}</span>
            </div>
            
            <div id="m3u" class="form-section active">
                <form method="POST">
                    <input type="hidden" name="type" value="m3u">
                    <input type="text" name="m3u_url" placeholder="{ph_m3u}" required>
                    <input type="submit" value="{_('webif_submit', lang)}">
                </form>
            </div>
            <div id="xtream" class="form-section">
                <form method="POST"><input type="hidden" name="type" value="xtream">
                    <input type="text" name="xt_host" placeholder="{ph_xt_host}" required>
                    <input type="text" name="xt_user" placeholder="{ph_xt_user}" required>
                    <input type="password" name="xt_pass" placeholder="{ph_xt_pass}" required>
                    <input type="submit" value="{_('webif_submit', lang)}">
                </form>
            </div>
            <div id="mac" class="form-section">
                <form method="POST"><input type="hidden" name="type" value="mac">
                    <input type="text" name="mac_host" placeholder="{ph_mac_host}" required>
                    <input type="text" name="mac_addr" placeholder="{ph_mac_addr}" required>
                    <input type="submit" value="{_('webif_submit', lang)}">
                </form>
            </div>
            
            <div class="warning">{_('webif_warning', lang)}</div>
            <div class="support">{qr_html}<br>{support_txt}</div>
        </div>
    </body></html>
    """
    return html.encode('utf-8')

class IPTVDreamWebIf(Resource):
    """Zasób obsługujący żądania HTTP dla interfejsu web."""
    isLeaf = True
    
    def __init__(self, callback):
        global _on_data_ready_callback
        _on_data_ready_callback = callback
    
    def render_GET(self, request):
        """Obsługuje żądania GET."""
        # Priority: explicit query param ?lang=pl/en -> plugin config -> system language
        try:
            qlang = request.args.get(b"lang", [b""])[0].decode("utf-8", "ignore").strip().lower()
        except Exception:
            qlang = ""
        if qlang in ("pl", "en"):
            lang = qlang
        else:
            lang = _detect_lang_from_config() or _detect_lang_from_system()
        return get_html_page(lang)

    def render_POST(self, request):
        """Obsługuje żądania POST."""
        global _on_data_ready_callback
        try:
            req_type = request.args.get(b"type", [b""])[0].decode().strip()
            data = None
            
            if req_type == "m3u":
                url = request.args.get(b"m3u_url", [b""])[0].decode().strip()
                if is_valid_url(url): 
                    data = {"type": "m3u", "url": url}
                
            elif req_type == "xtream":
                host = request.args.get(b"xt_host", [b""])[0].decode().strip()
                if not host.startswith("http"): 
                    host = "http://" + host
                if is_valid_url(host):
                    user = request.args.get(b"xt_user", [b""])[0].decode().strip()
                    pwd = request.args.get(b"xt_pass", [b""])[0].decode().strip()
                    if user and pwd:  # Sprawdzenie czy dane nie są puste
                        data = {"type": "xtream", "host": host, "user": user, "pass": pwd}
                
            elif req_type == "mac":
                host = request.args.get(b"mac_host", [b""])[0].decode().strip()
                if not host.startswith("http"): 
                    host = "http://" + host
                if is_valid_url(host):
                    mac = request.args.get(b"mac_addr", [b""])[0].decode().strip().upper()
                    if mac:  # Sprawdzenie czy MAC nie jest pusty
                        data = {"type": "mac", "host": host, "mac": mac}

            if data and _on_data_ready_callback:
                _on_data_ready_callback(data)
                return b"OK"
                
        except Exception as e:
            print(f"WEBIF ERROR: {e}")
            
        return b"Error"

def start_web_server(port, on_data_ready):
    """Uruchamia serwer web."""
    global _server_port
    if _server_port: 
        return
        
    try:
        root = IPTVDreamWebIf(on_data_ready)
        _server_port = reactor.listenTCP(port, Site(root))
        print(f"[IPTVDream] Web interface started on port {port}")
    except Exception as e:
        print(f"[IPTVDream] Failed to start web server: {e}")

def stop_web_server():
    """Zatrzymuje serwer web."""
    global _server_port
    if _server_port:
        try:
            _server_port.stopListening()
            _server_port = None
            print("[IPTVDream] Web interface stopped")
        except Exception as e:
            print(f"[IPTVDream] Error stopping web server: {e}")