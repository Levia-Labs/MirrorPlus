"""GTK dialog for the Mirror+ GIMP plug-in: wind-rose arrow picker and live preview."""
import math

import gi

gi.require_version("Gimp", "3.0")
gi.require_version("GimpUi", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GimpUi, GObject, Gtk  # noqa: E402

import mirror_plus_geometry as geo  # noqa: E402
from mirror_plus_preview import PreviewWidget  # noqa: E402

ROSE_SIZE = 240



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



class MirrorPlusDialog:
    """Modal dialog; `run()` returns a settings dict or None when cancelled."""

    PRESETS = (("+", "plus"), ("x", "cross"), ("Full", "full"), ("None", "none"))

    def __init__(self, image, layer, directions, mask, merge, tint, visible=False):
        use_header_bar = Gtk.Settings.get_default().get_property("gtk-dialogs-use-header")
        self.dialog = GimpUi.Dialog(use_header_bar=use_header_bar, title="Mirror+")
        self.dialog.add_button("_Cancel", Gtk.ResponseType.CANCEL)
        self.dialog.add_button("_Apply", Gtk.ResponseType.OK)
        self.rose = RoseWidget(directions, mask, tint)
        self.preview = PreviewWidget(image, layer, visible)
        self.spin = Gtk.SpinButton.new_with_range(geo.MIN_DIRECTIONS, geo.MAX_DIRECTIONS, 1)
        self.spin.set_value(directions)
        self.merge_check = Gtk.CheckButton.new_with_label("Merge copies into one layer")
        self.merge_check.set_active(merge)
        self.tint_check = Gtk.CheckButton.new_with_label(
            "Tint copies (preview; color tags when unmerged)")
        self.tint_check.set_active(tint)
        self.layer_radio = Gtk.RadioButton.new_with_label(None, "Selected layer")
        self.visible_radio = Gtk.RadioButton.new_with_label_from_widget(
            self.layer_radio, "Visible")
        self.visible_radio.set_active(visible)
        self.refresh_button = Gtk.Button.new_with_mnemonic("_Refresh preview")
        self._build(self.dialog.get_content_area())
        self.visible_radio.connect(
            "toggled", lambda *_: self.preview.set_source(self.visible_radio.get_active()))
        self.refresh_button.connect("clicked", lambda *_: self.preview.reload())
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
        source = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        source.pack_start(Gtk.Label(label="Source"), False, False, 0)
        source.pack_start(self.layer_radio, False, False, 0)
        source.pack_start(self.visible_radio, False, False, 0)
        left.pack_start(source, False, False, 0)
        left.pack_start(self.merge_check, False, False, 0)
        left.pack_start(self.tint_check, False, False, 0)
        left.pack_end(self.refresh_button, False, False, 0)
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
                "visible": self.visible_radio.get_active(),
            }
        self.dialog.destroy()
        return settings
