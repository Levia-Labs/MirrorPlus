"""Preview widget for the Mirror+ dialog: GIMP thumbnails fanned out with cairo."""
import math

import gi

gi.require_version("Gimp", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gimp, GLib, Gtk  # noqa: E402

import cairo  # noqa: E402
import mirror_plus_geometry as geo  # noqa: E402

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


class PreviewWidget(Gtk.DrawingArea):
    """Composites rotated thumbnails over a dimmed image thumbnail."""

    def __init__(self, image, layer, visible=False):
        super().__init__()
        self.set_size_request(PREVIEW_SIZE, PREVIEW_SIZE)
        self.count, self.mask, self.tint = 8, 0, False
        self.image, self.layer, self.visible = image, layer, visible
        self.connect("draw", self._on_draw)
        self.reload()

    def reload(self):
        """Re-read the thumbnails from GIMP; the user may have painted since the last read."""
        image = self.image
        # Locals first: a failing thumbnail call must not leave the widget half updated.
        try:
            backdrop = image_pixbuf(image)
        except Exception:  # noqa: BLE001 - the backdrop is optional
            backdrop = None
        image_w, image_h = image.get_width(), image.get_height()
        if self.visible:
            # The composite is the image itself, so the backdrop thumbnail doubles as source;
            # None draws nothing for the copies when the thumbnail is unavailable.
            pixbuf = backdrop
            layer_w, layer_h = image_w, image_h
            center = (image_w / 2, image_h / 2)
        else:
            layer = self.layer
            pixbuf = drawable_pixbuf(layer)
            _ok, ox, oy = layer.get_offsets()
            layer_w, layer_h = layer.get_width(), layer.get_height()
            center = (ox + layer_w / 2, oy + layer_h / 2)
        self.image_pixbuf, self.image_w, self.image_h = backdrop, image_w, image_h
        self.layer_pixbuf, self.layer_w, self.layer_h = pixbuf, layer_w, layer_h
        self.center = center
        self.queue_draw()

    def set_source(self, visible):
        self.visible = visible
        self.reload()

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
        if self.layer_pixbuf is not None:
            cr.scale(self.layer_w / self.layer_pixbuf.get_width(),
                     self.layer_h / self.layer_pixbuf.get_height())
        if self.tint:
            cr.push_group()
        if self.layer_pixbuf is not None:
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
