#!/usr/bin/env python3
"""Build reproducible all-architecture IPK and DEB from the same runtime."""
import argparse
import gzip
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("runtime_package", str(ROOT / "tools/runtime_package.py"))
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
PACKAGE = "enigma2-plugin-extensions-iptvdream"
PREFIX = "usr/lib/enigma2/python/Plugins/Extensions/IPTVDream"


def tar_gz(entries, epoch):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.GNU_FORMAT) as archive:
        for name, content, mode in sorted(entries):
            info = tarfile.TarInfo("./" + name)
            info.size, info.mode, info.mtime = len(content), mode, epoch
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            archive.addfile(info, io.BytesIO(content))
    return gzip.compress(stream.getvalue(), compresslevel=9, mtime=0)


def write_ar(path, entries, epoch):
    with path.open("wb") as handle:
        handle.write(b"!<arch>\n")
        for name, content in entries:
            header = "{:<16}{:<12}{:<6}{:<6}{:<8}{:<10}`\n".format(name + "/", epoch, 0, 0, "100644", len(content))
            handle.write(header.encode("ascii"))
            handle.write(content)
            if len(content) % 2:
                handle.write(b"\n")


def build(output):
    version = (ROOT / "VERSION").read_text().strip()
    if not re.match(r"^\d+[0-9A-Za-z.+~-]*$", version):
        raise ValueError("Invalid VERSION")
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "1795219200"))
    files = runtime.runtime_files(ROOT)
    entries, md5s = [], []
    total_size = 0
    for relative in files:
        content = (ROOT / relative).read_bytes()
        if relative.endswith(".py"):
            compile(content, relative, "exec")
        name = PREFIX + "/" + relative
        entries.append((name, content, 0o644))
        md5s.append(hashlib.md5(content).hexdigest() + "  " + name)
        total_size += len(content)
    payload = tar_gz(entries, epoch)
    template = (ROOT / "packaging/control.in").read_text(encoding="utf-8")
    control = template.replace("@VERSION@", version).rstrip() + "\nInstalled-Size: %d\n" % ((total_size + 1023) // 1024)
    metadata = [("control", control.encode("utf-8"), 0o644),
                ("postinst", (ROOT / "packaging/postinst").read_bytes(), 0o755),
                ("md5sums", ("\n".join(md5s) + "\n").encode("utf-8"), 0o644)]
    output.mkdir(parents=True, exist_ok=True)
    built = []
    for extension in ("ipk", "deb"):
        path = output / ("%s_%s_all.%s" % (PACKAGE, version, extension))
        write_ar(path, [("debian-binary", b"2.0\n"), ("control.tar.gz", tar_gz(metadata, epoch)), ("data.tar.gz", payload)], epoch)
        built.append(path)
        print("%s (%d bytes)" % (path, path.stat().st_size))
    checksums = "".join(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name + "\n" for path in built)
    (output / "SHA256SUMS.txt").write_text(checksums, encoding="utf-8")
    return built


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", default=str(ROOT / "release"))
    args = parser.parse_args()
    build(Path(args.output).resolve())
