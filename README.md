# IPTV Dream v6.5.2

A modern IPTV plugin for Enigma2 focused on practical everyday use: portal/MAC handling, playlist workflows, bouquet generation, Web Interface support, and stable day-to-day operation across popular images.

---

## Overview

**IPTV Dream** is an Enigma2 plugin designed to make IPTV management simpler and more reliable on supported receivers.  
It provides a unified workflow for:

- adding and managing **portal/MAC** entries
- importing and organizing IPTV content
- generating **bouquets**
- handling playback-related metadata
- working with the plugin from both **GUI** and **Web Interface**
- keeping updates and maintenance straightforward

This release focuses on **compatibility**, **stability**, and **cleaner portal handling**, especially on images where users reported installation or runtime issues.

---

## What's New in v6.5.2

Version **6.5.2** brings several practical fixes based directly on user feedback:

### Improved compatibility
- better behavior on images where entering the plugin menu caused immediate problems
- safer handling when **Pillow** is not installed
- optional picon/image features now fail gracefully instead of breaking plugin startup

### Better MAC / Portal handling
- improved support for manual and WebIF-based portal entry
- more tolerant parsing of portal configuration files
- better handling of common portal paths such as:
  - `/c`
  - `/stalker_portal/c`
- improved fallback logic for problematic live stream link creation

### More reliable bouquet generation
- improved LIVE group detection
- better handling of category/group names, including cases like **XXX**
- more consistent behavior when creating bouquets from MAC-based portals

### Web Interface improvements
- clearer handling of content modes:
  - **LIVE**
  - **VOD**
  - **SERIES**

### Maintenance and metadata updates
- version bump to **6.5.2**
- updated package metadata
- updated changelog and plugin version references
- cleaner package structure for GitHub and IPK distribution

---

## Main Features

- **Portal / MAC support**
- **M3U workflow support**
- **Bouquet creation and organization**
- **Web Interface integration**
- **Automatic update mechanism**
- **Configuration stored in simple JSON files**
- **Improved host/MAC normalization**
- **Cleaner error handling and better resilience**

---

## Supported Usage

IPTV Dream is intended for users who want a practical plugin workflow on Enigma2, including:

- adding portal addresses and MAC entries from the plugin GUI
- adding/editing entries via WebIF
- maintaining portal entries manually in JSON files
- generating bouquets from IPTV sources
- keeping configurations portable and easy to back up

---

## Installation

### Option 1: Install from IPK
Install the `.ipk` package using your preferred method for Enigma2:

```sh
opkg install /path/to/enigma2-plugin-extensions-iptvdream_6.5.2_all.ipk

Then restart Enigma2 GUI.

Option 2: Update from inside the plugin

If your build includes the integrated updater:

Open the plugin
Press the GREEN button
Run the updater
Restart Enigma2 GUI after update
Optional dependency

Some image or picon-related functionality may benefit from Pillow:

opkg install python3-pillow

As of v6.5.2, the plugin is more tolerant when Pillow is missing, but installing it is still recommended when available.

Configuration Files

Depending on your workflow, IPTV Dream may use configuration files such as:

/etc/enigma2/iptvdream_mac.json
/etc/enigma2/iptvdream_mylinks.json
Example portal entry
{
  "host": "http://example.com/stalker_portal/c",
  "mac": "00:1A:79:1F:1C:C4"
}

The plugin is now more tolerant of formatting differences and better aligned between GUI, WebIF, and manual file-based workflows.

Notes for Manual Configuration

If you prefer editing files manually:

make sure JSON syntax is valid
use full host addresses
keep one consistent host format per entry
restart GUI after major changes if needed

If a portal entry works through WebIF but not through a manual file edit, the issue is often related to:

invalid JSON formatting
hidden character differences
wrong host path
duplicated or malformed entries

Version 6.5.2 improves validation and error handling in these cases.

Troubleshooting
Plugin menu opens with errors or broken screen

Try installing:

opkg install python3-pillow

Then restart GUI.

Portal entry is added but does not work

Check:

host format
MAC format
JSON syntax
whether the portal uses /c or /stalker_portal/c
Bouquet is created but some groups are missing

Version 6.5.2 improves category detection and fallback behavior, especially for unusual or less common group names.

Manual JSON entry does not load

Make sure the file is valid JSON and saved in the correct location under /etc/enigma2/.

Changelog

See CHANGELOG.txt for full release history.

Recommended latest entry for this release:

v6.5.2
improved Pillow fallback and startup compatibility
improved portal/MAC parsing and validation
improved WebIF content mode handling
improved bouquet generation and category detection
metadata and package cleanup
Project Structure

Important files in this release include:

dream_v6.py
plugin.py
__init__.py
setup.xml
tools/mac_portal.py
tools/webif.py
tools/picon_manager_v6.py
tools/lang.py
CHANGELOG.txt
VERSION
Support

For feedback, bug reports, and compatibility notes:

Email: aio-iptv@wp.pl

When reporting a problem, include:

receiver model
image name and version
plugin version
installation method
exact error message or screenshot
whether the issue occurs in GUI, WebIF, or both
Disclaimer

This project is provided for educational and interoperability purposes for Enigma2 environments.
Users are responsible for ensuring that their IPTV sources, portals, playlists, and use cases comply with applicable law, platform rules, and service terms.

Version Information
Plugin: IPTV Dream
Version: 6.5.2
Platform: Enigma2
Release focus: compatibility, portal stability, cleaner MAC/WebIF workflow
