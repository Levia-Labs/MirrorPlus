# mirror-plus

The plug-in itself. GIMP 3 loads `mirror-plus.py` from a folder of the same
name, so this whole directory is what gets copied into the user plug-ins folder.

1. `mirror-plus.py`: procedure registration (`python-fu-mirror-plus`, menu
   `Layer > Transform > Mirror+...`), argument handling, interactive dialog hand-off.
2. `mirror_plus_geometry.py`: pure math, no GIMP imports. Arrow angles, preset
   masks, click-to-arrow mapping, tint colors, layer names.
3. `mirror_plus_apply.py`: layer operations. Copy, rotate around center, remove
   original, merge down or color-tag.
4. `mirror_plus_ui.py`: GTK dialog with the wind rose widget and the cairo preview.

Direction count is capped at 30 so the selection bitmask fits a signed 32-bit
PDB integer argument.
