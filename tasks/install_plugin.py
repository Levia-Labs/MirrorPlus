"""Copy the Mirror+ plug-in into a GIMP 3 user plug-ins folder.

Usage: install_plugin.py [DEST]
DEST defaults to %APPDATA%/GIMP/<3.x>/plug-ins/mirror-plus on Windows and
~/.config/GIMP/<3.x>/plug-ins/mirror-plus elsewhere, where <3.x> is the newest
existing GIMP 3 profile folder (3.0 when none exists). Existing files are
overwritten; stale files in DEST are left alone. Prints the destination and
the number of files copied.
"""
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "mirror-plus"


def _gimp_series(gimp_dir: Path) -> str:
    """Newest existing 3.x profile folder; GIMP 3.2 reads 3.2/, not 3.0/, so a
    fixed 3.0 target leaves a stale copy running in newer releases."""
    series = [p.name for p in gimp_dir.glob("3.*") if p.is_dir()]
    if not series:
        return "3.0"
    return max(series, key=lambda s: tuple(int(x) for x in s.split(".") if x.isdigit()))


def default_dest() -> Path:
    if os.name == "nt":
        base = Path(os.environ["APPDATA"])
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    gimp_dir = base / "GIMP"
    return gimp_dir / _gimp_series(gimp_dir) / "plug-ins" / "mirror-plus"


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
