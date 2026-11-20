"""Unit tests for mirror_plus_geometry. Run with any Python 3.12 interpreter."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mirror-plus"))
import mirror_plus_geometry as geo  # noqa: E402


class GeometryTests(unittest.TestCase):
    def test_presets_for_eight(self):
        self.assertEqual(geo.selected_angles(geo.preset_mask(8, "plus"), 8), [0, 90, 180, 270])
        self.assertEqual(geo.selected_angles(geo.preset_mask(8, "cross"), 8), [45, 135, 225, 315])
        self.assertEqual(geo.preset_mask(8, "full"), 255)
        self.assertEqual(geo.preset_mask(8, "none"), 0)

    def test_presets_for_odd_counts(self):
        for count in (3, 5, 7):
            plus, cross = geo.preset_mask(count, "plus"), geo.preset_mask(count, "cross")
            self.assertEqual(plus & cross, 0)
            self.assertEqual(plus | cross, geo.full_mask(count))

    def test_angles_evenly_spaced(self):
        for count in range(geo.MIN_DIRECTIONS, geo.MAX_DIRECTIONS + 1):
            angles = geo.selected_angles(geo.full_mask(count), count)
            self.assertEqual(len(angles), count)
            self.assertAlmostEqual(angles[1] - angles[0], 360 / count)

    def test_click_maps_to_nearest_arrow(self):
        self.assertEqual(geo.index_at_point(0, -50, 8), 0)   # north
        self.assertEqual(geo.index_at_point(50, 0, 8), 2)    # east
        self.assertEqual(geo.index_at_point(0, 50, 8), 4)    # south
        self.assertEqual(geo.index_at_point(-50, 0, 8), 6)   # west
        self.assertEqual(geo.index_at_point(-1, -50, 8), 0)  # just left of north wraps
        self.assertEqual(geo.index_at_point(30, -50, 3), 0)
        self.assertEqual(geo.index_at_point(50, 20, 3), 1)

    def test_toggle_and_clamp(self):
        self.assertEqual(geo.toggle_bit(0, 3), 8)
        self.assertEqual(geo.toggle_bit(8, 3), 0)
        self.assertEqual(geo.clamp_directions(1), geo.MIN_DIRECTIONS)
        self.assertEqual(geo.clamp_directions(99), geo.MAX_DIRECTIONS)

    def test_tints_distinct(self):
        tints = {geo.tint_rgb(i, 8) for i in range(8)}
        self.assertEqual(len(tints), 8)
        self.assertEqual(geo.tag_name(9), geo.TAG_CYCLE[1])

    def test_layer_name(self):
        self.assertEqual(geo.layer_name("Hair", 45.0), "Hair 45°")
        self.assertEqual(geo.layer_name("Hair", 102.85714285714286), "Hair 102.857°")


if __name__ == "__main__":
    unittest.main()
