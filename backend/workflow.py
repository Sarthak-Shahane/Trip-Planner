from typing import TypedDict, Optional, List, Dict, Any

from agents.extraction_agent import ExtractionAgent
from agents.place_agent import PlaceAgent
from agents.restaurants_agent import RestaurantsAgent
from agents.hotels_agent import HotelsAgent
from agents.itinerary_agent import ItineraryAgent


class TravelPlanState(TypedDict, total=False):
    user_input: str
    travel_details: Dict[str, Any]
    places: List[dict]
    restaurants: List[dict]
    hotels: List[dict]
    itinerary: List[dict]
    nearby_places: List[dict]
    budget_breakdown: dict
    error: Optional[str]


class TravelPlanWorkflow:
    """Sequential trip planning using only local SQLite data."""

    def __init__(self):
        self.extraction_agent = ExtractionAgent()
        self.places_agent = PlaceAgent()
        self.restaurants_agent = RestaurantsAgent()
        self.hotels_agent = HotelsAgent()
        self.itinerary_agent = ItineraryAgent()

    def _extract_node(self, state: TravelPlanState) -> TravelPlanState:
        print("Extracting travel details")
        try:
            travel_details = self.extraction_agent.extract_details(state["user_input"])
            state["travel_details"] = travel_details
            print(f"✅ Extracted: {travel_details.get('destination')} — {travel_details.get('duration')} days")
        except Exception as e:
            print(f"❌ Extraction error: {e}")
            state["error"] = str(e)
        return state

    def _places_node(self, state: TravelPlanState) -> TravelPlanState:
        print("🏛️ Loading places from database...")
        try:
            places = self.places_agent.find_places(state["travel_details"])
            state["places"] = places
            print(f"✅ Loaded {len(places)} places")
        except Exception as e:
            print(f"❌ Places error: {e}")
            state["places"] = []
        return state

    def _restaurants_node(self, state: TravelPlanState) -> TravelPlanState:
        print("🍽️ Loading restaurants from database...")
        try:
            restaurants = self.restaurants_agent.find_restaurants(state["travel_details"])
            state["restaurants"] = restaurants
            print(f"✅ Loaded {len(restaurants)} restaurants")
        except Exception as e:
            print(f"❌ Restaurants error: {e}")
            state["restaurants"] = []
        return state

    def _hotels_node(self, state: TravelPlanState) -> TravelPlanState:
        print("🏨 Loading hotels from database...")
        try:
            hotels = self.hotels_agent.find_hotels(state["travel_details"])
            state["hotels"] = hotels
            print(f"✅ Loaded {len(hotels)} hotels")
        except Exception as e:
            print(f"❌ Hotels error: {e}")
            state["hotels"] = []
        return state

    def _itinerary_node(self, state: TravelPlanState) -> TravelPlanState:
        print("📅 Building itinerary from catalog...")
        try:
            itinerary = self.itinerary_agent.create_itinerary(
                state["travel_details"],
                state["places"],
                state["restaurants"],
            )
            state["itinerary"] = itinerary
            duration = int(state.get("travel_details", {}).get("duration", 0) or 0)
            if duration >= 6:
                import trip_database

                destination_key = state.get("travel_details", {}).get("destination_key", "")
                used_names = [p.get("name", "") for p in state.get("places", [])]
                state["nearby_places"] = trip_database.get_nearby_places(destination_key, used_names, limit=8)
            else:
                state["nearby_places"] = []
            state["budget_breakdown"] = self._calculate_budget(state)
            print(f"✅ Built {len(itinerary)} day itinerary")
        except Exception as e:
            print(f"❌ Itinerary error: {e}")
            state["itinerary"] = []
            state["nearby_places"] = []
        return state

    def _calculate_budget(self, state: TravelPlanState) -> dict:
        import re

        def extract_cost(cost_str: str) -> float:
            if not cost_str or cost_str in ("Free", "N/A"):
                return 0
            numbers = [n.replace(",", "") for n in re.findall(r"\d[\d,]*", str(cost_str))]
            if numbers:
                if len(numbers) >= 2:
                    return (float(numbers[0]) + float(numbers[1])) / 2
                return float(numbers[0])
            return 0

        hotels = state.get("hotels", [])
        hotel_costs = [extract_cost(h.get("total_estimated", "0")) for h in hotels]
        accommodation_cost = min(hotel_costs) if hotel_costs else 0

        food_cost = sum(extract_cost(d.get("estimated_cost", "0")) for d in state.get("itinerary", []))

        places = state.get("places", [])
        activities_cost = sum(extract_cost(p.get("entry_fee", "0")) for p in places)

        budget = state.get("travel_details", {}).get("budget", 2000)
        transportation_cost = float(budget) * 0.12
        miscellaneous_cost = float(budget) * 0.08

        total_estimated = (
            accommodation_cost + food_cost + activities_cost + transportation_cost + miscellaneous_cost
        )
        remaining_budget = float(budget) - total_estimated

        return {
            "accommodation": round(accommodation_cost, 2),
            "food": round(food_cost, 2),
            "activities": round(activities_cost, 2),
            "transportation": round(transportation_cost, 2),
            "miscellaneous": round(miscellaneous_cost, 2),
            "total_estimated": round(total_estimated, 2),
            "user_budget": budget,
            "remaining": round(remaining_budget, 2),
            "within_budget": remaining_budget >= 0,
        }

    def plan_travel(self, user_input: str) -> dict:
        print(f"\n🚀 Starting travel planning (local data only)...")
        print(f"📝 User input: {user_input[:100]}...")

        state: TravelPlanState = {
            "user_input": user_input,
            "travel_details": {},
            "places": [],
            "restaurants": [],
            "hotels": [],
            "itinerary": [],
            "nearby_places": [],
            "budget_breakdown": {},
            "error": None,
        }

        state = self._extract_node(state)
        if state.get("error"):
            err_td = dict(state.get("travel_details", {}))
            err_td.pop("destination_key", None)
            return {
                "travel_details": err_td,
                "places": [],
                "restaurants": [],
                "hotels": [],
                "itinerary": [],
                "nearby_places": [],
                "budget_breakdown": {},
                "error": state["error"],
            }

        state = self._places_node(state)
        state = self._restaurants_node(state)
        state = self._hotels_node(state)
        state = self._itinerary_node(state)

        print("\n✅ Workflow complete!")
        travel_details = dict(state.get("travel_details", {}))
        travel_details.pop("destination_key", None)
        return {
            "travel_details": travel_details,
            "places": state.get("places", []),
            "restaurants": state.get("restaurants", []),
            "hotels": state.get("hotels", []),
            "itinerary": state.get("itinerary", []),
            "nearby_places": state.get("nearby_places", []),
            "budget_breakdown": state.get("budget_breakdown", {}),
            "error": state.get("error"),
        }
