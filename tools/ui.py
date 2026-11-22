# -*- coding: utf-8 -*-
"""Scale built-in skins to the actual Enigma2 desktop, including SD images."""
import re
import xml.etree.ElementTree as ET


def fit_skin(skin, desktop_size=None):
    try:
        if desktop_size is None:
            from enigma import getDesktop
            size = getDesktop(0).size()
            desktop_size = size.width(), size.height()
        factor = min(desktop_size[0] / 1280.0, desktop_size[1] / 720.0)
        if abs(factor - 1.0) < 0.01:
            return skin
        root = ET.fromstring(skin)
        for element in root.iter():
            for name in ("position", "size"):
                value = element.get(name, "")
                if re.match(r"^\d+,\d+$", value):
                    element.set(name, ",".join(str(max(0, round(int(n) * factor))) for n in value.split(",")))
            for name in ("itemHeight", "borderWidth"):
                if element.get(name, "").isdigit():
                    element.set(name, str(max(1, round(int(element.get(name)) * factor))))
            if ";" in element.get("font", ""):
                family, size = element.get("font").rsplit(";", 1)
                if size.isdigit():
                    element.set("font", "%s;%d" % (family, max(10, round(int(size) * factor))))
        return ET.tostring(root, encoding="unicode")
    except Exception:
        return skin
