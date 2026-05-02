import trip_database


class PlaceAgent:
    """Load places from the local catalog."""

    def find_places(self, travel_details: dict) -> list:
        key = travel_details.get("destination_key") or trip_database.match_destination_key(
            travel_details.get("destination", "")
        )
        return trip_database.get_catalog_places(key, travel_details.get("starting_point", ""))
