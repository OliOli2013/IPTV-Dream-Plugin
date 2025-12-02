# -*- coding: utf-8 -*-
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor, error
from .lang import _
import os
import base64

# Globalne referencje
_server_port = None
_on_data_ready_callback = None

def get_qr_base64():
    """Wczytuje obraz QR z dysku i zwraca jako string base64"""
    try:
        # Zakładamy, że pic jest w ../pic względem tego pliku (tools/webif.py)
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        qr_path = os.path.join(base_path, "pic", "qrcode.png")
        
        if os.path.exists(qr_path):
            with open(qr_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
    except:
        return ""
    return ""

# --- HTML/FORMA ---

def get_html_page(lang):
    """Generuje interfejs HTML do wysyłania różnych danych."""
    
    qr_b64 = get_qr_base64()
    qr_html = ""
    if qr_b64:
        qr_html = f'<img src="data:image/png;base64,{qr_b64}" alt="QR Code" style="width: 100px; height: 100px; margin-bottom: 10px;">'

    # [FIX v4.1] Wyciągamy logikę z f-stringa dla starszych Pythonów (OpenPLi)
    support_text_content = _("support_text_long", lang).replace('\n', '<br>')

    html_content = f"""
    <!DOCTYPE html>
    <html lang="{lang}">
    <head>
        <meta charset="UTF-8">
        <title>IPTV Dream Web Controller</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #222; color: #eee; text-align: center; margin: 0; padding: 20px; }}
            .container {{ max-width: 700px; margin: 0 auto; background-color: #333; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }}
            h1 {{ color: #4CAF50; margin-bottom: 20px; }}
            .tab-container {{ display: flex; justify-content: center; margin-bottom: 20px; border-bottom: 2px solid #555; }}
            .tab {{ padding: 10px 20px; cursor: pointer; border-bottom: 3px solid transparent; font-weight: bold; color: #aaa; }}
            .tab:hover {{ color: white; }}
            .tab.active {{ border-bottom: 3px solid #4CAF50; color: #4CAF50; }}
            .form-section {{ display: none; text-align: left; animation: fadeIn 0.5s; }}
            .form-section.active {{ display: block; }}
            @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
            
            label {{ display: block; margin: 10px 0 5px; color: #ddd; font-size: 0.9em; }}
            input[type=text], input[type=password] {{ width: 100%; padding: 12px; margin-bottom: 15px; box-sizing: border-box; border: 2px solid #555; border-radius: 6px; background-color: #444; color: white; font-size: 16px; }}
            input[type=text]:focus, input[type=password]:focus {{ border-color: #4CAF50; outline: none; }}
            
            input[type=submit] {{ width: 100%; background-color: #4CAF50; color: white; padding: 15px; border: none; border-radius: 6px; cursor: pointer; font-size: 18px; font-weight: bold; margin-top: 10px; }}
            input[type=submit]:hover {{ background-color: #45a049; }}
            .footer {{ margin-top: 40px; font-size: 13px; color: #777; border-top: 1px solid #444; padding-top: 20px; }}
            .warning {{ color: #ff9800; font-size: 0.9em; margin-top: 20px; text-align: center; }}
            .support-section {{ margin-top: 20px; color: #00ff00; font-size: 1em; }}
        </style>
        <script>
            function showTab(tabName) {{
                document.querySelectorAll('.form-section').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
                document.getElementById(tabName).classList.add('active');
                document.getElementById('btn-' + tabName).classList.add('active');
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <h1>IPTV Dream v4.2</h1>
            
            <div class="tab-container">
                <div id="btn-m3u" class="tab active" onclick="showTab('m3u')">M3U Link</div>
                <div id="btn-xtream" class="tab" onclick="showTab('xtream')">Xtream Codes</div>
                <div id="btn-mac" class="tab" onclick="showTab('mac')">MAC Portal</div>
            </div>

            <div id="m3u" class="form-section active">
                <form method="POST">
                    <input type="hidden" name="type" value="m3u">
                    <label>M3U / M3U8 URL:</label>
                    <input type="text" name="m3u_url" placeholder="http://domain.com/playlist.m3u" required autocomplete="off">
                    <input type="submit" value="{_("webif_submit", lang)}">
                </form>
            </div>

            <div id="xtream" class="form-section">
                <form method="POST">
                    <input type="hidden" name="type" value="xtream">
                    <label>Host URL (http://domain.com:port):</label>
                    <input type="text" name="xt_host" placeholder="http://server:8080" required>
                    <label>Username:</label>
                    <input type="text" name="xt_user" required>
                    <label>Password:</label>
                    <input type="text" name="xt_pass" required>
                    <input type="submit" value="{_("webif_submit", lang)}">
                </form>
            </div>

            <div id="mac" class="form-section">
                <form method="POST">
                    <input type="hidden" name="type" value="mac">
                    <label>Portal URL (Mag/Stalker):</label>
                    <input type="text" name="mac_host" placeholder="http://mag.portal.com/c" required>
                    <label>MAC Address (00:1A:79:...):</label>
                    <input type="text" name="mac_addr" placeholder="00:1A:79:XX:XX:XX" required>
                    <input type="submit" value="{_("webif_submit", lang)}">
                </form>
            </div>

            <p class="warning">{_("webif_warning", lang)}</p>
            
            <div class="support-section">
                {qr_html}
                <p>{support_text_content}</p>
            </div>
        </div>
        <div class="footer">IPTV Dream Web Interface</div>
    </body>
    </html>
    """
    return html_content.encode("utf-8")

# --- Klasa Obsługi Żądań Twisted ---

class IPTVDreamWebIf(Resource):
    isLeaf = True

    def __init__(self, callback):
        global _on_data_ready_callback
        _on_data_ready_callback = callback
        
    def render_GET(self, request):
        lang = "pl"
        request.setHeader(b"Content-Type", b"text/html; charset=utf-8")
        return get_html_page(lang)

    def render_POST(self, request):
        global _on_data_ready_callback
        request.setHeader(b"Content-Type", b"text/html; charset=utf-8")
        lang = "pl"

        # Pobieranie typu formularza
        req_type = request.args.get(b"type", [b""])[0].decode().strip()
        data_to_send = None

        if req_type == "m3u":
            url = request.args.get(b"m3u_url", [b""])[0].decode().strip()
            if url.startswith(('http', 'https')):
                data_to_send = {"type": "m3u", "url": url}

        elif req_type == "xtream":
            host = request.args.get(b"xt_host", [b""])[0].decode().strip()
            user = request.args.get(b"xt_user", [b""])[0].decode().strip()
            pwd  = request.args.get(b"xt_pass", [b""])[0].decode().strip()
            if host and user and pwd:
                data_to_send = {"type": "xtream", "host": host, "user": user, "pass": pwd}

        elif req_type == "mac":
            host = request.args.get(b"mac_host", [b""])[0].decode().strip()
            mac  = request.args.get(b"mac_addr", [b""])[0].decode().strip()
            if host and mac:
                data_to_send = {"type": "mac", "host": host, "mac": mac}

        # Wysłanie danych do wtyczki
        if data_to_send and _on_data_ready_callback:
            _on_data_ready_callback(data_to_send)
            msg = _('webif_received', lang)
            return f"<html><body style='background:#222;color:#fff;text-align:center;padding:50px;font-family:sans-serif;'><h1>OK!</h1><p>{msg}</p><a href='.' style='color:#4CAF50'>Back</a></body></html>".encode('utf-8')
        
        return f"<html><body style='background:#222;color:red;text-align:center;padding:50px;font-family:sans-serif;'><h1>Error</h1><p>Invalid Data</p><a href='.' style='color:#fff'>Back</a></body></html>".encode('utf-8')


def start_web_server(port, on_data_ready):
    """Uruchamia serwer Twisted na podanym porcie."""
    global _server_port
    if _server_port: return 

    try:
        root = IPTVDreamWebIf(on_data_ready)
        factory = Site(root)
        _server_port = reactor.listenTCP(port, factory)
        print(f"[IPTVDream WebIF] Uruchomiono na porcie {port}")
    except error.CannotListenError as e:
        _server_port = None
        print(f"[IPTVDream WebIF] BŁĄD: {e}")

def stop_web_server():
    """Zatrzymuje serwer Twisted."""
    global _server_port
    if _server_port:
        try:
            _server_port.stopListening()
            _server_port = None
        except: pass
