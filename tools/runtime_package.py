# -*- coding: utf-8 -*-
"""One runtime manifest for packages, the installer and the online updater."""
import json
import os
from pathlib import Path
import shutil
import sys


def runtime_files(root):
    root = Path(root).resolve()
    with (root / "runtime.json").open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    files = set(manifest["files"])
    for relative in manifest["directories"]:
        directory = root / relative
        if not directory.is_dir() or directory.is_symlink() or root not in directory.resolve().parents:
            raise ValueError("Invalid runtime directory: %s" % relative)
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise ValueError("Runtime symlink rejected: %s" % path)
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in (".pyc", ".pyo", ".tmp", ".bak", ".log"):
                files.add(path.relative_to(root).as_posix())
    result = []
    for relative in sorted(files):
        path = root / relative
        if path.is_symlink() or not path.is_file() or root not in path.resolve().parents:
            raise ValueError("Missing or unsafe runtime file: %s" % relative)
        result.append(relative)
    return result


def copy_runtime(source, destination):
    source, destination = Path(source), Path(destination)
    files = runtime_files(source)
    for relative in files:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(source / relative), str(target))
        target.chmod(0o644)
    for current, _dirs, _files in os.walk(str(destination)):
        os.chmod(current, 0o755)
    return files


if __name__ == "__main__":
    copied = copy_runtime(sys.argv[1], sys.argv[2])
    print("Runtime: %d files" % len(copied))
