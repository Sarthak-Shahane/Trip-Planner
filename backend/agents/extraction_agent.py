import trip_database


class ExtractionAgent:
    """Parse user text and map to a bundled destination profile (SQLite only)."""

    def extract_details(self, user_input: str) -> dict:
        return trip_database.parse_travel_details(user_input)
