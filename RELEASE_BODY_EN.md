# IPTV Dream 8.0.1

Maintenance release based on a full review of version 8.0.0.

Highlights:

- fixed channels displayed as `N/A` after bouquet export;
- fixed black playback for unresolved MAC/Stalker loopback links (`127.0.0.1`);
- local portal commands are resolved even on lists larger than 400 channels;
- safe Enigma2 service-reference URL and channel-name encoding;
- reliable export reporting, `bouquets.tv` backup and stale-entry cleanup;
- source-aware bouquet sets plus a one-step option to remove every old IPTV Dream bouquet;
- collision-resistant M3U/Xtream/MAC source names without leaking usernames or MAC fragments;
- WebIF automatically falls back when port 9999 is occupied;
- EPG XML, picon download, logging, installer and updater hardening;
- automated regression tests in GitHub Actions.

Validation: 10/10 regression tests, complete Python compilation, installer syntax check, IPK payload inspection and reproducible package build.

Install from `/tmp`:

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-iptvdream_8.0.1_all.ipk
init 4
sleep 2
init 3
```
