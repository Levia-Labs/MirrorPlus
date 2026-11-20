"""Run tests/smoke_gimp.py inside a headless GIMP 3 and report PASS/FAIL lines.

Usage: run_smoke.py [GIMP_CONSOLE]
GIMP_CONSOLE is the path to gimp-console-3.x.exe; the GIMP_CONSOLE environment
variable or a search of common install folders is used when omitted. The
plug-in must already be installed (see install_plugin.py). Exit code 1 when
any check fails or no result file appears.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SMOKE = ROOT / "tests" / "smoke_gimp.py"
CANDIDATES = (
    r"X:\GIMP 3\bin",
    r"C:\Program Files\GIMP 3\bin",
    r"C:\Program Files\GIMP 3.2\bin",
)


def find_console() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    if os.environ.get("GIMP_CONSOLE"):
        return Path(os.environ["GIMP_CONSOLE"])
    for folder in CANDIDATES:
        for name in ("gimp-console-3.2.exe", "gimp-console-3.0.exe", "gimp-console-3.exe"):
            candidate = Path(folder) / name
            if candidate.exists():
                return candidate
    sys.exit("gimp-console not found; pass its path or set GIMP_CONSOLE")


def clean_env(console: Path) -> dict:
    # Python and MSYS variables inherited from a Git Bash shell break GIMP's bundled
    # Python (gi DLL load fails), so drop them and pin PATH to the GIMP bin folder.
    # Everything else stays: stripping SYSTEMDRIVE or PROGRAMDATA makes Windows
    # expand "%SystemDrive%" literally and litter the working directory.
    drop_prefixes = ("PYTHON", "MSYS", "MINGW", "VIRTUAL_ENV", "UV_", "GI_TYPELIB", "GSETTINGS")
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith(drop_prefixes)}
    system32 = Path(os.environ.get("SYSTEMROOT", r"C:\Windows")) / "System32"
    env["PATH"] = os.pathsep.join([str(console.parent), str(system32)])
    return env


def main() -> None:
    console = find_console()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "smoke_out.txt"
        env = clean_env(console)
        env["MIRROR_SMOKE_OUT"] = str(out)
        batch = f"import runpy; runpy.run_path(r'{SMOKE}')"
        subprocess.run(
            [str(console), "-idf", "--batch-interpreter", "python-fu-eval", "-b", batch, "--quit"],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
            timeout=300)
        if not out.exists():
            sys.exit("no result file: plug-in not registered or GIMP failed to start")
        lines = out.read_text(encoding="utf-8").splitlines()
    print("\n".join(lines))
    failed = [line for line in lines if line.startswith("FAIL")]
    print(f"{len(lines) - len(failed)} passed, {len(failed)} failed")
    sys.exit(1 if failed else 0)


main()
