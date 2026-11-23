"""Headless smoke test for the Mirror+ plug-in via the GIMP PDB.

Run inside gimp-console with the python-fu-eval batch interpreter:
    -b "import runpy; runpy.run_path(r'<this file>')"
Env: MIRROR_SMOKE_OUT = path of the result file (one line per check).
Builds a 200x200 image with one 60x20 layer offset from the center, runs
python-fu-mirror-plus non-interactively with 4 directions, full mask, merge on,
then checks the image holds one layer whose bounds grew to cover the rotations.
Case 2: unmerged tinted 3-way on layer "dots". Case 3: visible=True, 2 directions,
merge on; one new top layer named "Visible" covering the whole image.
"""
import os

import gi

gi.require_version("Gimp", "3.0")
from gi.repository import Gimp  # noqa: E402

lines = []


def check(label, ok, detail=""):
    lines.append(f"{'PASS' if ok else 'FAIL'} {label} {detail}".rstrip())


def run():
    image = Gimp.Image.new(200, 200, Gimp.ImageBaseType.RGB)
    layer = Gimp.Layer.new(image, "bar", 60, 20, Gimp.ImageType.RGBA_IMAGE, 100.0,
                           Gimp.LayerMode.NORMAL)
    image.insert_layer(layer, None, 0)
    layer.set_offsets(20, 90)
    Gimp.context_set_foreground(Gimp.color_parse_hex("#ff0000"))
    layer.edit_fill(Gimp.FillType.FOREGROUND)

    pdb = Gimp.get_pdb()
    proc = pdb.lookup_procedure("python-fu-mirror-plus")
    check("procedure registered", proc is not None)
    if proc is None:
        return
    config = proc.create_config()
    config.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
    config.set_property("image", image)
    config.set_core_object_array("drawables", [layer])
    config.set_property("directions", 4)
    config.set_property("mask", 15)
    config.set_property("merge", True)
    config.set_property("tint", False)
    result = proc.run(config)
    status = result.index(0)
    check("run status SUCCESS", status == Gimp.PDBStatusType.SUCCESS, str(status))

    layers = image.get_layers()
    check("one merged layer", len(layers) == 1, str(len(layers)))
    if layers:
        merged = layers[0]
        ok, x, y = merged.get_offsets()
        w, h = merged.get_width(), merged.get_height()
        # 60x20 bar centered at (50,100) rotated 0/90/180/270 spans 60x60 around the center.
        check("merged name kept", merged.get_name() == "bar", merged.get_name())
        check("bounds cover rotations", w >= 60 and h >= 60, f"{w}x{h} at {x},{y}")
        cx, cy = x + w / 2, y + h / 2
        check("center preserved", abs(cx - 50) <= 1 and abs(cy - 100) <= 1, f"{cx},{cy}")
        # Pixel at the top arm (vertical copy) must be opaque red.
        sample = merged.get_pixel(50 - x, 75 - y)
        rgba = sample.get_rgba() if hasattr(sample, "get_rgba") else None
        check("rotated arm painted", rgba is not None and rgba[0] > 0.9 and rgba[3] > 0.9, str(rgba))

    # Unmerged run with tint tags on a fresh layer.
    layer2 = Gimp.Layer.new(image, "dots", 40, 10, Gimp.ImageType.RGBA_IMAGE, 100.0,
                            Gimp.LayerMode.NORMAL)
    image.insert_layer(layer2, None, 0)
    config2 = proc.create_config()
    config2.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
    config2.set_property("image", image)
    config2.set_core_object_array("drawables", [layer2])
    config2.set_property("directions", 3)
    config2.set_property("mask", 7)
    config2.set_property("merge", False)
    config2.set_property("tint", True)
    result2 = proc.run(config2)
    check("unmerged run SUCCESS", result2.index(0) == Gimp.PDBStatusType.SUCCESS)
    names = [item.get_name() for item in image.get_layers()]
    check("three tagged copies", len(names) == 4, ";".join(names))
    tags = {item.get_color_tag() for item in image.get_layers() if item.get_name() != "bar"}
    check("distinct color tags", len(tags) == 3, str(tags))

    # Visible source: fans the composite, adds one top layer, keeps the originals.
    before = len(image.get_layers())
    config3 = proc.create_config()
    config3.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
    config3.set_property("image", image)
    config3.set_core_object_array("drawables", [image.get_layers()[0]])  # layer2 was consumed
    config3.set_property("directions", 2)
    config3.set_property("mask", 3)
    config3.set_property("merge", True)
    config3.set_property("visible", True)
    result3 = proc.run(config3)
    check("visible run SUCCESS", result3.index(0) == Gimp.PDBStatusType.SUCCESS,
          str(result3.index(0)) + " " + str(result3.index(1) if result3.length() > 1 else ""))
    top_layers = image.get_layers()
    check("visible adds one layer", len(top_layers) == before + 1,
          f"{before}->{len(top_layers)}")
    check("visible layer on top", top_layers[0].get_name() == "Visible", top_layers[0].get_name())
    vis = top_layers[0]
    check("visible bounds cover image", vis.get_width() >= 200 and vis.get_height() >= 200,
          f"{vis.get_width()}x{vis.get_height()}")

    # Empty mask: nothing to fan, so no stray Visible layer may appear.
    before = len(image.get_layers())
    config4 = proc.create_config()
    config4.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
    config4.set_property("image", image)
    config4.set_core_object_array("drawables", [image.get_layers()[0]])
    config4.set_property("directions", 4)
    config4.set_property("mask", 0)
    config4.set_property("visible", True)
    proc.run(config4)
    check("visible empty mask adds no layer", len(image.get_layers()) == before,
          f"{before}->{len(image.get_layers())}")
    image.delete()


try:
    run()
except Exception as exc:  # noqa: BLE001 - report every failure kind
    lines.append(f"FAIL exception {type(exc).__name__}: {exc}")

out = os.environ.get("MIRROR_SMOKE_OUT")
if out:
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
print("\n".join(lines))
