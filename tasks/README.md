# tasks

Scripts behind the `Taskfile.yml` entries.

1. `install_plugin.py [DEST]`: copies `mirror-plus/*.py` into the GIMP 3 user
   plug-ins folder (default `%APPDATA%\GIMP\3.0\plug-ins\mirror-plus`).
2. `run_smoke.py [GIMP_CONSOLE]`: launches `gimp-console` headless with a clean
   environment and runs `tests/smoke_gimp.py`; exits 1 on any FAIL line.
