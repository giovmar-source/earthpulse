
import unittest

from api.main import make_bbox


class TestAreaBoundingBox(unittest.TestCase):

    def test_bbox_has_four_coordinates(self):
        bbox = make_bbox(
            lat=40.81,
            lon=15.007,
            side_km=1.0,
        )

        self.assertEqual(len(bbox), 4)

    def test_bbox_contains_requested_center(self):
        lat = 40.81
        lon = 15.007

        min_lon, min_lat, max_lon, max_lat = make_bbox(
            lat=lat,
            lon=lon,
            side_km=1.0,
        )

        self.assertLess(min_lon, lon)
        self.assertGreater(max_lon, lon)
        self.assertLess(min_lat, lat)
        self.assertGreater(max_lat, lat)

    def test_bbox_is_smaller_for_smaller_area(self):
        small = make_bbox(40.81, 15.007, 1.0)
        large = make_bbox(40.81, 15.007, 5.0)

        small_width = small[2] - small[0]
        large_width = large[2] - large[0]

        self.assertLess(small_width, large_width)


if __name__ == "__main__":
    unittest.main(verbosity=2)