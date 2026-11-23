#!/usr/bin/env python3
"""Mirror+ : GIMP 3 plug-in that fans a layer out into rotated copies.

Pick directions on a wind rose, preview the result, then Apply: the layer is
copied once per selected arrow, each copy rotated around the layer center by
the arrow angle, and the copies are merged back into a single layer (or kept
as separate, color-tagged layers). The Visible source fans the visible
composite of the whole image instead and keeps the original layers beneath.

Install: the user plug-ins folder of the installed GIMP 3 series, for example
%APPDATA%\\GIMP\\3.2\\plug-ins\\mirror-plus\\mirror-plus.py, plus the
mirror_plus_*.py modules next to it. Menu: Layer > Transform > Mirror+...
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi  # noqa: E402

gi.require_version("Gimp", "3.0")
gi.require_version("GimpUi", "3.0")
from gi.repository import Gimp, GimpUi, GLib, GObject  # noqa: E402

import mirror_plus_geometry as geo  # noqa: E402
from mirror_plus_apply import apply_mirror, apply_mirror_visible  # noqa: E402

PROC_NAME = "python-fu-mirror-plus"
DEFAULT_DIRECTIONS = 8


def run_mirror_plus(procedure, run_mode, image, drawables, config, _data):
    layers = [d for d in drawables if isinstance(d, Gimp.Layer)]
    if not layers:
        return procedure.new_return_values(
            Gimp.PDBStatusType.CALLING_ERROR,
            GLib.Error("Mirror+ needs at least one selected layer."))

    directions = config.get_property("directions")
    mask = config.get_property("mask")
    merge = config.get_property("merge")
    tint = config.get_property("tint")
    visible = config.get_property("visible")

    if run_mode == Gimp.RunMode.INTERACTIVE:
        GimpUi.init(PROC_NAME)
        from mirror_plus_ui import MirrorPlusDialog  # GTK only when a display exists

        settings = MirrorPlusDialog(image, layers[0], directions, mask, merge, tint, visible).run()
        if settings is None:
            return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())
        directions, mask = settings["directions"], settings["mask"]
        merge, tint = settings["merge"], settings["tint"]
        visible = settings["visible"]
        config.set_property("directions", directions)
        config.set_property("mask", mask)
        config.set_property("merge", merge)
        config.set_property("tint", tint)
        config.set_property("visible", visible)

    if visible:
        apply_mirror_visible(image, directions, mask, merge=merge, tag_colors=tint)
    else:
        for layer in layers:
            apply_mirror(image, layer, directions, mask, merge=merge, tag_colors=tint)
    Gimp.displays_flush()
    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())


class MirrorPlus(Gimp.PlugIn):
    def do_set_i18n(self, _name):
        return False

    def do_query_procedures(self):
        return [PROC_NAME]

    def do_create_procedure(self, name):
        procedure = Gimp.ImageProcedure.new(self, name, Gimp.PDBProcType.PLUGIN,
                                            run_mirror_plus, None)
        procedure.set_image_types("*")
        procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.DRAWABLE
                                       | Gimp.ProcedureSensitivityMask.DRAWABLES)
        procedure.set_menu_label("Mirror+...")
        procedure.add_menu_path("<Image>/Layer/Transform")
        procedure.set_documentation(
            "Fan a layer into rotated copies picked on a wind rose",
            "Copies the layer once per selected direction, rotates each copy "
            "around the layer center and merges the copies into one layer.",
            name)
        procedure.set_attribution("Levia Labs", "Levia Labs", "2026")
        procedure.add_int_argument("directions", "Directions", "Number of arrows on the rose",
                                   geo.MIN_DIRECTIONS, geo.MAX_DIRECTIONS, DEFAULT_DIRECTIONS,
                                   GObject.ParamFlags.READWRITE)
        procedure.add_int_argument("mask", "Selected arrows",
                                   "Bitmask of selected arrows, bit 0 = north",
                                   0, geo.full_mask(geo.MAX_DIRECTIONS),
                                   geo.full_mask(DEFAULT_DIRECTIONS), GObject.ParamFlags.READWRITE)
        procedure.add_boolean_argument("merge", "Merge copies", "Merge copies into a single layer",
                                       True, GObject.ParamFlags.READWRITE)
        procedure.add_boolean_argument("tint", "Tint copies",
                                       "Tint preview copies; color-tag unmerged layers",
                                       False, GObject.ParamFlags.READWRITE)
        procedure.add_boolean_argument("visible", "Use visible",
                                       "Fan the visible image instead of the selected layer",
                                       False, GObject.ParamFlags.READWRITE)
        return procedure


Gimp.main(MirrorPlus.__gtype__, sys.argv)
