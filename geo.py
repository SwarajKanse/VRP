"""Road, geocoding, and tile helpers implemented with stdlib only."""

from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

from models import GeoPoint, Node

USER_AGENT = "mini-vrp-tkinter/1.0"
NOMINATIM_URL = "https://nominatim.openstreetmap.org"
OSRM_URL = "https://router.project-osrm.org"
TILE_URL = "https://tile.openstreetmap.org"

KNOWN_LOCATIONS = {
    "mumbai hub": GeoPoint(19.0760, 72.8777),
    "bandra boutique": GeoPoint(19.0596, 72.8295),
    "andheri medical": GeoPoint(19.1136, 72.8697),
    "powai electronics": GeoPoint(19.1176, 72.9060),
    "lower parel studio": GeoPoint(19.0038, 72.8295),
    "colaba documents": GeoPoint(18.9067, 72.8147),
}

GEOCODE_REPLACEMENTS = {
    " engg ": " engineering ",
    " engg. ": " engineering ",
    " st ": " saint ",
}


class RoadService:
    """Cache-backed stdlib client for geocoding, routing, and tiles."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.route_dir = self.cache_dir / "routes"
        self.route_dir.mkdir(parents=True, exist_ok=True)
        self.tile_dir = self.cache_dir / "tiles"
        self.tile_dir.mkdir(parents=True, exist_ok=True)
        self.geocode_path = self.cache_dir / "geocode.json"
        self.reverse_path = self.cache_dir / "reverse_geocode.json"
        self.geocode_cache = self._load_json(self.geocode_path)
        self.reverse_cache = self._load_json(self.reverse_path)
        self.route_cache: dict[str, list[GeoPoint]] = {}
        self._request_clock = {"nominatim": 0.0}

    def geocode(self, query: str, locality_hint: str | None = None) -> tuple[str, GeoPoint]:
        normalized = query.strip().lower()
        cache_key = self._geocode_cache_key(normalized, locality_hint)
        if not normalized:
            raise ValueError("Address is empty")
        if cache_key in self.geocode_cache:
            cached = self.geocode_cache[cache_key]
            return cached["label"], GeoPoint(cached["latitude"], cached["longitude"])
        if locality_hint is None and normalized in self.geocode_cache:
            cached = self.geocode_cache[normalized]
            return cached["label"], GeoPoint(cached["latitude"], cached["longitude"])
        if normalized in KNOWN_LOCATIONS:
            point = KNOWN_LOCATIONS[normalized]
            self._store_geocode(cache_key, query.strip(), point)
            return query.strip(), point

        for variant in self._geocode_variants(query, locality_hint):
            payload = self._search_nominatim(variant)
            if not payload:
                continue
            best = self._best_search_match(variant, payload)
            label = best.get("display_name", query.strip())
            point = GeoPoint(float(best["lat"]), float(best["lon"]))
            self._store_geocode(cache_key, label, point)
            if locality_hint is None:
                self._store_geocode(normalized, label, point)
            return label, point
        raise ValueError(f"Could not geocode '{query}'")

    def reverse_geocode(self, point: GeoPoint) -> str:
        key = self._point_key(point)
        if key in self.reverse_cache:
            return self.reverse_cache[key]
        self._respect_rate_limit("nominatim", 1.05)
        url = (
            f"{NOMINATIM_URL}/reverse?"
            + urllib.parse.urlencode(
                {
                    "lat": point.latitude,
                    "lon": point.longitude,
                    "format": "jsonv2",
                }
            )
        )
        payload = self._get_json(url)
        label = payload.get("display_name") if isinstance(payload, dict) else None
        if not label:
            label = f"{point.latitude:.5f}, {point.longitude:.5f}"
        self.reverse_cache[key] = label
        self._save_json(self.reverse_path, self.reverse_cache)
        return label

    def route_segment(self, left: GeoPoint, right: GeoPoint) -> list[GeoPoint]:
        segment_key = self._segment_key(left, right)
        if segment_key in self.route_cache:
            return self.route_cache[segment_key]
        route_path = self.route_dir / f"{segment_key}.json"
        if route_path.exists():
            points = self._load_route(route_path)
            self.route_cache[segment_key] = points
            return points

        coordinates = f"{left.longitude},{left.latitude};{right.longitude},{right.latitude}"
        url = (
            f"{OSRM_URL}/route/v1/driving/{coordinates}?"
            + urllib.parse.urlencode(
                {
                    "overview": "full",
                    "geometries": "geojson",
                    "steps": "false",
                }
            )
        )
        try:
            payload = self._get_json(url)
            routes = payload.get("routes") if isinstance(payload, dict) else None
            if routes:
                coords = routes[0].get("geometry", {}).get("coordinates", [])
                if coords:
                    points = [GeoPoint(latitude=lat, longitude=lon) for lon, lat in coords]
                    route_path.write_text(
                        json.dumps([{"lat": point.latitude, "lon": point.longitude} for point in points]),
                        encoding="utf-8",
                    )
                    self.route_cache[segment_key] = points
                    return points
        except Exception:
            pass

        points = self._demo_segment(left, right)
        route_path.write_text(
            json.dumps([{"lat": point.latitude, "lon": point.longitude} for point in points]),
            encoding="utf-8",
        )
        self.route_cache[segment_key] = points
        return points

    def compose_route(self, node_sequence: list[Node]) -> list[GeoPoint]:
        if len(node_sequence) < 2:
            return [node_sequence[0].point] if node_sequence else []
        geometry: list[GeoPoint] = []
        for left, right in zip(node_sequence, node_sequence[1:]):
            segment = self.route_segment(left.point, right.point)
            if geometry:
                geometry.extend(segment[1:])
            else:
                geometry.extend(segment)
        return geometry

    def prefetch_pairs(self, nodes: list[Node]) -> None:
        for left_index in range(len(nodes)):
            for right_index in range(left_index + 1, len(nodes)):
                self.route_segment(nodes[left_index].point, nodes[right_index].point)
                self.route_segment(nodes[right_index].point, nodes[left_index].point)

    def fetch_tile(self, zoom: int, tile_x: int, tile_y: int) -> Path | None:
        if tile_y < 0 or tile_x < 0:
            return None
        tile_path = self.tile_dir / str(zoom) / str(tile_x) / f"{tile_y}.png"
        tile_path.parent.mkdir(parents=True, exist_ok=True)
        if tile_path.exists():
            return tile_path
        url = f"{TILE_URL}/{zoom}/{tile_x}/{tile_y}.png"
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=6) as response:
                data = response.read()
            tile_path.write_bytes(data)
            return tile_path
        except Exception:
            return None

    def best_zoom(self, points: list[GeoPoint], width: int, height: int) -> int:
        if not points:
            return 12
        margin = 80
        for zoom in range(16, 2, -1):
            xs, ys = zip(*(self.latlon_to_world(point, zoom) for point in points))
            if max(xs) - min(xs) <= max(width - margin, 200) and max(ys) - min(ys) <= max(height - margin, 200):
                return zoom
        return 3

    def latlon_to_world(self, point: GeoPoint, zoom: int) -> tuple[float, float]:
        scale = 256 * (2**zoom)
        latitude = max(min(point.latitude, 85.0511), -85.0511)
        sin_y = math.sin(math.radians(latitude))
        world_x = (point.longitude + 180.0) / 360.0 * scale
        world_y = (
            0.5 - math.log((1.0 + sin_y) / (1.0 - sin_y)) / (4.0 * math.pi)
        ) * scale
        return world_x, world_y

    def world_to_latlon(self, world_x: float, world_y: float, zoom: int) -> GeoPoint:
        scale = 256 * (2**zoom)
        longitude = world_x / scale * 360.0 - 180.0
        mercator_y = math.pi - (2.0 * math.pi * world_y / scale)
        latitude = math.degrees(math.atan(math.sinh(mercator_y)))
        return GeoPoint(latitude, longitude)

    def haversine_km(self, left: GeoPoint, right: GeoPoint) -> float:
        radius_km = 6371.0
        lat1 = math.radians(left.latitude)
        lat2 = math.radians(right.latitude)
        dlat = lat2 - lat1
        dlon = math.radians(right.longitude - left.longitude)
        a = (
            math.sin(dlat / 2.0) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
        )
        return radius_km * (2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)))

    def _store_geocode(self, key: str, label: str, point: GeoPoint) -> None:
        self.geocode_cache[key] = {
            "label": label,
            "latitude": point.latitude,
            "longitude": point.longitude,
        }
        self._save_json(self.geocode_path, self.geocode_cache)

    def _search_nominatim(self, search_query: str):
        self._respect_rate_limit("nominatim", 1.05)
        url = (
            f"{NOMINATIM_URL}/search?"
            + urllib.parse.urlencode(
                {
                    "q": search_query,
                    "format": "jsonv2",
                    "limit": 5,
                    "addressdetails": 1,
                }
            )
        )
        payload = self._get_json(url)
        return payload if isinstance(payload, list) else []

    def _geocode_variants(self, query: str, locality_hint: str | None) -> list[str]:
        base = " ".join(query.strip().split())
        normalized = self._normalize_query(base)
        hint = ", ".join(part.strip() for part in (locality_hint or "").split(",") if part.strip())
        queries: list[str] = []

        def add(candidate: str) -> None:
            candidate = " ".join(candidate.replace(" ,", ",").split())
            if candidate and candidate not in queries:
                queries.append(candidate)

        add(base)
        add(normalized)

        if hint and hint.lower() not in base.lower():
            add(f"{base}, {hint}")
            add(f"{normalized}, {hint}")

        acronym = self._acronym(normalized)
        if acronym:
            if hint:
                add(f"{acronym}, {hint}")
                add(f"{acronym} College, {hint}")
            add(acronym)
            add(f"{acronym} College")

        return queries

    def _normalize_query(self, query: str) -> str:
        normalized = f" {query.strip().lower()} "
        for source, target in GEOCODE_REPLACEMENTS.items():
            normalized = normalized.replace(source, target)
        return " ".join(normalized.split()).title()

    def _acronym(self, query: str) -> str:
        words = [word for word in query.replace(",", " ").split() if word and word[0].isalnum()]
        if len(words) < 3:
            return ""
        initials = "".join(word[0] for word in words if word[0].isalnum())
        return initials.upper() if len(initials) >= 3 else ""

    def _best_search_match(self, query: str, candidates: list[dict]) -> dict:
        query_tokens = set(self._normalize_query(query).lower().split())

        def score(item: dict) -> tuple[float, float]:
            text = " ".join(
                [
                    str(item.get("display_name", "")),
                    str(item.get("name", "")),
                    str(item.get("type", "")),
                ]
            ).lower()
            text_tokens = set(text.replace(",", " ").split())
            overlap = len(query_tokens & text_tokens)
            importance = float(item.get("importance", 0.0) or 0.0)
            return (float(overlap), importance)

        return max(candidates, key=score)

    def _demo_segment(self, left: GeoPoint, right: GeoPoint) -> list[GeoPoint]:
        # Curved fallback path so offline demos still read as a route rather than a straight chord.
        points = [left]
        mid_lat = (left.latitude + right.latitude) / 2.0
        mid_lon = (left.longitude + right.longitude) / 2.0
        lat_offset = (right.longitude - left.longitude) * 0.04
        lon_offset = (left.latitude - right.latitude) * 0.04
        points.append(GeoPoint(mid_lat + lat_offset, mid_lon + lon_offset))
        points.append(right)
        return points

    def _respect_rate_limit(self, key: str, interval: float) -> None:
        last_time = self._request_clock.get(key, 0.0)
        wait = interval - (time.time() - last_time)
        if wait > 0:
            time.sleep(wait)
        self._request_clock[key] = time.time()

    def _get_json(self, url: str):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))

    def _load_route(self, route_path: Path) -> list[GeoPoint]:
        payload = json.loads(route_path.read_text(encoding="utf-8"))
        return [GeoPoint(item["lat"], item["lon"]) for item in payload]

    def _segment_key(self, left: GeoPoint, right: GeoPoint) -> str:
        return f"{self._point_key(left)}__{self._point_key(right)}"

    def _point_key(self, point: GeoPoint) -> str:
        return f"{point.latitude:.5f}_{point.longitude:.5f}"

    def _geocode_cache_key(self, normalized_query: str, locality_hint: str | None) -> str:
        if not locality_hint:
            return normalized_query
        hint = "|".join(part.strip().lower() for part in locality_hint.split(",") if part.strip())
        return f"{normalized_query}||{hint}"

    def _load_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_json(self, path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
