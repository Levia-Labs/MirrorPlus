"""Copy the Mirror+ plug-in into a GIMP 3 user plug-ins folder.

Usage: install_plugin.py [DEST]
DEST defaults to %APPDATA%/GIMP/3.0/plug-ins/mirror-plus on Windows and
~/.config/GIMP/3.0/plug-ins/mirror-plus elsewhere. Existing files are
overwritten; stale files in DEST are left alone. Prints the destination and
the number of files copied.
"""
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "mirror-plus"


def default_dest() -> Path:
    if os.name == "nt":
        base = Path(os.environ["APPDATA"])
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "GIMP" / "3.0" / "plug-ins" / "mirror-plus"


def main() -> None:
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else default_dest()
    dest.mkdir(parents=True, exist_ok=True)
    copied = 0
    for source in sorted(SOURCE.glob("*.py")):
        shutil.copy2(source, dest / source.name)
        copied += 1
    if os.name != "nt":
        (dest / "mirror-plus.py").chmod(0o755)
    print(f"{dest} ({copied} files)")


main()
