<p align="center"><img src="assets/logo.svg" width="140" alt="Mirror+ wind rose"></p>

# Mirror+

GIMP 3 plug-in that fans one layer out into rotated copies. Pick directions on a
wind rose, watch the live preview, press Apply: the layer is copied once per
selected arrow, every copy is rotated around the layer center by its arrow angle,
and the copies are merged back into a single layer that replaces the original.

Good for radial ornaments, snowflakes, gear teeth, mandala petals and any
"repeat this N times around a point" job without manual duplicate-rotate loops.

## Features

1. 2 to 30 directions, evenly spaced, clockwise from north.
2. Click arrows to toggle them; presets `+` (every second arrow from north),
   `x` (the arrows in between), `Full`, `None`. With 8 directions `+` is
   N/E/S/W and `x` the diagonals.
3. Live preview of the composite over a dimmed thumbnail of the image.
4. Tint: colors each copy and its arrow with a distinct hue in the preview so you
   can see which arrow contributes what. Unmerged copies get matching layer color
   tags.
5. Merge toggle: one merged layer (default) or separate layers named
   `name 45°`, `name 90°`, and so on.
6. Single undo step. The active selection is set aside during the rotations and
   restored afterwards, so whole layers rotate.
7. Source: fan the selected layer (default) or the visible composite of the whole
   image. Visible keeps the original layers and puts the result on top, like
   Layer > New from Visible.
8. Refresh preview button re-reads the thumbnails from GIMP, so changes made
   in GIMP while the dialog is open show up in the preview.
9. Scriptable: procedure `python-fu-mirror-plus` with arguments `directions`,
   `mask` (bit i selects arrow i), `merge`, `tint`, `visible`.

## Requirements

GIMP 3.2 or later. GIMP 3.0.2 on Windows shipped a broken Python runtime
(missing `libgirepository-2.0-0.dll`) and cannot load any Python plug-in.

## Quick start

```sh
git clone https://github.com/Levia-Labs/MirrorPlus.git
cd MirrorPlus
task install          # copies mirror-plus/ into the GIMP 3 user plug-ins folder
```

Without the task runner, copy the `mirror-plus` folder into
`%APPDATA%\GIMP\3.2\plug-ins\` (Windows) or `~/.config/GIMP/3.2/plug-ins/`
(Linux, macOS), using the folder that matches your installed GIMP 3 series. Restart GIMP, select a layer, open `Layer > Transform > Mirror+...`.

## Development

```sh
task test             # geometry unit tests, plain Python
task smoke            # installs, then drives the plug-in through the PDB in headless GIMP
task check            # both
```

Layout: `mirror-plus/` is the plug-in (registration, pure geometry, layer
operations, GTK dialog and preview widget), `tests/` holds the unit and smoke tests, `tasks/`
the install and smoke runners.

## Links

1. Levia Labs: https://www.levialabs.net
2. GitHub: https://github.com/Levia-Labs

## License

GPL-3.0, see [LICENSE](LICENSE).
