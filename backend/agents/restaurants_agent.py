import trip_database


class RestaurantsAgent:
    """Load restaurants from the local catalog."""

    def find_restaurants(self, travel_details: dict) -> list:
        key = travel_details.get("destination_key") or trip_database.match_destination_key(
            travel_details.get("destination", "")
        )
        return trip_database.get_catalog_restaurants(key)
