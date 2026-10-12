from __future__ import annotations

import math
from typing import Any

import httpx


ASOS_STATIONS: list[dict[str, Any]] = [
    {"station_no": "105", "station_name": "강릉", "lat": 37.7515, "lon": 128.8910},
    {"station_no": "108", "station_name": "서울", "lat": 37.5714, "lon": 126.9658},
    {"station_no": "112", "station_name": "인천", "lat": 37.4777, "lon": 126.6249},
    {"station_no": "119", "station_name": "수원", "lat": 37.2723, "lon": 126.9853},
    {"station_no": "131", "station_name": "청주", "lat": 36.6392, "lon": 127.4407},
    {"station_no": "133", "station_name": "대전", "lat": 36.3719, "lon": 127.3721},
    {"station_no": "143", "station_name": "대구", "lat": 35.8779, "lon": 128.6529},
    {"station_no": "146", "station_name": "전주", "lat": 35.8409, "lon": 127.1172},
    {"station_no": "152", "station_name": "울산", "lat": 35.5824, "lon": 129.3347},
    {"station_no": "156", "station_name": "광주", "lat": 35.1729, "lon": 126.8916},
    {"station_no": "159", "station_name": "부산", "lat": 35.1047, "lon": 129.0320},
    {"station_no": "165", "station_name": "목포", "lat": 34.8173, "lon": 126.3815},
    {"station_no": "168", "station_name": "여수", "lat": 34.7393, "lon": 127.7406},
    {"station_no": "184", "station_name": "제주", "lat": 33.5141, "lon": 126.5297},
]


class LocationService:
    KAKAO_ADDRESS_URL = "https://dapi.kakao.com/v2/local/search/address.json"

    def __init__(self, kakao_rest_api_key: str | None) -> None:
        self.kakao_rest_api_key = kakao_rest_api_key

    async def search_address(self, query: str) -> list[dict[str, Any]]:
        normalized = query.strip()
        if not normalized:
            return []
        if not self.kakao_rest_api_key:
            raise RuntimeError("KAKAO_REST_API_KEY is not configured")

        headers = {"Authorization": f"KakaoAK {self.kakao_rest_api_key}"}
        params = {"query": normalized, "size": "5"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(self.KAKAO_ADDRESS_URL, headers=headers, params=params)
            resp.raise_for_status()
            payload = resp.json()

        results: list[dict[str, Any]] = []
        for item in payload.get("documents", []):
            lon = float(item["x"])
            lat = float(item["y"])
            nx, ny = self.to_grid(lat, lon)
            station = self.nearest_asos_station(lat, lon)
            address = item.get("road_address") or item.get("address") or {}
            display_address = (
                address.get("address_name")
                or item.get("address_name")
                or normalized
            )
            results.append(
                {
                    "label": display_address,
                    "address": display_address,
                    "lat": lat,
                    "lon": lon,
                    "nx": str(nx),
                    "ny": str(ny),
                    "kma_asos_station_no": station["station_no"],
                    "kma_asos_station_name": station["station_name"],
                }
            )
        return results

    @staticmethod
    def to_grid(lat: float, lon: float) -> tuple[int, int]:
        re = 6371.00877
        grid = 5.0
        slat1 = 30.0
        slat2 = 60.0
        olon = 126.0
        olat = 38.0
        xo = 43
        yo = 136

        degrad = math.pi / 180.0
        re_grid = re / grid
        slat1_rad = slat1 * degrad
        slat2_rad = slat2 * degrad
        olon_rad = olon * degrad
        olat_rad = olat * degrad

        sn = math.tan(math.pi * 0.25 + slat2_rad * 0.5) / math.tan(
            math.pi * 0.25 + slat1_rad * 0.5
        )
        sn = math.log(math.cos(slat1_rad) / math.cos(slat2_rad)) / math.log(sn)
        sf = math.tan(math.pi * 0.25 + slat1_rad * 0.5)
        sf = (sf**sn) * math.cos(slat1_rad) / sn
        ro = math.tan(math.pi * 0.25 + olat_rad * 0.5)
        ro = re_grid * sf / (ro**sn)

        ra = math.tan(math.pi * 0.25 + lat * degrad * 0.5)
        ra = re_grid * sf / (ra**sn)
        theta = lon * degrad - olon_rad
        if theta > math.pi:
            theta -= 2.0 * math.pi
        if theta < -math.pi:
            theta += 2.0 * math.pi
        theta *= sn

        nx = math.floor(ra * math.sin(theta) + xo + 0.5)
        ny = math.floor(ro - ra * math.cos(theta) + yo + 0.5)
        return nx, ny

    @staticmethod
    def nearest_asos_station(lat: float, lon: float) -> dict[str, Any]:
        return min(
            ASOS_STATIONS,
            key=lambda station: (station["lat"] - lat) ** 2 + (station["lon"] - lon) ** 2,
        )
