import urllib.parse
import trip_database


class Helper:
    """Legacy shim: all assets are local static files under /static/."""

    def __init__(self):
        trip_database.init_db()

    def search_images(self, query: str, num_results: int = 1, category=None) -> list:
        ref = "placeholders/food.svg" if (category or "").lower() == "restaurant" else (
            "placeholders/hotel.svg" if (category or "").lower() == "hotel" else "placeholders/landmark.svg"
        )
        url = trip_database.public_static_url(ref)
        return [url] * max(1, num_results) if num_results else [url]

    def get_maps_link(self, place_name: str, city: str = "") -> str:
        q = ", ".join([p for p in [place_name, city] if p]).strip()
        return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote_plus(q)}"
