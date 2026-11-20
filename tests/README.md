# tests

1. `test_mirror_plus_geometry.py`: unittest suite for the pure geometry module.
   Runs with any Python 3.12 (`task test`).
2. `smoke_gimp.py`: runs inside headless GIMP through the `python-fu-eval` batch
   interpreter (`task smoke`). Builds a small image, calls
   `python-fu-mirror-plus` through the PDB in merged and unmerged mode and writes
   PASS/FAIL lines to the file named by `MIRROR_SMOKE_OUT`.
