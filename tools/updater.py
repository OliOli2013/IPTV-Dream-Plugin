# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import os
import re
import shutil
import tempfile

from .net import http_get
from .logger import get_logger, mask_sensitive

REPO_ZIP = "https://github.com/OliOli2013/IPTV-Dream-Plugin/archive/refs/heads/main.zip"
CHANGELOG_URL = "https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/CHANGELOG.txt"
VERSION_URL = "https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/VERSION"
PLUGIN_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/IPTVDream"
SAFE_BAK_DIR = os.path.join(os.path.dirname(PLUGIN_DIR), ".IPTVDream_BAK")
LOG_UPD = get_logger("IPTVDream.UPDATER", log_file="/tmp/iptvdream.log", debug=False)


def _read_text(path, default="unknown"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            value = (f.read() or "").strip()
            return value or default
    except Exception:
        return default


def _get_local_version():
    return _read_text(os.path.join(PLUGIN_DIR, "VERSION"), default="unknown")


def _parse_version(value):
    nums = [int(x) for x in re.findall(r"\d+", (value or "").strip())]
    if not nums:
        return (0,)
    return tuple(nums[:4])


def _is_remote_newer(local, remote):
    return _parse_version(remote) > _parse_version(local)


def _get_remote_info():
    try:
        r_ver = http_get(VERSION_URL, timeout=(5, 5), retries=2, backoff=0.8)
        r_ver.raise_for_status()
        remote_ver = (r_ver.text or "").strip()

        changelog = ""
        try:
            r_log = http_get(CHANGELOG_URL, timeout=(5, 10), retries=2, backoff=0.8)
            if r_log.status_code == 200:
                changelog = r_log.text or ""
        except Exception as e:
            try:
                LOG_UPD.info("changelog fetch skipped: %s", mask_sensitive(e))
            except Exception:
                pass

        return remote_ver, changelog
    except Exception as e:
        try:
            LOG_UPD.warning("remote info fetch failed: %s", mask_sensitive(e))
        except Exception:
            pass
        return None, None


def check_update():
    local = _get_local_version()
    remote, changelog = _get_remote_info()

    if not remote:
        return False, local, "NETWORK_ERROR", None

    if _is_remote_newer(local, remote):
        return True, local, remote, changelog

    return False, local, remote, None


def _find_extracted_plugin_dir(root_dir):
    candidates = []
    for current, _dirs, files in os.walk(root_dir):
        fset = set(files)
        if "plugin.py" in fset and ("VERSION" in fset or "dream_v6.py" in fset):
            candidates.append(current)

    if not candidates:
        for current, _dirs, files in os.walk(root_dir):
            if "plugin.py" in files:
                candidates.append(current)

    if not candidates:
        raise Exception("Błąd struktury ZIP: Nie znaleziono katalogu wtyczki.")

    def _score(path):
        name = os.path.basename(path).lower()
        depth = path.count(os.sep)
        score = depth
        if name == "iptvdream":
            score -= 5
        if os.path.exists(os.path.join(path, "VERSION")):
            score -= 2
        return score, len(path)

    candidates.sort(key=_score)
    return candidates[0]


def _cleanup_package_artifacts(root_dir):
    for current, dirs, files in os.walk(root_dir):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(current, d), ignore_errors=True)
        for fname in files:
            full = os.path.join(current, fname)
            if fname.endswith((".pyc", ".pyo")):
                try:
                    os.remove(full)
                except Exception:
                    pass
            elif fname in ("test_plugin.py",):
                try:
                    os.remove(full)
                except Exception:
                    pass


def _apply_permissions(root_dir):
    try:
        os.chmod(root_dir, 0o755)
    except Exception:
        pass

    for current, dirs, files in os.walk(root_dir):
        for d in dirs:
            try:
                os.chmod(os.path.join(current, d), 0o755)
            except Exception:
                pass
        for fname in files:
            path = os.path.join(current, fname)
            mode = 0o644
            if fname.endswith((".py", ".sh")):
                mode = 0o755
            try:
                os.chmod(path, mode)
            except Exception:
                pass


def do_update():
    tmp = tempfile.mkdtemp(prefix="iptvdream_upd_")
    zip_path = os.path.join(tmp, "main.zip")
    extracted_folder = None

    try:
        r = http_get(REPO_ZIP, timeout=(10, 60), retries=2, backoff=1.0)
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            f.write(r.content)

        shutil.unpack_archive(zip_path, tmp)
        extracted_folder = _find_extracted_plugin_dir(tmp)
        _cleanup_package_artifacts(extracted_folder)

        if os.path.exists(SAFE_BAK_DIR):
            shutil.rmtree(SAFE_BAK_DIR)

        if os.path.exists(PLUGIN_DIR):
            shutil.move(PLUGIN_DIR, SAFE_BAK_DIR)

        shutil.move(extracted_folder, PLUGIN_DIR)
        _cleanup_package_artifacts(PLUGIN_DIR)
        _apply_permissions(PLUGIN_DIR)

        if os.path.exists(SAFE_BAK_DIR):
            shutil.rmtree(SAFE_BAK_DIR, ignore_errors=True)
        return True
    except Exception as e:
        try:
            LOG_UPD.error("update failed: %s", mask_sensitive(e))
        except Exception:
            pass
        if os.path.exists(SAFE_BAK_DIR) and not os.path.exists(PLUGIN_DIR):
            try:
                shutil.move(SAFE_BAK_DIR, PLUGIN_DIR)
            except Exception:
                pass
        raise
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
