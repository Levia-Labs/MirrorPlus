"""GTK dialog for the Mirror+ GIMP plug-in: wind-rose arrow picker and live preview."""
import math

import gi

gi.require_version("Gimp", "3.0")
gi.require_version("GimpUi", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gimp, GimpUi, GLib, GObject, Gtk  # noqa: E402

import cairo  # noqa: E402
import mirror_plus_geometry as geo  # noqa: E402

ROSE_SIZE = 240
PREVIEW_SIZE = 380
THUMB_MAX = 512
TINT_ALPHA = 0.55
BACKDROP_ALPHA = 0.35


def _pixbuf_from_data(width, height, bpp, data):
    raw = data if isinstance(data, GLib.Bytes) else GLib.Bytes.new(bytes(data))
    return GdkPixbuf.Pixbuf.new_from_bytes(
        raw, GdkPixbuf.Colorspace.RGB, bpp == 4, 8, width, height, width * bpp)


def _thumb_size(width, height, max_side):
    scale = min(1.0, max_side / max(width, height))
    return max(1, int(width * scale)), max(1, int(height * scale))


def drawable_pixbuf(drawable, max_side=THUMB_MAX):
    """Thumbnail of a drawable as a GdkPixbuf, trying both libgimp entry points."""
    tw, th = _thumb_size(drawable.get_width(), drawable.get_height(), max_side)
    try:
        return drawable.get_thumbnail(tw, th, Gimp.PixbufTransparency.KEEP_ALPHA)
    except (AttributeError, TypeError):
        _ok, aw, ah, bpp, data = drawable.get_thumbnail_data(tw, th)
        return _pixbuf_from_data(aw, ah, bpp, data)


def image_pixbuf(image, max_side=THUMB_MAX):
    tw, th = _thumb_size(image.get_width(), image.get_height(), max_side)
    try:
        return image.get_thumbnail(tw, th, Gimp.PixbufTransparency.KEEP_ALPHA)
    except (AttributeError, TypeError):
        _ok, aw, ah, bpp, data = image.get_thumbnail_data(tw, th)
        return _pixbuf_from_data(aw, ah, bpp, data)


class RoseWidget(Gtk.DrawingArea):
    """Clickable wind rose: one arrow per direction, click toggles it."""

    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self, count, mask, tint):
        super().__init__()
        self.count, self.mask, self.tint = count, mask, tint
        self.set_size_request(ROSE_SIZE, ROSE_SIZE)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("draw", self._on_draw)
        self.connect("button-press-event", self._on_click)

    def update(self, count=None, mask=None, tint=None):
        if count is not None:
            self.count = count
        if mask is not None:
            self.mask = mask
        if tint is not None:
            self.tint = tint
        self.queue_draw()

    def _on_click(self, _widget, event):
        alloc = self.get_allocation()
        cx, cy = alloc.width / 2, alloc.height / 2
        if math.hypot(event.x - cx, event.y - cy) < 8:
            return True
        index = geo.index_at_point(event.x - cx, event.y - cy, self.count)
        self.mask = geo.toggle_bit(self.mask, index)
        self.queue_draw()
        self.emit("changed")
        return True

    def _on_draw(self, _widget, cr):
        alloc = self.get_allocation()
        cx, cy = alloc.width / 2, alloc.height / 2
        radius = min(cx, cy) - 22
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.25)
        cr.set_line_width(1)
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.stroke()
        for index in range(self.count):
            self._draw_arrow(cr, cx, cy, radius, index)
        return True

    def _draw_arrow(self, cr, cx, cy, radius, index):
        selected = geo.is_selected(self.mask, index)
        angle = math.radians(geo.angle_degrees(index, self.count))
        dx, dy = math.sin(angle), -math.cos(angle)
        if selected:
            color = geo.tint_rgb(index, self.count) if self.tint else (0.2, 0.55, 0.95)
            cr.set_source_rgba(*color, 1.0)
            cr.set_line_width(4)
        else:
            cr.set_source_rgba(0.55, 0.55, 0.55, 0.6)
            cr.set_line_width(2)
        cr.move_to(cx, cy)
        tip_x, tip_y = cx + dx * radius, cy + dy * radius
        cr.line_to(tip_x, tip_y)
        cr.stroke()
        head = 10 if selected else 7
        for side in (-1, 1):
            back = angle + math.pi + side * 0.4
            cr.move_to(tip_x, tip_y)
            cr.line_to(tip_x + math.sin(back) * head, tip_y - math.cos(back) * head)
        cr.stroke()
        label = f"{geo.angle_degrees(index, self.count):g}"
        cr.set_font_size(9)
        ext = cr.text_extents(label)
        cr.move_to(cx + dx * (radius + 13) - ext.width / 2,
                   cy + dy * (radius + 13) + ext.height / 2)
        cr.show_text(label)


class PreviewWidget(Gtk.DrawingArea):
    """Composites rotated thumbnails over a dimmed image thumbnail."""

    def __init__(self, image, layer):
        super().__init__()
        self.set_size_request(PREVIEW_SIZE, PREVIEW_SIZE)
        self.count, self.mask, self.tint = 8, 0, False
        self.layer_pixbuf = drawable_pixbuf(layer)
        try:
            self.image_pixbuf = image_pixbuf(image)
        except Exception:  # noqa: BLE001 - the backdrop is optional
            self.image_pixbuf = None
        self.image_w, self.image_h = image.get_width(), image.get_height()
        _ok, ox, oy = layer.get_offsets()
        self.layer_w, self.layer_h = layer.get_width(), layer.get_height()
        self.center = (ox + self.layer_w / 2, oy + self.layer_h / 2)
        self.connect("draw", self._on_draw)

    def update(self, count, mask, tint):
        self.count, self.mask, self.tint = count, mask, tint
        self.queue_draw()

    def _bounds(self):
        half = geo.rotated_bounds(self.layer_w, self.layer_h) / 2
        cx, cy = self.center
        x0, y0 = min(0, cx - half), min(0, cy - half)
        x1, y1 = max(self.image_w, cx + half), max(self.image_h, cy + half)
        return x0, y0, x1 - x0, y1 - y0

    def _on_draw(self, _widget, cr):
        alloc = self.get_allocation()
        bx, by, bw, bh = self._bounds()
        scale = min(alloc.width / bw, alloc.height / bh)
        cr.translate((alloc.width - bw * scale) / 2, (alloc.height - bh * scale) / 2)
        cr.scale(scale, scale)
        cr.translate(-bx, -by)
        self._draw_backdrop(cr)
        for index in geo.selected_indices(self.mask, self.count):
            self._draw_copy(cr, index)
        return True

    def _draw_backdrop(self, cr):
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.2)
        cr.rectangle(0, 0, self.image_w, self.image_h)
        cr.fill()
        if self.image_pixbuf is None:
            return
        cr.save()
        cr.scale(self.image_w / self.image_pixbuf.get_width(),
                 self.image_h / self.image_pixbuf.get_height())
        Gdk.cairo_set_source_pixbuf(cr, self.image_pixbuf, 0, 0)
        cr.paint_with_alpha(BACKDROP_ALPHA)
        cr.restore()

    def _draw_copy(self, cr, index):
        cr.save()
        cr.translate(*self.center)
        cr.rotate(math.radians(geo.angle_degrees(index, self.count)))
        cr.translate(-self.layer_w / 2, -self.layer_h / 2)
        cr.scale(self.layer_w / self.layer_pixbuf.get_width(),
                 self.layer_h / self.layer_pixbuf.get_height())
        if self.tint:
            cr.push_group()
        Gdk.cairo_set_source_pixbuf(cr, self.layer_pixbuf, 0, 0)
        cr.paint()
        if self.tint:
            # ATOP keeps the copy's alpha and lays a translucent color over it.
            cr.set_operator(cairo.OPERATOR_ATOP)
            cr.set_source_rgba(*geo.tint_rgb(index, self.count), TINT_ALPHA)
            cr.paint()
            cr.pop_group_to_source()
            cr.set_operator(cairo.OPERATOR_OVER)
            cr.paint()
        cr.restore()


class MirrorPlusDialog:
    """Modal dialog; `run()` returns a settings dict or None when cancelled."""

    PRESETS = (("+", "plus"), ("x", "cross"), ("Full", "full"), ("None", "none"))

    def __init__(self, image, layer, directions, mask, merge, tint):
        use_header_bar = Gtk.Settings.get_default().get_property("gtk-dialogs-use-header")
        self.dialog = GimpUi.Dialog(use_header_bar=use_header_bar, title="Mirror+")
        self.dialog.add_button("_Cancel", Gtk.ResponseType.CANCEL)
        self.dialog.add_button("_Apply", Gtk.ResponseType.OK)
        self.rose = RoseWidget(directions, mask, tint)
        self.preview = PreviewWidget(image, layer)
        self.spin = Gtk.SpinButton.new_with_range(geo.MIN_DIRECTIONS, geo.MAX_DIRECTIONS, 1)
        self.spin.set_value(directions)
        self.merge_check = Gtk.CheckButton.new_with_label("Merge copies into one layer")
        self.merge_check.set_active(merge)
        self.tint_check = Gtk.CheckButton.new_with_label(
            "Tint copies (preview; color tags when unmerged)")
        self.tint_check.set_active(tint)
        self._build(self.dialog.get_content_area())
        self.rose.connect("changed", lambda *_: self._refresh())
        self.spin.connect("value-changed", self._on_count)
        self.tint_check.connect("toggled", lambda *_: self._refresh())
        self._refresh()

    def _build(self, content):
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, border_width=12)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left.pack_start(self.rose, False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.pack_start(Gtk.Label(label="Directions"), False, False, 0)
        row.pack_start(self.spin, True, True, 0)
        left.pack_start(row, False, False, 0)
        presets = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for label, kind in self.PRESETS:
            button = Gtk.Button(label=label)
            button.connect("clicked", self._on_preset, kind)
            presets.pack_start(button, True, True, 0)
        left.pack_start(presets, False, False, 0)
        left.pack_start(self.merge_check, False, False, 0)
        left.pack_start(self.tint_check, False, False, 0)
        hbox.pack_start(left, False, False, 0)
        frame = Gtk.Frame(label="Preview")
        frame.add(self.preview)
        hbox.pack_start(frame, True, True, 0)
        content.add(hbox)

    def _on_count(self, spin):
        count = geo.clamp_directions(spin.get_value_as_int())
        self.rose.update(count=count, mask=geo.full_mask(count))
        self._refresh()

    def _on_preset(self, _button, kind):
        self.rose.update(mask=geo.preset_mask(self.rose.count, kind))
        self._refresh()

    def _refresh(self):
        tint = self.tint_check.get_active()
        self.rose.update(tint=tint)
        self.preview.update(self.rose.count, self.rose.mask, tint)

    def run(self):
        self.dialog.show_all()
        response = self.dialog.run()
        settings = None
        if response == Gtk.ResponseType.OK:
            settings = {
                "directions": self.rose.count,
                "mask": self.rose.mask,
                "merge": self.merge_check.get_active(),
                "tint": self.tint_check.get_active(),
            }
        self.dialog.destroy()
        return settings
