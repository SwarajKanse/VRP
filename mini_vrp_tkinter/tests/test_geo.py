from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from mini_vrp_tkinter.geo import RoadService
from mini_vrp_tkinter.models import GeoPoint


class RoadServiceTests(TestCase):
    def setUp(self) -> None:
        self.cache_dir = Path(__file__).resolve().parent / "_cache_geo"
        self.service = RoadService(self.cache_dir)

    def tearDown(self) -> None:
        if self.cache_dir.exists():
            for path in sorted(self.cache_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                else:
                    path.rmdir()

    def test_known_location_geocode_uses_builtin_lookup(self) -> None:
        label, point = self.service.geocode("Mumbai Hub")
        self.assertEqual(label, "Mumbai Hub")
        self.assertAlmostEqual(point.latitude, 19.0760, places=3)

    def test_demo_segment_has_multiple_points(self) -> None:
        segment = self.service.route_segment(GeoPoint(19.0, 72.8), GeoPoint(19.1, 72.9))
        self.assertGreaterEqual(len(segment), 3)

    def test_route_cache_keeps_direction_specific_geometry(self) -> None:
        left = GeoPoint(19.0, 72.8)
        right = GeoPoint(19.1, 72.9)

        def fake_get_json(url: str):
            if "72.8,19.0;72.9,19.1" in url:
                return {
                    "routes": [
                        {
                            "geometry": {
                                "coordinates": [[72.8, 19.0], [72.85, 19.05], [72.9, 19.1]],
                            }
                        }
                    ]
                }
            if "72.9,19.1;72.8,19.0" in url:
                return {
                    "routes": [
                        {
                            "geometry": {
                                "coordinates": [[72.9, 19.1], [72.84, 19.06], [72.8, 19.0]],
                            }
                        }
                    ]
                }
            raise AssertionError("Unexpected URL")

        with patch.object(self.service, "_get_json", side_effect=fake_get_json):
            forward = self.service.route_segment(left, right)
            reverse = self.service.route_segment(right, left)

        self.assertEqual(forward[0], left)
        self.assertEqual(forward[-1], right)
        self.assertEqual(reverse[0], right)
        self.assertEqual(reverse[-1], left)

    def test_geocode_uses_fallback_variants_for_named_places(self) -> None:
        def fake_search(query: str):
            if query == "Thadomal Shahani Engineering College":
                return []
            if query == "TSEC College, Mumbai, Maharashtra, India":
                return [
                    {
                        "display_name": "TSEC College, Bandra West, Mumbai, Maharashtra, India",
                        "lat": "19.0639480",
                        "lon": "72.8357925",
                        "importance": 0.4,
                        "name": "TSEC College",
                    }
                ]
            return []

        with patch.object(self.service, "_search_nominatim", side_effect=fake_search):
            label, point = self.service.geocode(
                "Thadomal Shahani Engineering College",
                locality_hint="Mumbai, Maharashtra, India",
            )

        self.assertIn("TSEC College", label)
        self.assertAlmostEqual(point.latitude, 19.0639480, places=4)
