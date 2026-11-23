"""Layer operations for the Mirror+ GIMP plug-in.

Copies the source layer once per selected arrow, rotates each copy around the
layer center by the arrow angle and optionally merges the copies back into a
single layer that replaces the original; the Visible source first adds a
layer from the visible composite and fans that instead.
"""
import math

import gi

gi.require_version("Gimp", "3.0")
from gi.repository import Gimp  # noqa: E402

import mirror_plus_geometry as geo  # noqa: E402


def _color_tag(name):
    return getattr(Gimp.ColorTag, name, Gimp.ColorTag.NONE)


def _save_selection(image):
    """Detach the selection so transforms act on whole layers, return a restore closure."""
    if Gimp.Selection.is_empty(image):
        return lambda: None
    saved = Gimp.Selection.save(image)
    Gimp.Selection.none(image)

    def restore():
        image.select_item(Gimp.ChannelOps.REPLACE, saved)
        image.remove_channel(saved)

    return restore


def _make_copy(image, layer, parent, position, base_name, degrees):
    copy = layer.copy()
    if not copy.has_alpha():
        copy.add_alpha()
    copy.set_name(geo.layer_name(base_name, degrees))
    copy.set_visible(True)
    image.insert_layer(copy, parent, position)
    if degrees:
        # transform_rotate returns the item that now holds the pixels.
        copy = copy.transform_rotate(math.radians(degrees), True, 0.0, 0.0)
    return copy


def _merge_stack(image, copies, base_name):
    # Copies were inserted at the same position in turn, so the last one is on top.
    result = copies[-1]
    for _ in range(len(copies) - 1):
        result = image.merge_down(result, Gimp.MergeType.EXPAND_AS_NECESSARY)
    result.set_name(base_name)
    return result


def apply_mirror(image, layer, directions, mask, merge=True, tag_colors=False):
    """Run the transform on one layer. Returns the list of resulting layers."""
    indices = geo.selected_indices(mask, directions)
    if not indices:
        return []
    Gimp.context_push()
    image.undo_group_start()
    restore_selection = _save_selection(image)
    try:
        Gimp.context_set_transform_resize(Gimp.TransformResize.ADJUST)
        Gimp.context_set_interpolation(Gimp.InterpolationType.CUBIC)
        parent = layer.get_parent()
        position = image.get_item_position(layer)
        base_name = layer.get_name()
        copies = []
        for index in indices:
            degrees = geo.angle_degrees(index, directions)
            copies.append(_make_copy(image, layer, parent, position, base_name, degrees))
        image.remove_layer(layer)
        if merge:
            if len(copies) > 1:
                copies = [_merge_stack(image, copies, base_name)]
            else:
                copies[0].set_name(base_name)
        elif tag_colors:
            for index, copy in zip(indices, copies):
                copy.set_color_tag(_color_tag(geo.tag_name(index)))
        return copies
    finally:
        restore_selection()
        image.undo_group_end()
        Gimp.context_pop()


def new_visible_layer(image, name="Visible"):
    """Add the visible composite as a top layer, like Layer > New from Visible."""
    layer = Gimp.Layer.new_from_visible(image, image, name)
    image.insert_layer(layer, None, 0)
    return layer


def apply_mirror_visible(image, directions, mask, merge=True, tag_colors=False):
    """Fan the visible composite; the outer undo group makes the run one undo step."""
    if not geo.selected_indices(mask, directions):
        return []
    image.undo_group_start()
    try:
        layer = new_visible_layer(image)
        return apply_mirror(image, layer, directions, mask, merge=merge, tag_colors=tag_colors)
    finally:
        image.undo_group_end()
