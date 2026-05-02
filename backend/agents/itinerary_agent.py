class ItineraryAgent:
    """Build a day-by-day plan by rotating catalog places and restaurants (no LLM)."""

    def create_itinerary(self, travel_details: dict, places: list, restaurants: list) -> list:
        destination = travel_details.get("destination", "")
        duration = max(1, int(travel_details.get("duration", 7)))

        if not places:
            places = [
                {
                    "name": "City orientation walk",
                    "description": "Stroll the main district and note transit stops.",
                    "location": destination or "City center",
                    "duration": "2 hours",
                    "entry_fee": "Free",
                }
            ]
        n_p, n_r = len(places), len(restaurants)

        def meal(i: int) -> str:
            if n_r == 0:
                return "Local dining (from your list)"
            return restaurants[i % n_r]["name"]

        days = []
        for day in range(1, duration + 1):
            p0 = places[(day - 1) % n_p]
            p1 = places[day % n_p]
            p2 = places[(day + 1) % n_p]

            def act(time: str, p: dict) -> dict:
                return {
                    "time": time,
                    "activity": p.get("name", "Activity"),
                    "description": (p.get("description") or "")[:200],
                    "location": p.get("location", destination),
                    "duration": p.get("duration", "2 hours"),
                    "cost": p.get("entry_fee", "Free"),
                }

            days.append(
                {
                    "day": day,
                    "title": f"Day {day} — {p0.get('name', 'Exploration')}",
                    "activities": [
                        act("9:00 AM", p0),
                        act("1:00 PM", p1),
                        act("4:30 PM", p2),
                    ],
                    "meals": {
                        "breakfast": meal(day * 3),
                        "lunch": meal(day * 3 + 1),
                        "dinner": meal(day * 3 + 2),
                    },
                    "estimated_cost": "₹6,640-₹13,280",
                    "tips": "Confirm hours locally; allow flex between sights; stay hydrated.",
                }
            )
        return days
