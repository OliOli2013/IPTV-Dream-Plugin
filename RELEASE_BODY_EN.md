# IPTV Dream v8.0.0

A major Enigma2 IPTV Dream update combining the 7.0.1 stability audit with clean bouquet/channel naming and a refreshed AIO Panel-inspired interface.

## Highlights

- **Bouquet display names now match the playlist group name only** — no playlist, username or portal prefix.
- Technical country/language prefixes are removed from channel and group names, for example:
  - `|DE| HOPE TV` → `HOPE TV`
  - `[PL] TVP 1 HD` → `TVP 1 HD`
  - `UK - BBC ONE FHD` → `BBC ONE FHD`
- Clean names improve **EPG and picon matching**, while the original `tvg-id` remains preferred.
- Visible quality suffixes such as `HD/FHD/UHD/4K` are preserved.
- Channel normalization was corrected for names such as **CANAL+**, **TV PULS**, **CHANNEL 4** and **KANAL D**.
- New AIO Panel-inspired dark navy/cyan/green UI and IPTV Dream branding.
- Context-sensitive help updates immediately when a menu item is highlighted.
- Help text is available in **PL / EN / DE / ES / AR / RU**.
- The main screen now contains a QR code and the project website: `https://olioli2013.github.io/aio-iptv-projekt/`.
- WebIF menu text is cleaner; the full `IP:9999` address is shown in the information panel.
- Playlist group navigation was also fixed.

## Installation

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-iptvdream_8.0.0_all.ipk
init 4
sleep 2
init 3
```

GitHub installer:

```sh
wget -qO - https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh | /bin/sh
```

**Author:** Paweł Pawełek  
**Project website:** `https://olioli2013.github.io/aio-iptv-projekt/`
