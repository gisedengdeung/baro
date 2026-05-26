from __future__ import annotations

import unittest

from cloud.services.location_service import LocationService


class LocationServiceTest(unittest.TestCase):
    def test_to_grid_converts_seoul_coordinates(self):
        nx, ny = LocationService.to_grid(37.5665, 126.9780)
        self.assertEqual((nx, ny), (60, 127))

    def test_nearest_asos_station_uses_coordinates(self):
        station = LocationService.nearest_asos_station(37.5665, 126.9780)
        self.assertEqual(station["station_no"], "108")
        self.assertEqual(station["station_name"], "서울")


if __name__ == "__main__":
    unittest.main()
