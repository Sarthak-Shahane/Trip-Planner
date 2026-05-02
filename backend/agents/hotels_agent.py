import trip_database


class HotelsAgent:
    """Load hotels from the local catalog."""

    def find_hotels(self, travel_details: dict) -> list:
        key = travel_details.get("destination_key") or trip_database.match_destination_key(
            travel_details.get("destination", "")
        )
        nights = int(travel_details.get("duration", 7))
        return trip_database.get_catalog_hotels(key, nights)
