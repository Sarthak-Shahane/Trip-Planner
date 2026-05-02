import trip_database
import urllib.parse


class GoogleAPIHelper:
    """Compatibility class: data comes only from SQLite and local /static/ files."""

    def __init__(self):
        trip_database.init_db()

    def search_images(self, query: str, num_results: int = 1) -> list:
        url = trip_database.public_static_url("placeholders/generic.svg")
        return [url] * max(1, num_results)

    def get_place_details(self, place_name: str, city: str = "") -> dict:
        row = trip_database.lookup_place(place_name, city)
        if not row:
            return self._fallback_place_data(place_name, city)
        return {
            "place_id": None,
            "name": place_name,
            "formatted_address": row.get("formatted_address", ""),
            "location": {"lat": row["lat"], "lng": row["lng"]},
            "rating": row.get("rating", 0),
            "maps_url": f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote_plus(place_name + ', ' + city)}",
        }

    def _fallback_place_data(self, place_name: str, city: str = "") -> dict:
        return {
            "place_id": None,
            "name": place_name,
            "formatted_address": f"{place_name}, {city}".strip(", "),
            "location": {"lat": 0, "lng": 0},
            "rating": 0,
            "maps_url": f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote_plus(place_name + ', ' + city)}",
        }

    def get_static_map_image(self, place_name: str, city: str = "", zoom: int = 15, size: str = "600x400") -> str:
        q = urllib.parse.quote_plus(f"{place_name}, {city}".strip(", "))
        return f"https://www.google.com/maps/search/?api=1&query={q}"
