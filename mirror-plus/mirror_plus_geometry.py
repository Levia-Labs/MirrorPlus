"""Pure geometry and selection helpers for the Mirror+ GIMP plug-in.

No GIMP or GTK imports here so the module stays unit-testable with a plain
Python interpreter.
"""
import colorsys
import math

MIN_DIRECTIONS = 2
MAX_DIRECTIONS = 30  # bitmask must fit a signed 32-bit PDB int argument

# Layer color tags cycle through these GIMP color tag names; the UI module maps
# them onto Gimp.ColorTag members.
TAG_CYCLE = ("RED", "ORANGE", "YELLOW", "GREEN", "BLUE", "VIOLET", "BROWN", "GRAY")


def clamp_directions(count):
    """Clamp a direction count into the supported range."""
    return max(MIN_DIRECTIONS, min(MAX_DIRECTIONS, int(count)))


def step_degrees(count):
    """Angle between neighbouring arrows."""
    return 360.0 / clamp_directions(count)


def angle_degrees(index, count):
    """Clockwise angle from north for arrow `index`."""
    return (index * step_degrees(count)) % 360.0


def full_mask(count):
    """Bitmask with every arrow selected."""
    return (1 << clamp_directions(count)) - 1


def preset_mask(count, kind):
    """Return the bitmask for a preset.

    "plus"  selects every second arrow starting at north (N/E/S/W for 8).
    "cross" selects the arrows in between (NE/SE/SW/NW for 8).
    "full"  selects all arrows, "none" clears the selection.
    """
    count = clamp_directions(count)
    if kind == "full":
        return full_mask(count)
    if kind == "none":
        return 0
    if kind == "plus":
        return sum(1 << i for i in range(0, count, 2))
    if kind == "cross":
        return sum(1 << i for i in range(1, count, 2))
    raise ValueError(f"unknown preset {kind!r}")


def toggle_bit(mask, index):
    """Flip one arrow in the mask."""
    return mask ^ (1 << index)


def is_selected(mask, index):
    return bool(mask & (1 << index))


def selected_indices(mask, count):
    """Ordered list of selected arrow indices within `count`."""
    count = clamp_directions(count)
    return [i for i in range(count) if is_selected(mask, i)]


def selected_angles(mask, count):
    """Clockwise angles in degrees for every selected arrow."""
    return [angle_degrees(i, count) for i in selected_indices(mask, count)]


def index_at_point(dx, dy, count):
    """Arrow index nearest to a vector from the rose center (screen coords, y down)."""
    count = clamp_directions(count)
    angle = math.degrees(math.atan2(dx, -dy)) % 360.0
    return int(round(angle / step_degrees(count))) % count


def tint_rgb(index, count):
    """Distinct, evenly spread RGB tint (0..1 floats) for arrow `index`."""
    hue = (index / clamp_directions(count)) % 1.0
    return colorsys.hls_to_rgb(hue, 0.5, 1.0)


def tag_name(index):
    """GIMP color tag name for arrow `index`, cycling through TAG_CYCLE."""
    return TAG_CYCLE[index % len(TAG_CYCLE)]


def rotated_bounds(width, height):
    """Square box side that contains the layer rotated to any angle."""
    return math.hypot(width, height)


def layer_name(base, degrees):
    """Name for one rotated copy."""
    return f"{base} {degrees:g}°"
