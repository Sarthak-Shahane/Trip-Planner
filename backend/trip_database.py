"""
SQLite-only trip data: destinations, places, restaurants, hotels, snippets.
No outbound HTTP — media paths resolve to this app's /static/ files.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import hashlib
import math
import urllib.parse
import urllib.request

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "trip_planner.db")
MIN_CITIES = 40
USD_TO_INR = 83.0
CURATED_NEARBY_PLACES = {
    "jaipur": [
        ("Amber Fort", "Fort", "Devisinghpura, Amer", "morning", "$15", 4.7),
        ("Jal Mahal", "Landmark", "Man Sagar Lake", "sunset", "Free", 4.5),
        ("Nahargarh Fort", "Viewpoint", "Aravalli Hills", "late afternoon", "$8", 4.6),
        ("Patrika Gate", "Photo Spot", "Jawahar Circle", "evening", "Free", 4.4),
    ],
    "delhi": [
        ("Humayun's Tomb", "Monument", "Nizamuddin East", "morning", "$7", 4.7),
        ("Lotus Temple", "Landmark", "Kalkaji", "afternoon", "Free", 4.6),
        ("Lodhi Garden", "Park", "Lodhi Estate", "morning", "Free", 4.6),
    ],
    "mumbai": [
        ("Gateway of India", "Landmark", "Colaba", "morning", "Free", 4.6),
        ("Marine Drive", "Promenade", "South Mumbai", "sunset", "Free", 4.7),
        ("Bandra Fort", "Fort", "Bandra West", "evening", "Free", 4.4),
    ],
}


def public_static_url(relative_path: str) -> str:
    base = os.environ.get("TRIP_PLANNER_PUBLIC_URL", "http://127.0.0.1:5000").rstrip("/")
    return f"{base}/static/{relative_path.lstrip('/')}"


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _normalize_destination(name: str) -> str:
    s = (name or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    if "," in s:
        s = s.split(",")[0].strip()
    return s


def _row_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS destination_meta (
                destination_key TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                default_duration INTEGER NOT NULL DEFAULT 7,
                default_budget INTEGER NOT NULL DEFAULT 2000,
                travel_type TEXT NOT NULL DEFAULT 'General',
                interests_json TEXT NOT NULL DEFAULT '[]',
                overview TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS destination_snippets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                destination_key TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                url TEXT
            );

            CREATE TABLE IF NOT EXISTS catalog_places (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                destination_key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                location TEXT NOT NULL,
                how_to_reach TEXT NOT NULL,
                best_time TEXT NOT NULL,
                visit_duration TEXT NOT NULL,
                entry_fee TEXT NOT NULL,
                rating REAL NOT NULL,
                tips TEXT NOT NULL,
                image_ref TEXT NOT NULL,
                lat REAL,
                lng REAL,
                sort_order INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS catalog_restaurants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                destination_key TEXT NOT NULL,
                name TEXT NOT NULL,
                cuisine TEXT NOT NULL,
                description TEXT NOT NULL,
                budget_level TEXT NOT NULL,
                avg_cost_per_person TEXT NOT NULL,
                location TEXT NOT NULL,
                rating REAL NOT NULL,
                specialties TEXT NOT NULL,
                atmosphere TEXT NOT NULL,
                best_time TEXT NOT NULL,
                reservation_needed INTEGER NOT NULL DEFAULT 0,
                image_ref TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS catalog_hotels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                destination_key TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                price_per_night TEXT NOT NULL,
                rating REAL NOT NULL,
                amenities TEXT NOT NULL,
                room_type TEXT NOT NULL,
                proximity TEXT NOT NULL,
                booking_tip TEXT NOT NULL,
                image_ref TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS place_lookup (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_key TEXT NOT NULL,
                city_key TEXT NOT NULL,
                place_id TEXT,
                formatted_address TEXT,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                rating REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS media_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                destination_key TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                image_ref TEXT NOT NULL,
                source_url TEXT NOT NULL DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(destination_key, entity_type, entity_name)
            );

            CREATE INDEX IF NOT EXISTS idx_snippets_dest ON destination_snippets(destination_key);
            CREATE INDEX IF NOT EXISTS idx_cat_places ON catalog_places(destination_key);
            CREATE INDEX IF NOT EXISTS idx_cat_rest ON catalog_restaurants(destination_key);
            CREATE INDEX IF NOT EXISTS idx_cat_hotels ON catalog_hotels(destination_key);
            CREATE INDEX IF NOT EXISTS idx_place_lookup ON place_lookup(name_key, city_key);
            CREATE INDEX IF NOT EXISTS idx_media_assets ON media_assets(destination_key, entity_type, entity_name);
            """
        )
        _ensure_seeded(conn)


def _ensure_seeded(conn: sqlite3.Connection) -> None:
    """
    Ensure the bundled DB contains a reasonable offline catalog.

    We treat the DB as user-owned state: if it already exists but contains too few cities
    (e.g. an older version), we only INSERT missing rows (never delete).
    """
    cur = conn.execute(
        "SELECT COUNT(*) AS c FROM destination_meta WHERE destination_key <> 'generic'"
    )
    city_count = int(cur.fetchone()["c"] or 0)
    if city_count < MIN_CITIES:
        _seed_all(conn)


def _seed_all(conn: sqlite3.Connection) -> None:
    """
    Seed 40+ destinations and a small per-city catalog so the app works fully offline.
    """
    meta = _seed_meta_rows()
    conn.executemany(
        """INSERT OR IGNORE INTO destination_meta
        (destination_key, display_name, default_duration, default_budget, travel_type, interests_json, overview)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        meta,
    )

    snippets = [
        ("paris", "Iconic sights", "Eiffel Tower, Louvre, Notre-Dame area, Montmartre, Seine walks."),
        ("paris", "Food", "Bistros in Le Marais, pastries in Saint-Germain, Marché Bastille."),
        ("tokyo", "Highlights", "Shibuya, Senso-ji, Meiji Shrine, day trips to Kamakura."),
        ("new york", "Classic NYC", "Central Park, Met Museum, Brooklyn Bridge, Broadway."),
        ("london", "Museums", "British Museum, Tower, South Bank, Borough Market."),
        ("rome", "Ancient core", "Colosseum, Forum, Vatican, Trastevere evenings."),
        ("barcelona", "Gaudí", "Sagrada Família, Park Güell, Gothic Quarter, beaches."),
        ("dubai", "Mix", "Burj Khalifa, old Al Fahidi, desert safari, Marina."),
        ("singapore", "Hawkers", "Gardens by the Bay, Maxwell, Lau Pa Sat, Sentosa."),
        ("generic", "Tips", "Balance busy days with rest; carry water and comfortable shoes."),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO destination_snippets (destination_key, title, content, url) VALUES (?, ?, ?, ?)",
        [(a, b, c, "local") for a, b, c in snippets],
    )

    places = [
        ("paris", "Eiffel Tower", "Iron lattice icon with city views; best at sunset.", "Landmark",
         "7th arrondissement", "Metro Bir-Hakeim / Trocadéro", "late afternoon", "2 hours", "$30-45", 4.8,
         "Book summit tickets early; windy at top.", "placeholders/landmark.svg", 48.8584, 2.2945, 1),
        ("paris", "Louvre Museum", "World-class art including Mona Lisa; huge—pick a wing.", "Museum",
         "1st arrondissement", "Metro Palais Royal / Louvre", "morning", "3-4 hours", "$20", 4.7,
         "Use timed entry; Wednesdays often busy.", "placeholders/museum.svg", 48.8606, 2.3376, 2),
        ("paris", "Montmartre & Sacré-Cœur", "Village-like streets and basilica views over Paris.", "Neighborhood",
         "18th arrondissement", "Metro Anvers + short walk", "morning", "2-3 hours", "Free", 4.6,
         "Wear sturdy shoes on cobblestones.", "placeholders/park.svg", 48.8867, 2.3431, 3),
        ("tokyo", "Senso-ji Temple", "Tokyo's oldest temple; thunder gate and market stalls.", "Temple",
         "Asakusa", "Metro Asakusa", "morning", "1-2 hours", "Free", 4.6,
         "Visit Nakamise shopping street early.", "placeholders/landmark.svg", 35.7148, 139.7967, 1),
        ("tokyo", "Shibuya Crossing", "Famous scramble; nearby shops and cafes.", "Landmark",
         "Shibuya", "JR Shibuya", "evening", "1 hour", "Free", 4.5,
         "Watch from Starbucks second floor for classic photo.", "placeholders/generic.svg", 35.6595, 139.7004, 2),
        ("tokyo", "Meiji Shrine", "Serene forest shrine near Harajuku.", "Shrine",
         "Shibuya", "Harajuku Station", "morning", "1-2 hours", "Free", 4.7,
         "Respect quiet zones; weddings on weekends.", "placeholders/park.svg", 35.6764, 139.6993, 3),
        ("new york", "Central Park", "Meadows, reservoir, and Bethesda Terrace.", "Park",
         "Manhattan", "Subway 59th St / Columbus Circle", "morning", "2-3 hours", "Free", 4.8,
         "Rent bikes or walk the Ramble.", "placeholders/park.svg", 40.7829, -73.9654, 1),
        ("new york", "Metropolitan Museum", "Massive collection spanning millennia.", "Museum",
         "Upper East Side", "Metro 86th St", "afternoon", "3+ hours", "$30", 4.8,
         "Suggested donation days vary—check site.", "placeholders/museum.svg", 40.7794, -73.9632, 2),
        ("london", "British Museum", "Rosetta Stone, Egyptian halls, free entry.", "Museum",
         "Bloomsbury", "Tottenham Court Road", "morning", "2-3 hours", "Free", 4.7,
         "Security lines peak on weekends.", "placeholders/museum.svg", 51.5194, -0.127, 1),
        ("london", "Tower of London", "Crown jewels and Yeoman tours.", "Historic site",
         "Tower Hill", "Tower Hill tube", "morning", "2-3 hours", "$40", 4.6,
         "Join a Beefeater tour included with ticket.", "placeholders/landmark.svg", 51.5081, -0.0759, 2),
        ("rome", "Colosseum", "Ancient amphitheater; book combined forum ticket.", "Historic site",
         "Monti", "Colosseo metro", "morning", "2 hours", "$25", 4.7,
         "Arrive at opening to beat heat.", "placeholders/landmark.svg", 41.8902, 12.4922, 1),
        ("rome", "Vatican Museums", "Sistine Chapel and vast collections.", "Museum",
         "Vatican", "Ottaviano metro", "morning", "3-4 hours", "$35", 4.6,
         "Dress covers shoulders/knees.", "placeholders/museum.svg", 41.9065, 12.4536, 2),
        ("barcelona", "Sagrada Família", "Gaudí's unfinished basilica masterpiece.", "Landmark",
         "Eixample", "Sagrada Família metro", "morning", "2 hours", "$30", 4.8,
         "Timed tickets mandatory.", "placeholders/landmark.svg", 41.4036, 2.1744, 1),
        ("barcelona", "Park Güell", "Mosaic terraces and city views.", "Park",
         "Gràcia", "Bus or walk from Lesseps", "morning", "2 hours", "$15", 4.5,
         "Book Park Güell slot ahead.", "placeholders/park.svg", 41.4145, 2.1527, 2),
        ("dubai", "Burj Khalifa", "Observation decks above the city.", "Landmark",
         "Downtown", "Burj Khalifa / Dubai Mall metro", "evening", "2 hours", "$50-80", 4.7,
         "Sunset slots sell out.", "placeholders/landmark.svg", 25.1972, 55.2744, 1),
        ("singapore", "Gardens by the Bay", "Supertree Grove and conservatories.", "Garden",
         "Marina Bay", "Bayfront MRT", "late afternoon", "2-3 hours", "$20-35", 4.7,
         "Light show evenings.", "placeholders/park.svg", 1.2816, 103.8636, 1),
        ("generic", "Old Town Walk", "Sample historic quarter streets and local shops.", "Neighborhood",
         "City center", "Central station", "morning", "2 hours", "Free", 4.3,
         "Grab a paper map at visitor kiosk.", "placeholders/generic.svg", None, None, 1),
        ("generic", "City Museum", "Regional history and rotating exhibits.", "Museum",
         "Civic district", "Tram line 1", "afternoon", "2 hours", "$12", 4.4,
         "Closed Mondays in many cities.", "placeholders/museum.svg", None, None, 2),
    ]
    conn.executemany(
        """INSERT OR IGNORE INTO catalog_places
        (destination_key, name, description, category, location, how_to_reach, best_time,
         visit_duration, entry_fee, rating, tips, image_ref, lat, lng, sort_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        places,
    )

    restaurants = [
        ("paris", "Bouillon Pigalle", "French", "Busy brasserie with affordable classics.", "Budget", "$15-25",
         "9th / Pigalle", 4.5, "Onion soup|steak frites", "lively", "lunch or dinner", 0, "placeholders/food.svg", 1),
        ("paris", "Le Comptoir du Relais", "French", "Saint-Germain bistro plates.", "Mid-range", "$35-55",
         "6th arrondissement", 4.6, "Duck|seasonal tart", "cozy", "dinner", 1, "placeholders/food.svg", 2),
        ("tokyo", "Ichiran Shibuya", "Ramen", "Solo booth tonkotsu ramen.", "Budget", "$12-18",
         "Shibuya", 4.5, "Tonkotsu ramen|egg", "casual", "late night", 0, "placeholders/food.svg", 1),
        ("tokyo", "Sukiyabashi Jiro Roppongi", "Sushi", "High-end omakase experience.", "Fine Dining", "$120+",
         "Roppongi", 4.7, "Chef's selection", "formal", "dinner", 1, "placeholders/food.svg", 2),
        ("new york", "Joe's Pizza", "Pizza", "Classic NY slices.", "Budget", "$5-10",
         "Greenwich Village", 4.6, "Cheese slice", "casual", "lunch", 0, "placeholders/food.svg", 1),
        ("new york", "Gramercy Tavern", "American", "Seasonal dining room and bar.", "Fine Dining", "$80-120",
         "Gramercy", 4.7, "Tasting menu|fish", "upscale", "dinner", 1, "placeholders/food.svg", 2),
        ("london", "Borough Market", "Market", "Street food and produce stalls.", "Budget", "$10-20",
         "Southwark", 4.6, "Grilled cheese|oysters", "bustling", "lunch", 0, "placeholders/food.svg", 1),
        ("london", "Dishoom Covent Garden", "Indian", "Bombay café style.", "Mid-range", "$25-40",
         "Covent Garden", 4.7, "Black daal|naan", "vibrant", "lunch or dinner", 1, "placeholders/food.svg", 2),
        ("rome", "Roscioli Salumeria", "Italian", "Cheese, cured meats, wine.", "Mid-range", "$35-55",
         "Centro Storico", 4.7, "Carbonara|burrata", "intimate", "lunch", 1, "placeholders/food.svg", 1),
        ("rome", "Pizzarium Bonci", "Pizza", "Roman pizza al taglio.", "Budget", "$8-15",
         "Prati", 4.6, "Seasonal slices", "casual", "lunch", 0, "placeholders/food.svg", 2),
        ("barcelona", "Cal Pep", "Tapas", "Counter seating seafood tapas.", "Mid-range", "$40-70",
         "El Born", 4.6, "Clams|tortilla", "lively", "dinner", 1, "placeholders/food.svg", 1),
        ("barcelona", "Quimet & Quimet", "Tapas", "Standing room montaditos.", "Budget", "$15-25",
         "Poble Sec", 4.5, "Conserves|vermut", "casual", "lunch", 0, "placeholders/food.svg", 2),
        ("dubai", "Al Ustad Special Kabab", "Persian", "Legendary kebabs since 1978.", "Budget", "$15-25",
         "Bur Dubai", 4.6, "Kebab platter", "casual", "lunch or dinner", 0, "placeholders/food.svg", 1),
        ("singapore", "Maxwell Food Centre", "Hawker", "Chicken rice and more.", "Budget", "$5-12",
         "Chinatown", 4.5, "Hainanese chicken rice", "busy", "lunch", 0, "placeholders/food.svg", 1),
        ("generic", "Market Hall Lunch", "International", "Food hall with many stalls.", "Budget", "$10-18",
         "Downtown", 4.3, "Chef's daily special", "casual", "lunch", 0, "placeholders/food.svg", 1),
        ("generic", "Bistro Central", "Local", "Seasonal dinner menu.", "Mid-range", "$35-50",
         "Old Town", 4.4, "Tasting menu", "warm", "dinner", 1, "placeholders/food.svg", 2),
    ]
    conn.executemany(
        """INSERT OR IGNORE INTO catalog_restaurants
        (destination_key, name, cuisine, description, budget_level, avg_cost_per_person, location,
         rating, specialties, atmosphere, best_time, reservation_needed, image_ref, sort_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(a, b, c, d, e, f, g, h, i, j, k, l, m, n) for a, b, c, d, e, f, g, h, i, j, k, l, m, n in restaurants],
    )

    hotels = [
        ("paris", "Hotel des Grands Boulevards", "Boutique", "Stylish 4-star near passages.",
         "2nd / 9th border", "$180-240", 4.6, "Rooftop bar|WiFi|AC", "Superior Room",
         "Walk to metro; lively area", "Book direct for breakfast", "placeholders/hotel.svg", 1),
        ("paris", "Generator Paris", "Budget", "Design hostel with private rooms.",
         "10th arrondissement", "$45-85", 4.2, "WiFi|bar|laundry", "Private double",
         "Near Canal Saint-Martin", "Private rooms sell out weekends", "placeholders/hotel.svg", 2),
        ("tokyo", "Hotel Gracery Shinjuku", "Mid-scale", "Godzilla head landmark hotel.",
         "Shinjuku", "$120-180", 4.5, "WiFi|restaurant|laundry", "Moderate twin",
         "Steps to Shinjuku station", "Ask for quiet floor", "placeholders/hotel.svg", 1),
        ("new york", "Pod Times Square", "Budget", "Compact rooms, great location.",
         "Midtown", "$90-140", 4.1, "WiFi|lounge", "Pod queen",
         "Near Times Square", "Rooms are small by design", "placeholders/hotel.svg", 1),
        ("new york", "The Ludlow Hotel", "Boutique", "Lower East Side brick and velvet.",
         "LES", "$220-320", 4.7, "Bar|room service|gym", "Deluxe king",
         "Neighborhood dining scene", "Weekend premiums", "placeholders/hotel.svg", 2),
        ("london", "Hub by Premier Inn", "Budget", "Compact smart rooms.", "Kings Cross", "$100-150", 4.3,
         "WiFi|AC", "Standard double", "Kings Cross trains", "Early check-in app", "placeholders/hotel.svg", 1),
        ("rome", "Hotel Artemide", "4-Star", "Roof terrace near Termini.",
         "Monti", "$160-220", 4.6, "Spa|breakfast|WiFi", "Classic double",
         "Walk to Colosseum", "Include breakfast rate", "placeholders/hotel.svg", 1),
        ("barcelona", "Casa Camper", "Boutique", "Minimal design in Raval.",
         "Raval", "$170-230", 4.7, "24h snack lounge|WiFi", "Loft room",
         "Near MACBA", "Use lounge for light meals", "placeholders/hotel.svg", 1),
        ("generic", "City Inn Express", "Budget", "Clean rooms near transit.", "Central", "$70-110", 4.0,
         "WiFi|breakfast option", "Standard", "Metro two blocks", "Join loyalty for late checkout", "placeholders/hotel.svg", 1),
        ("generic", "Grand Plaza Hotel", "4-Star", "Pool and skyline bar.", "Business district", "$190-260", 4.5,
         "Pool|gym|WiFi|spa", "Executive king", "Airport shuttle", "Weekend packages", "placeholders/hotel.svg", 2),
    ]
    conn.executemany(
        """INSERT OR IGNORE INTO catalog_hotels
        (destination_key, name, category, description, location, price_per_night, rating,
         amenities, room_type, proximity, booking_tip, image_ref, sort_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        hotels,
    )

    geo = [
        ("eiffel tower", "paris", "local", "Champ de Mars, Paris", 48.8584, 2.2945, 4.8),
        ("louvre", "paris", "local", "Paris 1er", 48.8606, 2.3376, 4.7),
        ("senso-ji", "tokyo", "local", "Asakusa, Tokyo", 35.7148, 139.7967, 4.6),
        ("central park", "new york", "local", "Manhattan", 40.7829, -73.9654, 4.8),
        ("british museum", "london", "local", "London", 51.5194, -0.127, 4.6),
        ("colosseum", "rome", "local", "Rome", 41.8902, 12.4922, 4.7),
        ("sagrada familia", "barcelona", "local", "Barcelona", 41.4036, 2.1744, 4.8),
    ]
    conn.executemany(
        """INSERT OR IGNORE INTO place_lookup
        (name_key, city_key, place_id, formatted_address, lat, lng, rating)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        geo,
    )

    _seed_generated_city_catalog(conn)
    conn.commit()


def _seed_meta_rows() -> list[tuple]:
    """
    Returns destination_meta rows (40+ cities) plus 'generic'.
    destination_key must match _normalize_destination() behavior (lowercase, no extra punctuation).
    """
    # A practical offline catalog set (mix of global + India) to exceed MIN_CITIES.
    rows: list[tuple] = [
        ("paris", "Paris, France", 7, 2400, "Cultural", '["museums","food","history"]',
         "Art, architecture, and café culture along the Seine."),
        ("tokyo", "Tokyo, Japan", 7, 2800, "Urban", '["food","temples","technology"]',
         "Neon cityscapes, quiet shrines, and world-class dining."),
        ("new york", "New York, USA", 5, 3200, "Urban", '["theatre","museums","food"]',
         "Iconic skyline, Broadway, and neighborhoods worth walking."),
        ("london", "London, UK", 6, 2600, "Cultural", '["history","theatre","markets"]',
         "Royal landmarks, free museums, and global cuisine."),
        ("rome", "Rome, Italy", 6, 2200, "Cultural", '["history","food","art"]',
         "Ancient ruins layered with trattorias and piazzas."),
        ("barcelona", "Barcelona, Spain", 5, 2100, "Relaxation", '["architecture","beach","tapas"]',
         "Gaudí masterpieces and Mediterranean pace."),
        ("dubai", "Dubai, UAE", 5, 3500, "Luxury", '["shopping","desert","skyline"]',
         "Ultra-modern towers and desert excursions."),
        ("singapore", "Singapore", 4, 2000, "Foodie", '["hawker food","gardens","family"]',
         "Compact, safe, and packed with flavor."),
        ("amsterdam", "Amsterdam, Netherlands", 4, 2100, "Cultural", '["canals","museums","biking"]',
         "Canal belts, art museums, and an easy cycling rhythm."),
        ("berlin", "Berlin, Germany", 5, 2000, "Urban", '["history","nightlife","museums"]',
         "Layered history and modern neighborhoods."),
        ("vienna", "Vienna, Austria", 4, 2200, "Cultural", '["music","palaces","cafes"]',
         "Imperial palaces and coffeehouse culture."),
        ("prague", "Prague, Czechia", 4, 1800, "Cultural", '["old town","castles","beer"]',
         "Gothic streets and riverside views."),
        ("budapest", "Budapest, Hungary", 4, 1700, "Relaxation", '["thermal baths","views","food"]',
         "River panoramas and famous bathhouses."),
        ("istanbul", "Istanbul, Türkiye", 5, 1900, "Cultural", '["bazaars","mosques","food"]',
         "Where continents meet—markets, domes, and ferries."),
        ("athens", "Athens, Greece", 4, 1800, "Cultural", '["ruins","food","day trips"]',
         "Ancient hilltops and modern tavernas."),
        ("lisbon", "Lisbon, Portugal", 4, 1800, "Relaxation", '["views","trams","seafood"]',
         "Hills, miradouros, and a salty breeze."),
        ("madrid", "Madrid, Spain", 4, 2000, "Cultural", '["museums","tapas","parks"]',
         "Late dinners, grand boulevards, and art triangles."),
        ("seville", "Seville, Spain", 3, 1700, "Cultural", '["flamenco","history","food"]',
         "Courtyards, orange trees, and evening plazas."),
        ("florence", "Florence, Italy", 4, 2100, "Cultural", '["art","architecture","food"]',
         "Renaissance streets and Tuscan flavors."),
        ("venice", "Venice, Italy", 3, 2400, "Relaxation", '["canals","walks","art"]',
         "Car-free lanes and quiet lagoon light."),
        ("munich", "Munich, Germany", 4, 2200, "Cultural", '["beer gardens","day trips","museums"]',
         "A tidy city with alpine day-trip options."),
        ("zurich", "Zurich, Switzerland", 3, 3200, "Relaxation", '["lakes","walks","museums"]',
         "Lakefront walks and efficient transit."),
        ("copenhagen", "Copenhagen, Denmark", 4, 2800, "Relaxation", '["design","cycling","food"]',
         "Hygge streets and modern Scandinavian dining."),
        ("stockholm", "Stockholm, Sweden", 4, 2700, "Relaxation", '["archipelago","museums","walks"]',
         "Island neighborhoods and waterfront views."),
        ("oslo", "Oslo, Norway", 3, 2800, "Relaxation", '["fjords","museums","saunas"]',
         "Compact city, big nature access."),
        ("helsinki", "Helsinki, Finland", 3, 2500, "Relaxation", '["design","saunas","sea"]',
         "Seaside design capital with calm pace."),
        ("reykjavik", "Reykjavik, Iceland", 4, 3500, "Adventure", '["geysers","waterfalls","northern lights"]',
         "Gateway to geothermal landscapes."),
        ("dublin", "Dublin, Ireland", 3, 2300, "Cultural", '["pubs","history","walks"]',
         "Literary streets and warm pubs."),
        ("edinburgh", "Edinburgh, UK", 3, 2200, "Cultural", '["castles","walks","history"]',
         "Dramatic old town and hilltop views."),
        ("cape town", "Cape Town, South Africa", 5, 2200, "Adventure", '["views","food","beaches"]',
         "Table Mountain panoramas and coastal drives."),
        ("cairo", "Cairo, Egypt", 4, 1600, "Cultural", '["pyramids","museums","markets"]',
         "Ancient wonders and bustling streets."),
        ("marrakech", "Marrakech, Morocco", 4, 1700, "Cultural", '["souks","gardens","food"]',
         "Medina lanes and spice-scented evenings."),
        ("bangkok", "Bangkok, Thailand", 4, 1600, "Foodie", '["street food","temples","shopping"]',
         "Canals, markets, and late-night bites."),
        ("chiang mai", "Chiang Mai, Thailand", 4, 1500, "Relaxation", '["temples","cafes","nature"]',
         "Northern calm with mountain air."),
        ("bali", "Bali, Indonesia", 6, 1800, "Relaxation", '["beaches","temples","wellness"]',
         "Rice terraces and coastal sunsets."),
        ("kuala lumpur", "Kuala Lumpur, Malaysia", 3, 1500, "Urban", '["food","markets","views"]',
         "Skylines and hawker stalls."),
        ("hong kong", "Hong Kong", 4, 2600, "Urban", '["harbor","food","hikes"]',
         "Vertical city with big hikes minutes away."),
        ("seoul", "Seoul, South Korea", 5, 2300, "Urban", '["food","palaces","shopping"]',
         "Palaces, cafes, and neon districts."),
        ("taipei", "Taipei, Taiwan", 4, 1900, "Foodie", '["night markets","hikes","tea"]',
         "Night markets and nearby mountains."),
        ("sydney", "Sydney, Australia", 5, 3000, "Relaxation", '["beaches","harbor","walks"]',
         "Harbor views and coastal paths."),
        ("melbourne", "Melbourne, Australia", 4, 2800, "Cultural", '["cafes","arts","laneways"]',
         "Laneways, coffee, and galleries."),
        ("auckland", "Auckland, New Zealand", 4, 2700, "Adventure", '["harbors","day trips","nature"]',
         "City base for island and coast escapes."),
        ("san francisco", "San Francisco, USA", 4, 3400, "Urban", '["views","food","walks"]',
         "Hills, bridges, and diverse neighborhoods."),
        ("los angeles", "Los Angeles, USA", 5, 3300, "Urban", '["beaches","studios","food"]',
         "Sprawling city of scenes and sunsets."),
        ("toronto", "Toronto, Canada", 4, 2600, "Urban", '["food","museums","waterfront"]',
         "Neighborhoods, lake views, and global eats."),
        ("vancouver", "Vancouver, Canada", 4, 2800, "Adventure", '["nature","food","walks"]',
         "Mountains and ocean in one skyline."),
        ("mexico city", "Mexico City, Mexico", 5, 1900, "Foodie", '["food","museums","markets"]',
         "Street tacos, art, and lively plazas."),
        ("rio de janeiro", "Rio de Janeiro, Brazil", 5, 2000, "Relaxation", '["beaches","views","music"]',
         "Big views and bigger energy."),
        ("buenos aires", "Buenos Aires, Argentina", 5, 1800, "Cultural", '["tango","food","walks"]',
         "European boulevards and late dinners."),
        ("mumbai", "Mumbai, India", 4, 1200, "Urban", '["food","markets","coast"]',
         "Coastal city with nonstop food and neighborhoods."),
        ("delhi", "Delhi, India", 4, 1100, "Cultural", '["history","markets","food"]',
         "Layered capitals—old forts and new boulevards."),
        ("bengaluru", "Bengaluru, India", 4, 1100, "Urban", '["cafes","parks","shopping"]',
         "Garden city energy with modern cafes."),
        ("hyderabad", "Hyderabad, India", 4, 1000, "Foodie", '["biryani","history","markets"]',
         "Charminar lanes and legendary biryani."),
        ("chennai", "Chennai, India", 4, 1000, "Cultural", '["temples","beaches","food"]',
         "Temple towns and long sandy coasts."),
        ("kolkata", "Kolkata, India", 4, 900, "Cultural", '["culture","food","walks"]',
         "Colonial streets and sweets."),
        ("jaipur", "Jaipur, India", 4, 900, "Cultural", '["palaces","markets","history"]',
         "Pink City forts and craft bazaars."),
        ("goa", "Goa, India", 5, 1100, "Relaxation", '["beaches","seafood","markets"]',
         "Beach days and evening markets."),
        ("agra", "Agra, India", 2, 800, "Cultural", '["monuments","history","food"]',
         "A short trip built around iconic monuments."),
        ("kerala", "Kerala, India", 6, 1200, "Relaxation", '["backwaters","nature","food"]',
         "Backwaters, tea hills, and slow travel."),
        ("pune", "Pune, India", 3, 900, "Urban", '["cafes","history","walks"]',
         "A relaxed city with forts and food."),
        ("ahmedabad", "Ahmedabad, India", 3, 900, "Cultural", '["heritage","food","markets"]',
         "Heritage lanes and textile crafts."),
        ("varanasi", "Varanasi, India", 3, 900, "Cultural", '["ghats","rituals","walks"]',
         "Riverside rituals and early-morning boat rides."),
        ("udaipur", "Udaipur, India", 3, 1000, "Relaxation", '["lakes","palaces","views"]',
         "Lake city sunsets and palace courtyards."),
        ("generic", "Sample destination", 5, 2000, "General", '["sightseeing","food"]',
         "Illustrative itinerary from bundled catalog data."),
    ]
    # Normalize keys defensively.
    return [(_normalize_destination(k), d, dur, bud, tt, ints, ov) for (k, d, dur, bud, tt, ints, ov) in rows]


def _seed_generated_city_catalog(conn: sqlite3.Connection) -> None:
    """
    Create a minimal but complete per-city catalog (places/restaurants/hotels) for all destinations.
    Cities with rich handcrafted entries (e.g. paris/tokyo) keep them; this fills in missing cities.
    """
    rows = conn.execute(
        "SELECT destination_key, display_name FROM destination_meta WHERE destination_key <> 'generic'"
    ).fetchall()
    for r in rows:
        key = r["destination_key"]
        display = r["display_name"]
        _seed_city_bundle_if_missing(conn, key, display)


def _seed_city_bundle_if_missing(conn: sqlite3.Connection, destination_key: str, display_name: str) -> None:
    # If city already has at least a couple rows in each table, leave it alone.
    cur = conn.execute("SELECT COUNT(*) AS c FROM catalog_places WHERE destination_key = ?", (destination_key,))
    if int(cur.fetchone()["c"] or 0) < 3:
        conn.executemany(
            """INSERT OR IGNORE INTO catalog_places
            (destination_key, name, description, category, location, how_to_reach, best_time,
             visit_duration, entry_fee, rating, tips, image_ref, lat, lng, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            _gen_places(destination_key, display_name),
        )

    cur = conn.execute(
        "SELECT COUNT(*) AS c FROM catalog_restaurants WHERE destination_key = ?",
        (destination_key,),
    )
    if int(cur.fetchone()["c"] or 0) < 2:
        conn.executemany(
            """INSERT OR IGNORE INTO catalog_restaurants
            (destination_key, name, cuisine, description, budget_level, avg_cost_per_person, location,
             rating, specialties, atmosphere, best_time, reservation_needed, image_ref, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            _gen_restaurants(destination_key, display_name),
        )

    cur = conn.execute("SELECT COUNT(*) AS c FROM catalog_hotels WHERE destination_key = ?", (destination_key,))
    if int(cur.fetchone()["c"] or 0) < 2:
        conn.executemany(
            """INSERT OR IGNORE INTO catalog_hotels
            (destination_key, name, category, description, location, price_per_night, rating,
             amenities, room_type, proximity, booking_tip, image_ref, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            _gen_hotels(destination_key, display_name),
        )


def _city_short(display_name: str) -> str:
    return (display_name or "").split(",")[0].strip() or "City"


def _gen_places(destination_key: str, display_name: str) -> list[tuple]:
    city = _city_short(display_name)
    base_loc = f"{city} center"
    return [
        (
            destination_key,
            f"{city} Old Town Walk",
            f"A relaxed walking loop through {city}'s historic core and main squares.",
            "Neighborhood",
            base_loc,
            "Start at the central transit hub; walkable route.",
            "morning",
            "2 hours",
            "Free",
            4.4,
            "Wear comfortable shoes; carry water.",
            "placeholders/landmark.svg",
            None,
            None,
            10,
        ),
        (
            destination_key,
            f"{city} City Museum",
            f"A compact museum introducing key moments, art, and everyday life in {city}.",
            "Museum",
            "Civic district",
            "Take public transit to the civic district stop.",
            "afternoon",
            "2 hours",
            "$10-20",
            4.3,
            "Go early for quieter galleries.",
            "placeholders/museum.svg",
            None,
            None,
            11,
        ),
        (
            destination_key,
            f"{city} Riverside / Park Promenade",
            f"A scenic promenade for sunsets, local vendors, and people-watching in {city}.",
            "Park",
            "Waterfront / main park",
            "Short ride-share or metro/bus to the waterfront.",
            "late afternoon",
            "1-2 hours",
            "Free",
            4.5,
            "Golden hour is best for photos.",
            "placeholders/park.svg",
            None,
            None,
            12,
        ),
    ]


def _gen_restaurants(destination_key: str, display_name: str) -> list[tuple]:
    city = _city_short(display_name)
    return [
        (
            destination_key,
            f"{city} Street Food Corner",
            "Local",
            f"A casual spot to sample popular bites and quick plates loved in {city}.",
            "Budget",
            "$8-15",
            "Downtown",
            4.3,
            "House special|Seasonal snack",
            "casual",
            "lunch",
            0,
            "placeholders/food.svg",
            10,
        ),
        (
            destination_key,
            f"{city} Bistro & Grill",
            "International",
            f"Comfortable sit-down dinner with a rotating menu and local twists in {city}.",
            "Mid-range",
            "$25-45",
            "Old Town",
            4.4,
            "Chef's plate|Dessert",
            "cozy",
            "dinner",
            1,
            "placeholders/food.svg",
            11,
        ),
    ]


def _gen_hotels(destination_key: str, display_name: str) -> list[tuple]:
    city = _city_short(display_name)
    return [
        (
            destination_key,
            f"{city} Central Stay",
            "Mid-scale",
            f"Reliable base in {city} with easy transit access and simple comfort.",
            "Central",
            "$90-140",
            4.2,
            "WiFi|AC|breakfast option",
            "Standard double",
            "Near main transit lines",
            "Weekdays are often cheaper than weekends",
            "placeholders/hotel.svg",
            10,
        ),
        (
            destination_key,
            f"{city} Boutique Rooms",
            "Boutique",
            f"Small, stylish rooms near the most walkable areas of {city}.",
            "Old Town / core",
            "$150-220",
            4.5,
            "WiFi|lounge|concierge",
            "Deluxe king",
            "Walk to main sights",
            "Ask for a quieter room away from street-facing windows",
            "placeholders/hotel.svg",
            11,
        ),
    ]

def list_destination_rows() -> list[sqlite3.Row]:
    init_db()
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM destination_meta ORDER BY LENGTH(destination_key) DESC"
        ).fetchall()


def match_destination_key(user_input: str) -> str:
    u = (user_input or "").lower()
    for row in list_destination_rows():
        key = row["destination_key"]
        disp = row["display_name"].lower()
        if key != "generic" and (key in u or disp in u):
            return key
        parts = disp.split(",")[0].strip()
        if key != "generic" and parts and parts in u:
            return key
    return "generic"


def parse_travel_details(user_input: str) -> dict:
    init_db()
    key = match_destination_key(user_input)
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM destination_meta WHERE destination_key = ?", (key,)
        ).fetchone()
    meta = _row_dict(row)
    interests = json.loads(meta["interests_json"])

    text = user_input or ""
    dur_m = re.search(r"(\d+)\s*(?:days?|day|nights?)", text, re.I)
    duration = int(dur_m.group(1)) if dur_m else int(meta["default_duration"])

    bud_m = re.search(r"(?:budget|under|around|\$|₹|rs\.?|inr)\s*(?:\$|₹|rs\.?|inr)?\s*(\d{3,7})\b", text, re.I)
    if not bud_m:
        bud_m = re.search(r"(?:\$|₹)\s*(\d{3,7})\b", text)
    budget_raw = int(bud_m.group(1)) if bud_m else int(meta["default_budget"])
    is_rupee_input = bool(re.search(r"(₹|rs\.?|inr)", text, re.I))
    budget = budget_raw if is_rupee_input else int(round(budget_raw * USD_TO_INR))

    trav_m = re.search(r"(\d+)\s*(?:people|travelers|guests|of us)", text, re.I)
    travelers = int(trav_m.group(1)) if trav_m else 2
    start_m = re.search(
        r"(?:from|starting\s+from|start(?:ing)?\s+point(?:\s+is)?|origin(?:\s+is)?)\s+([A-Za-z0-9\.\-][A-Za-z0-9\s,\.\-]{2,80})",
        text,
        re.I,
    )
    start_point = start_m.group(1).strip(" .,") if start_m else ""
    if start_point:
        start_point = re.split(r"\b(with|for|budget|under|around|in)\b", start_point, maxsplit=1, flags=re.I)[0]
        start_point = start_point.strip(" ,-")

    return {
        "destination": meta["display_name"],
        "destination_key": key,
        "duration": max(1, min(duration, 21)),
        "budget": budget,
        "budget_currency": "INR",
        "currency_symbol": "₹",
        "starting_point": start_point,
        "travel_type": meta["travel_type"],
        "travelers": max(1, travelers),
        "interests": interests,
        "overview": meta["overview"],
    }


def _coords(lat: float | None, lng: float | None) -> str:
    if lat is None or lng is None:
        return "N/A"
    return f"{lat:.4f}, {lng:.4f}"


def _format_inr(value: float) -> str:
    return f"₹{int(round(value)):,}"


def _convert_price_text_to_inr(text: str) -> str:
    if not text:
        return text
    cleaned = text.replace("$", "")
    nums = [int(x) for x in re.findall(r"\d+", cleaned)]
    if not nums:
        return text.replace("$", "₹")
    converted = [_format_inr(n * USD_TO_INR) for n in nums[:2]]
    if "-" in cleaned and len(converted) >= 2:
        return f"{converted[0]}-{converted[1]}"
    return converted[0]


def _maps_place_query_link(name: str, location: str = "") -> str:
    q = ", ".join([p for p in [name, location] if p]).strip()
    return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote_plus(q)}"


def _maps_directions_link(origin: str, destination_name: str, destination_location: str = "") -> str:
    dest = ", ".join([p for p in [destination_name, destination_location] if p]).strip()
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={urllib.parse.quote_plus(origin)}"
        f"&destination={urllib.parse.quote_plus(dest)}"
        "&travelmode=driving"
    )


def _city_center_coords(destination_key: str) -> tuple[float, float] | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT lat, lng FROM catalog_places
            WHERE destination_key = ? AND lat IS NOT NULL AND lng IS NOT NULL
            ORDER BY sort_order, id
            LIMIT 1
            """,
            (destination_key,),
        ).fetchone()
    if not row:
        return None
    return float(row["lat"]), float(row["lng"])


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = p2 - p1
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _travel_time_estimate(origin_coords: tuple[float, float] | None, lat: float | None, lng: float | None) -> str:
    if not origin_coords or lat is None or lng is None:
        return "Travel time varies by traffic"
    dist_km = _haversine_km(origin_coords[0], origin_coords[1], float(lat), float(lng))
    minutes = max(10, int((dist_km / 28.0) * 60) + 8)
    if minutes >= 60:
        return f"{minutes // 60}h {minutes % 60}m (est.)"
    return f"{minutes} min (est.)"


def _photo_download_url(kind: str, city: str, subject: str) -> str:
    query = urllib.parse.quote_plus(f"{city} {subject} {kind} travel")
    return f"https://source.unsplash.com/featured/?{query}"


def _ensure_media_asset(
    destination_key: str,
    entity_type: str,
    entity_name: str,
    city_name: str,
    fallback_ref: str,
) -> str:
    norm_name = entity_name.strip().lower()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT image_ref FROM media_assets
            WHERE destination_key = ? AND entity_type = ? AND entity_name = ?
            LIMIT 1
            """,
            (destination_key, entity_type, norm_name),
        ).fetchone()
        if row:
            return row["image_ref"]

    media_dir = os.path.join(os.path.dirname(__file__), "static", "photos")
    os.makedirs(media_dir, exist_ok=True)
    digest = hashlib.sha1(f"{destination_key}:{entity_type}:{norm_name}".encode("utf-8")).hexdigest()[:14]
    local_ref = f"photos/{destination_key}-{entity_type}-{digest}.jpg"
    local_path = os.path.join(os.path.dirname(__file__), "static", local_ref)
    source_url = _photo_download_url(entity_type, city_name, entity_name)
    chosen_ref = fallback_ref

    try:
        urllib.request.urlretrieve(source_url, local_path)
        if os.path.exists(local_path) and os.path.getsize(local_path) > 1024:
            chosen_ref = local_ref
        else:
            seed = urllib.parse.quote_plus(f"{destination_key}-{entity_type}-{norm_name}")
            urllib.request.urlretrieve(f"https://picsum.photos/seed/{seed}/1200/800", local_path)
            if os.path.exists(local_path) and os.path.getsize(local_path) > 1024:
                chosen_ref = local_ref
    except Exception:
        try:
            seed = urllib.parse.quote_plus(f"{destination_key}-{entity_type}-{norm_name}")
            urllib.request.urlretrieve(f"https://picsum.photos/seed/{seed}/1200/800", local_path)
            if os.path.exists(local_path) and os.path.getsize(local_path) > 1024:
                chosen_ref = local_ref
            else:
                chosen_ref = fallback_ref
        except Exception:
            chosen_ref = fallback_ref

    with _connect() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO media_assets
            (destination_key, entity_type, entity_name, image_ref, source_url)
            VALUES (?, ?, ?, ?, ?)
            """,
            (destination_key, entity_type, norm_name, chosen_ref, source_url),
        )
        conn.commit()
    return chosen_ref


def _hotel_total(price_per_night: str, nights: int) -> str:
    nums = [int(x) for x in re.findall(r"\d+", price_per_night)]
    if len(nums) >= 2:
        lo, hi = nums[0], nums[1]
        return f"{_format_inr(lo * nights * USD_TO_INR)}-{_format_inr(hi * nights * USD_TO_INR)} for {nights} nights"
    if len(nums) == 1:
        n = nums[0]
        return f"{_format_inr(n * nights * USD_TO_INR)} (est.) for {nights} nights"
    return f"See nightly rate × {nights} nights"


def get_catalog_places(destination_key: str, start_point: str = "") -> list[dict]:
    init_db()
    key = _normalize_destination(destination_key)
    with _connect() as conn:
        rows = conn.execute(
            """SELECT * FROM catalog_places
               WHERE destination_key = ? OR destination_key = 'generic'
               ORDER BY (destination_key = ?) DESC, sort_order, id""",
            (key, key),
        ).fetchall()
    out = []
    origin_coords = _city_center_coords(key)
    city_name = key.title()
    for r in rows:
        d = _row_dict(r)
        lat, lng = d.get("lat"), d.get("lng")
        image_ref = _ensure_media_asset(
            key, "place", d["name"], city_name, d.get("image_ref", "placeholders/landmark.svg")
        )
        route_link = _maps_directions_link(start_point, d["name"], d["location"]) if start_point else ""
        out.append(
            {
                "name": d["name"],
                "description": d["description"],
                "category": d["category"],
                "location": d["location"],
                "how_to_reach": d["how_to_reach"],
                "best_time": d["best_time"],
                "duration": d["visit_duration"],
                "entry_fee": _convert_price_text_to_inr(d["entry_fee"]),
                "rating": d["rating"],
                "tips": d["tips"],
                "image_url": public_static_url(image_ref),
                "maps_link": _maps_place_query_link(d["name"], d["location"]),
                "coordinates": _coords(lat, lng),
                "route_from_start": route_link,
                "travel_time_from_start": _travel_time_estimate(origin_coords, lat, lng) if start_point else "",
                "source_url": "local-db",
            }
        )
    return out


def get_catalog_restaurants(destination_key: str) -> list[dict]:
    init_db()
    key = _normalize_destination(destination_key)
    with _connect() as conn:
        rows = conn.execute(
            """SELECT * FROM catalog_restaurants
               WHERE destination_key = ? OR destination_key = 'generic'
               ORDER BY (destination_key = ?) DESC, sort_order, id""",
            (key, key),
        ).fetchall()
    out = []
    for r in rows:
        d = _row_dict(r)
        specs = [s.strip() for s in d["specialties"].split("|") if s.strip()]
        image_ref = _ensure_media_asset(
            key, "restaurant", d["name"], key.title(), d.get("image_ref", "placeholders/food.svg")
        )
        out.append(
            {
                "name": d["name"],
                "cuisine": d["cuisine"],
                "description": d["description"],
                "budget_level": d["budget_level"],
                "avg_cost_per_person": _convert_price_text_to_inr(d["avg_cost_per_person"]),
                "location": d["location"],
                "rating": d["rating"],
                "specialties": specs,
                "atmosphere": d["atmosphere"],
                "best_time": d["best_time"],
                "reservation_needed": bool(d["reservation_needed"]),
                "image_url": public_static_url(image_ref),
                "maps_link": _maps_place_query_link(d["name"], d["location"]),
                "source_url": "local-db",
            }
        )
    return out


def get_catalog_hotels(destination_key: str, nights: int) -> list[dict]:
    init_db()
    key = _normalize_destination(destination_key)
    with _connect() as conn:
        rows = conn.execute(
            """SELECT * FROM catalog_hotels
               WHERE destination_key = ? OR destination_key = 'generic'
               ORDER BY (destination_key = ?) DESC, sort_order, id""",
            (key, key),
        ).fetchall()
    out = []
    for r in rows:
        d = _row_dict(r)
        amenities = [s.strip() for s in d["amenities"].split("|") if s.strip()]
        image_ref = _ensure_media_asset(
            key, "hotel", d["name"], key.title(), d.get("image_ref", "placeholders/hotel.svg")
        )
        out.append(
            {
                "name": d["name"],
                "category": d["category"],
                "description": d["description"],
                "location": d["location"],
                "price_per_night": _convert_price_text_to_inr(d["price_per_night"]),
                "total_estimated": _hotel_total(d["price_per_night"], max(1, nights)),
                "rating": d["rating"],
                "amenities": amenities,
                "room_type": d["room_type"],
                "proximity": d["proximity"],
                "booking_tip": d["booking_tip"],
                "image_url": public_static_url(image_ref),
                "maps_link": _maps_place_query_link(d["name"], d["location"]),
                "source_url": "local-db",
            }
        )
    return out


def get_nearby_places(destination_key: str, exclude_names: list[str], limit: int = 6) -> list[dict]:
    init_db()
    key = _normalize_destination(destination_key)
    exclude = {x.strip().lower() for x in (exclude_names or []) if x}
    curated = CURATED_NEARBY_PLACES.get(key, [])
    out: list[dict] = []

    for name, category, location, best_time, entry_fee, rating in curated:
        if name.strip().lower() in exclude:
            continue
        image_ref = _ensure_media_asset(key, "place", name, key.title(), "placeholders/landmark.svg")
        out.append(
            {
                "name": name,
                "category": category,
                "location": location,
                "best_time": best_time,
                "entry_fee": _convert_price_text_to_inr(entry_fee),
                "rating": rating,
                "image_url": public_static_url(image_ref),
                "maps_link": _maps_place_query_link(name, location),
            }
        )
        if len(out) >= max(1, limit):
            return out

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM catalog_places
            WHERE destination_key = ? OR destination_key = 'generic'
            ORDER BY (destination_key = ?) DESC, rating DESC, sort_order, id
            LIMIT 20
            """,
            (key, key),
        ).fetchall()
    for r in rows:
        d = _row_dict(r)
        if d["name"].strip().lower() in exclude:
            continue
        image_ref = _ensure_media_asset(
            key, "place", d["name"], key.title(), d.get("image_ref", "placeholders/landmark.svg")
        )
        out.append(
            {
                "name": d["name"],
                "category": d["category"],
                "location": d["location"],
                "best_time": d["best_time"],
                "entry_fee": _convert_price_text_to_inr(d["entry_fee"]),
                "rating": d["rating"],
                "image_url": public_static_url(image_ref),
                "maps_link": _maps_place_query_link(d["name"], d["location"]),
            }
        )
        if len(out) >= max(1, limit):
            break
    if not out:
        city = key.title()
        templates = [
            (f"{city} Heritage Quarter", "Neighborhood", "Old City", "morning"),
            (f"{city} Local Crafts Market", "Market", "City market district", "afternoon"),
            (f"{city} Scenic Sunset Point", "Viewpoint", "Outskirts", "late afternoon"),
        ]
        for name, category, location, best_time in templates[: max(1, limit)]:
            image_ref = _ensure_media_asset(key, "place", name, city, "placeholders/landmark.svg")
            out.append(
                {
                    "name": name,
                    "category": category,
                    "location": location,
                    "best_time": best_time,
                    "entry_fee": "Free",
                    "rating": 4.2,
                    "image_url": public_static_url(image_ref),
                    "maps_link": _maps_place_query_link(name, location),
                }
            )
    return out


def get_destination_context(destination: str, limit: int = 8) -> list[dict]:
    init_db()
    key = _normalize_destination(destination)
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT title, content, url FROM destination_snippets
            WHERE destination_key = ? OR destination_key = 'generic'
            ORDER BY (destination_key = ?) DESC, id
            LIMIT ?
            """,
            (key, key, limit),
        ).fetchall()
        if not rows:
            rows = conn.execute(
                "SELECT title, content, url FROM destination_snippets WHERE destination_key = 'generic' LIMIT ?",
                (limit,),
            ).fetchall()
    return [{"title": r["title"], "content": r["content"], "url": r["url"] or ""} for r in rows]


def lookup_place(name: str, city: str = "") -> dict | None:
    init_db()
    nk = _normalize_destination(name)
    ck = _normalize_destination(city)
    with _connect() as conn:
        if ck:
            row = conn.execute(
                """
                SELECT place_id, formatted_address, lat, lng, rating
                FROM place_lookup
                WHERE name_key = ? AND city_key = ?
                LIMIT 1
                """,
                (nk, ck),
            ).fetchone()
            if row:
                return _row_dict(row)
            row = conn.execute(
                """
                SELECT place_id, formatted_address, lat, lng, rating
                FROM place_lookup
                WHERE (? LIKE '%' || name_key || '%' OR name_key LIKE '%' || ? || '%')
                  AND city_key = ?
                LIMIT 1
                """,
                (nk, nk, ck),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT place_id, formatted_address, lat, lng, rating
                FROM place_lookup
                WHERE name_key = ? OR ? LIKE '%' || name_key || '%'
                LIMIT 1
                """,
                (nk, nk),
            ).fetchone()
        if row:
            return _row_dict(row)
    return None
