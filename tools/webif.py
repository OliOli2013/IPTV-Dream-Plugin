# -*- coding: utf-8 -*-
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor, error
from .lang import _
import os
import base64
import re

_server_port = None
_on_data_ready_callback = None

def is_valid_url(url):
    regex = re.compile(
        r'^(?:http|https)://' 
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|' 
        r'localhost|' 
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' 
        r'(?::\d+)?' 
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None

def get_qr_base64():
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        qr_path = os.path.join(base_path, "pic", "qrcode.png")
        if os.path.exists(qr_path):
            with open(qr_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
    except: return ""
    return ""

def get_html_page(lang):
    qr_b64 = get_qr_base64()
    qr_html = f'<img src="data:image/png;base64,{qr_b64}" alt="QR" style="width:100px;">' if qr_b64 else ""
    
    # POPRAWKA F-STRINGA: Pobieramy tekst przed wstawieniem
    try:
        support_txt = _("support_text_long", lang).replace('\n', '<br>')
    except:
        support_txt = "Support me!"

    html = f"""
    <!DOCTYPE html>
    <html lang="{lang}">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IPTV Dream v4.4 WebIF</title>
    <style>
        body {{ font-family: sans-serif; background: #222; color: #eee; text-align: center; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #333; padding: 20px; border-radius: 10px; }}
        input[type=text], input[type=password] {{ width: 100%; padding: 10px; margin: 10px 0; border-radius: 5px; border: 1px solid #555; background: #444; color: white; }}
        input[type=submit] {{ width: 100%; padding: 12px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; }}
        .tab {{ padding: 10px; cursor: pointer; display: inline-block; margin: 5px; border-bottom: 2px solid transparent; }}
        .tab.active {{ border-color: #4CAF50; color: #4CAF50; }}
        .form-section {{ display: none; }}
        .form-section.active {{ display: block; }}
        .support {{ margin-top: 20px; color: #00ff00; }}
    </style>
    <script>
        function showTab(id) {{
            document.querySelectorAll('.form-section').forEach(e => e.classList.remove('active'));
            document.getElementById(id).classList.add('active');
        }}
    </script>
    </head>
    <body>
        <div class="container">
            <h1>IPTV Dream v4.4</h1>
            <div>
                <span class="tab" onclick="showTab('m3u')">M3U</span>
                <span class="tab" onclick="showTab('xtream')">Xtream</span>
                <span class="tab" onclick="showTab('mac')">MAC Portal</span>
            </div>
            
            <div id="m3u" class="form-section active">
                <form method="POST">
                    <input type="hidden" name="type" value="m3u">
                    <input type="text" name="m3u_url" placeholder="http://playlist.m3u" required>
                    <input type="submit" value="{_("webif_submit", lang)}">
                </form>
            </div>
            <div id="xtream" class="form-section">
                <form method="POST"><input type="hidden" name="type" value="xtream">
                    <input type="text" name="xt_host" placeholder="Host" required>
                    <input type="text" name="xt_user" placeholder="User" required>
                    <input type="text" name="xt_pass" placeholder="Pass" required>
                    <input type="submit" value="{_("webif_submit", lang)}">
                </form>
            </div>
            <div id="mac" class="form-section">
                <form method="POST"><input type="hidden" name="type" value="mac">
                    <input type="text" name="mac_host" placeholder="Portal URL" required>
                    <input type="text" name="mac_addr" placeholder="MAC Address" required>
                    <input type="submit" value="{_("webif_submit", lang)}">
                </form>
            </div>
            
            <div class="support">{qr_html}<br>{support_txt}</div>
        </div>
    </body></html>
    """
    return html.encode('utf-8')

class IPTVDreamWebIf(Resource):
    isLeaf = True
    def __init__(self, callback):
        global _on_data_ready_callback
        _on_data_ready_callback = callback
    
    def render_GET(self, request):
        return get_html_page("pl")

    def render_POST(self, request):
        global _on_data_ready_callback
        try:
            req_type = request.args.get(b"type", [b""])[0].decode().strip()
            data = None
            
            if req_type == "m3u":
                url = request.args.get(b"m3u_url", [b""])[0].decode().strip()
                if is_valid_url(url): data = {"type": "m3u", "url": url}
                
            elif req_type == "xtream":
                host = request.args.get(b"xt_host", [b""])[0].decode().strip()
                if not host.startswith("http"): host = "http://" + host
                if is_valid_url(host):
                    user = request.args.get(b"xt_user", [b""])[0].decode().strip()
                    pwd = request.args.get(b"xt_pass", [b""])[0].decode().strip()
                    data = {"type": "xtream", "host": host, "user": user, "pass": pwd}
                    
            elif req_type == "mac":
                host = request.args.get(b"mac_host", [b""])[0].decode().strip()
                if not host.startswith("http"): host = "http://" + host
                if is_valid_url(host):
                    mac = request.args.get(b"mac_addr", [b""])[0].decode().strip().upper()
                    data = {"type": "mac", "host": host, "mac": mac}

            if data and _on_data_ready_callback:
                _on_data_ready_callback(data)
                return b"OK"
                
        except Exception as e:
            print(f"WEBIF ERROR: {e}")
            
        return b"Error"

def start_web_server(port, on_data_ready):
    global _server_port
    if _server_port: return
    try:
        root = IPTVDreamWebIf(on_data_ready)
        _server_port = reactor.listenTCP(port, Site(root))
    except: pass

def stop_web_server():
    global _server_port
    if _server_port:
        try:
            _server_port.stopListening()
            _server_port = None
        except: pass
