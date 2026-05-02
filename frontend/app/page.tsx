'use client'
import { useMemo, useState } from "react";
import Image from "next/image";
import { apiUrl } from '@/lib/api'
import dynamic from "next/dynamic"
import { Loader2, Plane, MapPin, Hotel, UtensilsCrossed, Calendar, Compass, Sparkles, Route } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { InteractivePhoto, DEFAULT_PHOTO_FALLBACK } from "@/components/interactive-photo"

const PlacesMap = dynamic(() => import("@/components/places-map").then((m) => m.PlacesMap), {
  ssr: false,
  loading: () => (
    <div className="h-[420px] w-full rounded-xl border bg-muted/20 grid place-items-center text-sm text-muted-foreground">
      Loading map…
    </div>
  ),
})
const MiniPlaceMap = dynamic(() => import("@/components/mini-place-map").then((m) => m.MiniPlaceMap), {
  ssr: false,
})

interface TravelDetails{
  destination:string
  duration: number
  budget: number
  budget_currency?: string
  currency_symbol?: string
  starting_point?: string
  travelers: number
  travel_type: string
  interests: string[]
  overview: string
}


interface Place {
  name: string
  description: string
  category: string
  location: string
  how_to_reach: string
  best_time: string
  duration: string
  entry_fee: string
  rating: number
  tips: string
  image_url: string
  maps_link: string
  coordinates?: string
  route_from_start?: string
  travel_time_from_start?: string
}

interface Restaurant {
  name: string
  cuisine: string
  description: string
  budget_level: string
  avg_cost_per_person: string
  location: string
  rating: number
  specialties: string[]
  atmosphere: string
  best_time: string
  reservation_needed: boolean
  image_url: string
  maps_link: string
}

interface Hotel {
  name: string
  category: string
  description: string
  location: string
  price_per_night: string
  total_estimated: string
  rating: number
  amenities: string[]
  room_type: string
  proximity: string
  booking_tip: string
  image_url: string
  maps_link: string
}

interface Activity {
  time: string
  activity: string
  description: string
  location: string
  duration: string
  cost: string
}

interface Itinerary {
  day: number
  title: string
  activities: Activity[]
  meals: {
    breakfast: string
    lunch: string
    dinner: string
  }
  estimated_cost: string
  tips: string
}

const OFFLINE_IMG_PLACEHOLDER = DEFAULT_PHOTO_FALLBACK

const inspirationCards = [
  {
    title: "Coastal Escape",
    subtitle: "Sea breeze, sunsets, and slow mornings",
    image: "/images/hero-beach.jpg",
  },
  {
    title: "Epic Roadtrip",
    subtitle: "Scenic drives and hidden viewpoints",
    image: "/images/card-roadtrip.jpg",
  },
  {
    title: "City Lights",
    subtitle: "Cafes, culture, and vibrant nights",
    image: "/images/card-city.jpg",
  },
  {
    title: "Mountain Calm",
    subtitle: "Cool air, treks, and panoramic peaks",
    image: "/images/card-mountains.jpg",
  },
  {
    title: "Wildlife Trails",
    subtitle: "Nature walks and unforgettable sightings",
    image: "/images/card-wildlife.jpg",
  },
  {
    title: "Local Heritage",
    subtitle: "Architecture, stories, and traditions",
    image: "/images/card-culture.jpg",
  },
]

interface TravelPlan {
  travel_details: TravelDetails
  places: Place[]
  restaurants: Restaurant[]
  hotels: Hotel[]
  itinerary: Itinerary[]
  nearby_places?: Place[]
  budget_breakdown: {
    accommodation: number
    food: number
    activities: number
    transportation: number
    miscellaneous: number
    total_estimated: number
    user_budget: number
    remaining: number
    within_budget: boolean
  }
}

const formatINR = (value: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(value)

export default function Home() {
  const [userInput, setUserInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [travelPlan, setTravelPlan] = useState<TravelPlan | null>(null)
  const [error, setError] = useState('')
  const [placeQuery, setPlaceQuery] = useState('')
  const [placeCategory, setPlaceCategory] = useState('all')
  const [startPointInput, setStartPointInput] = useState('')

  const placeCategories = useMemo(() => {
    if (!travelPlan) return []
    return Array.from(new Set(travelPlan.places.map((p) => p.category))).sort()
  }, [travelPlan])

  const filteredPlaces = useMemo(() => {
    if (!travelPlan) return []
    const q = placeQuery.trim().toLowerCase()
    return travelPlan.places.filter((p) => {
      const categoryOk = placeCategory === 'all' || p.category === placeCategory
      const queryOk =
        !q ||
        p.name.toLowerCase().includes(q) ||
        p.location.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q)
      return categoryOk && queryOk
    })
  }, [travelPlan, placeQuery, placeCategory])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setTravelPlan(null)

    try {
      const payloadInput =
        startPointInput.trim() && !/\b(from|starting from|start point|origin)\b/i.test(userInput)
          ? `${userInput.trim()} starting point is ${startPointInput.trim()}`
          : userInput
      const response = await fetch(apiUrl('/api/plan_travel'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_input: payloadInput }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to create travel plan')
      }

      setTravelPlan(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_right,#dbeafe_0%,#f8fafc_30%,#f8fafc_100%)]">
      <div className="pointer-events-none absolute -top-20 -left-10 h-72 w-72 rounded-full bg-sky-300/25 blur-3xl animate-pulse" />
      <div className="pointer-events-none absolute -bottom-20 -right-10 h-72 w-72 rounded-full bg-violet-300/20 blur-3xl animate-pulse [animation-delay:700ms]" />
      <div className="container mx-auto p-4 md:p-8 relative z-10">
        <div className="mb-8 rounded-3xl border border-white/40 bg-white/55 backdrop-blur-xl p-6 md:p-10 shadow-lg">
          <div className="flex items-start justify-between gap-6">
            <div className="space-y-3">
              <div className="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-50/80 px-3 py-1 text-xs text-sky-700">
                <Sparkles className="h-3.5 w-3.5" />
                Local catalog + maps + photos
              </div>
              <h1 className="text-4xl md:text-5xl font-bold tracking-tight bg-gradient-to-r from-slate-900 via-sky-700 to-indigo-700 bg-clip-text text-transparent">
                Travel Planner
              </h1>
              <p className="text-muted-foreground max-w-2xl">
                Get a city itinerary, places, hotels, restaurants, photos, and a map view. Add a starting point (e.g. “from Pune”) to get route links + travel-time estimates.
              </p>
              <div className="flex flex-wrap gap-2 pt-1">
                <Badge variant="secondary" className="gap-1"><Compass className="h-3.5 w-3.5" /> Places</Badge>
                <Badge variant="secondary" className="gap-1"><Hotel className="h-3.5 w-3.5" /> Hotels</Badge>
                <Badge variant="secondary" className="gap-1"><UtensilsCrossed className="h-3.5 w-3.5" /> Food</Badge>
                <Badge variant="secondary" className="gap-1"><Route className="h-3.5 w-3.5" /> Routes</Badge>
              </div>
            </div>
            <div className="hidden md:block w-[320px]">
              <div className="relative rounded-2xl border border-white/20 overflow-hidden text-white p-5 min-h-[220px]">
                <Image src="/images/hero-beach.jpg" alt="Travel hero" fill className="object-cover" sizes="320px" priority />
                <div className="absolute inset-0 bg-gradient-to-br from-slate-900/85 to-indigo-900/60" />
                <div className="relative z-10">
                  <div className="text-sm opacity-80">Tip</div>
                  <div className="mt-2 font-semibold">Try:</div>
                  <div className="mt-2 text-sm opacity-95">
                  “Plan a 7 day trip to Jaipur from Pune with budget ₹80000 for 2 people”
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {!travelPlan && (
          <section className="mb-8">
            <div className="mb-4 flex items-end justify-between">
              <div>
                <h2 className="text-xl md:text-2xl font-semibold text-slate-900">Travel Inspiration</h2>
                <p className="text-sm text-muted-foreground">Fresh internet-fetched visuals now built into your planner.</p>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {inspirationCards.map((card) => (
                <div key={card.title} className="group relative h-52 overflow-hidden rounded-2xl border border-white/40 shadow-md hover:shadow-xl transition-all duration-300">
                  <Image
                    src={card.image}
                    alt={card.title}
                    fill
                    sizes="(max-width: 768px) 100vw, 33vw"
                    className="object-cover transition-transform duration-700 group-hover:scale-110"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 to-transparent" />
                  <div className="absolute bottom-0 left-0 right-0 p-4 text-white">
                    <p className="font-semibold text-lg">{card.title}</p>
                    <p className="text-xs text-white/85">{card.subtitle}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

       {/* Input Form */}
      {!travelPlan && (
        <Card className="max-w-3xl mx-auto border-white/50 bg-white/70 backdrop-blur">
          <CardHeader>
            <CardTitle>Describe Your Dream Trip</CardTitle>
            <CardDescription>
              Tell us about your destination, duration, budget, and interests
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <Textarea
                placeholder="e.g., Plan a 7 day trip to Jaipur from Pune with budget ₹80000 for 2 people. I like forts, markets, and local food..."
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                className="min-h-[150px]"
                required
              />
              <input
                type="text"
                value={startPointInput}
                onChange={(e) => setStartPointInput(e.target.value)}
                placeholder="Optional: Starting location (e.g., Pune or 18.52043, 73.85674)"
                className="h-10 w-full rounded-md border px-3 text-sm bg-background"
              />
              <div className="flex flex-wrap items-center gap-3">
                <p className="text-xs text-muted-foreground">
                  Location auto-detect is disabled. Enter your start location manually.
                </p>
              </div>
              <Button 
                type="submit" 
                className="w-full"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Generating Your Travel Plan...
                  </>
                ) : (
                  <>
                    <Plane className="mr-2 h-4 w-4" />
                    Generate Travel Plan
                  </>
                )}
              </Button>
            </form>
            {error && (
              <div className="mt-4 p-4 border rounded-lg text-destructive">
                {error}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {travelPlan && (
        <div className="space-y-6">
          {/* Summary Header */}
          <Card>
            <CardHeader>
              <CardTitle>Your Personalized Travel Plan</CardTitle>
              <CardDescription>
                {travelPlan.travel_details.overview}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Destination</p>
                  <p className="text-lg font-semibold">{travelPlan.travel_details.destination}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Duration</p>
                  <p className="text-lg font-semibold">{travelPlan.travel_details.duration} days</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Budget</p>
                  <p className="text-lg font-semibold">{formatINR(travelPlan.travel_details.budget)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Travelers</p>
                  <p className="text-lg font-semibold">{travelPlan.travel_details.travelers}</p>
                </div>
              </div>
              {!!travelPlan.travel_details.starting_point && (
                <div className="mt-4 rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                  Routes enabled from <span className="font-semibold text-foreground">{travelPlan.travel_details.starting_point}</span>.
                </div>
              )}
            </CardContent>
          </Card>

          {/* Budget Breakdown */}
          {travelPlan.budget_breakdown && (
            <Card>
              <CardHeader>
                <CardTitle>Budget Breakdown</CardTitle>
                <CardDescription>
                  {travelPlan.budget_breakdown.within_budget ? (
                    <>
                      You&apos;re within budget!{" "}
                      {travelPlan.budget_breakdown.remaining >= 0
                        ? `${formatINR(travelPlan.budget_breakdown.remaining)} remaining`
                        : ""}
                    </>
                  ) : (
                    <>Budget exceeded by {formatINR(Math.abs(travelPlan.budget_breakdown.remaining))}</>
                  )}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Accommodation</span>
                    <span className="font-semibold">{formatINR(travelPlan.budget_breakdown.accommodation)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Food & Dining</span>
                    <span className="font-semibold">{formatINR(travelPlan.budget_breakdown.food)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Activities & Attractions</span>
                    <span className="font-semibold">{formatINR(travelPlan.budget_breakdown.activities)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Transportation</span>
                    <span className="font-semibold">{formatINR(travelPlan.budget_breakdown.transportation)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Miscellaneous</span>
                    <span className="font-semibold">{formatINR(travelPlan.budget_breakdown.miscellaneous)}</span>
                  </div>
                  <div className="border-t pt-3 flex justify-between items-center">
                    <span className="font-semibold">Total Estimated Cost</span>
                    <span className="text-lg font-bold">{formatINR(travelPlan.budget_breakdown.total_estimated)}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-semibold">Your Budget</span>
                    <span className="text-lg font-bold">{formatINR(travelPlan.budget_breakdown.user_budget)}</span>
                  </div>
                  <div className={`border-t pt-3 flex justify-between items-center ${travelPlan.budget_breakdown.within_budget ? 'text-green-600' : 'text-red-600'}`}>
                    <span className="font-semibold">
                      {travelPlan.budget_breakdown.within_budget ? 'Remaining' : 'Over Budget'}
                    </span>
                    <span className="text-lg font-bold">
                      {travelPlan.budget_breakdown.within_budget ? '+' : '-'}
                      {formatINR(Math.abs(travelPlan.budget_breakdown.remaining))}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
          {!!travelPlan.travel_details.starting_point && (
            <Card>
              <CardHeader>
                <CardTitle>Route Planning</CardTitle>
                <CardDescription>
                  Travel-time estimates from {travelPlan.travel_details.starting_point}
                </CardDescription>
              </CardHeader>
            </Card>
          )}

          {/* Tabs for different sections */}
          <Tabs defaultValue="itinerary" className="w-full">
            <TabsList className="grid w-full grid-cols-5">
              <TabsTrigger value="itinerary">
                <Calendar className="h-4 w-4 mr-2" />
                Itinerary
              </TabsTrigger>
              <TabsTrigger value="map">
                <MapPin className="h-4 w-4 mr-2" />
                Map
              </TabsTrigger>
              <TabsTrigger value="places">
                <MapPin className="h-4 w-4 mr-2" />
                Places ({travelPlan.places.length})
              </TabsTrigger>
              <TabsTrigger value="restaurants">
                <UtensilsCrossed className="h-4 w-4 mr-2" />
                Restaurants ({travelPlan.restaurants.length})
              </TabsTrigger>
              <TabsTrigger value="hotels">
                <Hotel className="h-4 w-4 mr-2" />
                Hotels ({travelPlan.hotels.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="map" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Map View</CardTitle>
                  <CardDescription>
                    Interactive map using OpenStreetMap. Markers appear for places with coordinates.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <PlacesMap places={filteredPlaces} />
                </CardContent>
              </Card>
            </TabsContent>
            {/* Itinerary Tab */}
            <TabsContent value="itinerary" className="space-y-4">
              {travelPlan.itinerary.map((day) => (
                <Card key={day.day}>
                  <CardHeader>
                    <CardTitle>Day {day.day}: {day.title}</CardTitle>
                    <CardDescription>
                      Estimated Cost: {day.estimated_cost}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {day.activities.map((activity, idx) => (
                      <div key={idx} className="border-l-2 pl-4">
                        <div className="flex gap-3">
                          <Badge variant="outline">{activity.time}</Badge>
                          <div className="flex-1">
                            <h4 className="font-semibold">{activity.activity}</h4>
                            <p className="text-sm text-muted-foreground mt-1">{activity.description}</p>
                            <div className="flex flex-wrap gap-4 mt-2 text-sm text-muted-foreground">
                              <span>{activity.location}</span>
                              <span>{activity.duration}</span>
                              <span>{activity.cost}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                    
                    <div className="grid grid-cols-3 gap-3 mt-4">
                      <div>
                        <p className="font-semibold text-sm">Breakfast</p>
                        <p className="text-sm text-muted-foreground">{day.meals.breakfast}</p>
                      </div>
                      <div>
                        <p className="font-semibold text-sm">Lunch</p>
                        <p className="text-sm text-muted-foreground">{day.meals.lunch}</p>
                      </div>
                      <div>
                        <p className="font-semibold text-sm">Dinner</p>
                        <p className="text-sm text-muted-foreground">{day.meals.dinner}</p>
                      </div>
                    </div>

                    {day.tips && (
                      <div className="border p-3 rounded-lg">
                        <p className="font-semibold text-sm">Tips for the Day</p>
                        <p className="text-sm text-muted-foreground mt-1">{day.tips}</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </TabsContent>
            {/* Places Tab */}
            <TabsContent value="places">
              <Card className="mb-4">
                <CardContent className="p-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <input
                      value={placeQuery}
                      onChange={(e) => setPlaceQuery(e.target.value)}
                      placeholder="Search place name, location, or description..."
                      className="md:col-span-2 h-10 rounded-md border px-3 text-sm bg-background"
                    />
                    <select
                      value={placeCategory}
                      onChange={(e) => setPlaceCategory(e.target.value)}
                      className="h-10 rounded-md border px-3 text-sm bg-background"
                    >
                      <option value="all">All categories</option>
                      {placeCategories.map((cat) => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </select>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Showing {filteredPlaces.length} of {travelPlan.places.length} places
                  </p>
                </CardContent>
              </Card>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredPlaces.map((place, idx) => (
                  <Card key={idx}>
                    <div className="relative h-48">
                      <InteractivePhoto src={place.image_url || OFFLINE_IMG_PLACEHOLDER} alt={place.name} className="object-cover rounded-t-lg transition-transform duration-300 hover:scale-105" />
                      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/35 via-black/0 to-black/0 rounded-t-lg" />
                      <div className="pointer-events-none absolute bottom-3 left-3 right-3 flex items-center justify-between gap-2">
                        <Badge className="bg-white/90 text-slate-900">{place.category}</Badge>
                        <Badge variant="secondary" className="bg-white/90 text-slate-900">⭐ {place.rating.toFixed(1)}</Badge>
                      </div>
                    </div>
                    <CardHeader>
                      <div className="flex justify-between items-start">
                        <CardTitle className="text-lg">{place.name}</CardTitle>
                      </div>
                      <CardDescription>
                        {place.best_time} • {place.duration} • {place.entry_fee}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <p className="text-sm">{place.description}</p>
                      <div className="space-y-2 text-sm">
                        <div className="flex items-start gap-2">
                          <MapPin className="h-4 w-4 mt-0.5" />
                          <span>{place.location}</span>
                        </div>
                        <p>{place.how_to_reach}</p>
                        <div className="flex justify-between">
                          <span>{place.best_time}</span>
                          <span>{place.entry_fee}</span>
                        </div>
                      </div>
                      {place.tips && (
                        <div className="border p-2 rounded text-sm">
                          <span className="font-semibold">Tip:</span> {place.tips}
                        </div>
                      )}
                      <MiniPlaceMap coordinates={place.coordinates} />
                      {place.coordinates && place.coordinates !== "N/A" && (
                        <p className="text-xs text-muted-foreground">Coordinates: {place.coordinates}</p>
                      )}
                      {place.travel_time_from_start && (
                        <p className="text-xs text-muted-foreground">
                          From {travelPlan.travel_details.starting_point}: {place.travel_time_from_start}
                        </p>
                      )}
                      {place.route_from_start && (
                        <a
                          href={place.route_from_start}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block"
                        >
                          <Button className="w-full" variant="secondary" size="sm">
                            Route from Start Point
                          </Button>
                        </a>
                      )}
                      {place.maps_link ? (
                        <a
                          href={place.maps_link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block"
                        >
                          <Button className="w-full" variant="outline" size="sm">
                            View on Maps
                          </Button>
                        </a>
                      ) : (
                        <p className="text-xs text-muted-foreground text-center">
                          Maps link omitted — offline catalog only.
                        </p>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
              {!filteredPlaces.length && (
                <Card className="mt-4">
                  <CardContent className="p-6 text-center text-sm text-muted-foreground">
                    No places match your filters. Try clearing search/category.
                  </CardContent>
                </Card>
              )}
              {!!travelPlan.nearby_places?.length && (
                <Card className="mb-6">
                  <CardHeader>
                    <CardTitle>Nearby Places for Long Trips</CardTitle>
                    <CardDescription>
                      Extra attractions suggested because your trip duration is longer.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {travelPlan.nearby_places.map((p, i) => (
                        <Card key={`nearby-${i}`}>
                          <div className="relative h-36">
                            <InteractivePhoto src={p.image_url || OFFLINE_IMG_PLACEHOLDER} alt={p.name} className="object-cover rounded-t-lg transition-transform duration-300 hover:scale-105" />
                          </div>
                          <CardContent className="p-4 space-y-2">
                            <p className="font-semibold">{p.name}</p>
                            <p className="text-xs text-muted-foreground">{p.location}</p>
                            {p.maps_link && (
                              <a href={p.maps_link} target="_blank" rel="noopener noreferrer">
                                <Button variant="outline" size="sm" className="w-full">Open Map</Button>
                              </a>
                            )}
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>
            {/* Restaurants Tab */}
            <TabsContent value="restaurants">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {travelPlan.restaurants.map((restaurant, idx) => (
                  <Card key={idx}>
                    <div className="relative h-48">
                      <InteractivePhoto src={restaurant.image_url || OFFLINE_IMG_PLACEHOLDER} alt={restaurant.name} className="object-cover rounded-t-lg transition-transform duration-300 hover:scale-105" />
                    </div>
                    <CardHeader>
                      <div className="flex justify-between items-start">
                        <CardTitle className="text-lg">{restaurant.name}</CardTitle>
                        <Badge>{restaurant.budget_level}</Badge>
                      </div>
                      <CardDescription>
                        {restaurant.cuisine} • Rating: {restaurant.rating}/5.0
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <p className="text-sm">{restaurant.description}</p>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span>Price</span>
                          <span>{restaurant.avg_cost_per_person}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Atmosphere</span>
                          <span>{restaurant.atmosphere}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Best time</span>
                          <span>{restaurant.best_time}</span>
                        </div>
                      </div>
                      <div>
                        <p className="font-semibold text-sm mb-2">Must Try:</p>
                        <div className="flex flex-wrap gap-2">
                          {restaurant.specialties.map((item, i) => (
                            <Badge key={i} variant="secondary">{item}</Badge>
                          ))}
                        </div>
                      </div>
                      {restaurant.reservation_needed && (
                        <p className="text-sm">Reservation recommended</p>
                      )}
                      {restaurant.maps_link ? (
                        <a
                          href={restaurant.maps_link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block"
                        >
                          <Button className="w-full" variant="outline" size="sm">
                            View on Maps
                          </Button>
                        </a>
                      ) : (
                        <p className="text-xs text-muted-foreground text-center">
                          Maps link omitted — offline catalog only.
                        </p>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            {/* Hotels Tab */}
            <TabsContent value="hotels">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {travelPlan.hotels.map((hotel, idx) => (
                  <Card key={idx}>
                    <div className="relative h-48">
                      <InteractivePhoto src={hotel.image_url || OFFLINE_IMG_PLACEHOLDER} alt={hotel.name} className="object-cover rounded-t-lg transition-transform duration-300 hover:scale-105" />
                    </div>
                    <CardHeader>
                      <div className="flex justify-between items-start">
                        <CardTitle className="text-lg">{hotel.name}</CardTitle>
                        <Badge>{hotel.category}</Badge>
                      </div>
                      <CardDescription>
                        Rating: {hotel.rating}/5.0
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <p className="text-sm">{hotel.description}</p>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span>Per Night</span>
                          <span>{hotel.price_per_night}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Total</span>
                          <span className="font-semibold">{hotel.total_estimated}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Room</span>
                          <span>{hotel.room_type}</span>
                        </div>
                        <div className="flex items-start gap-2">
                          <MapPin className="h-4 w-4 mt-0.5" />
                          <span className="text-xs">{hotel.proximity}</span>
                        </div>
                      </div>
                      <div>
                        <p className="font-semibold text-sm mb-2">Amenities:</p>
                        <div className="flex flex-wrap gap-2">
                          {hotel.amenities.slice(0, 6).map((amenity, i) => (
                            <Badge key={i} variant="secondary" className="text-xs">{amenity}</Badge>
                          ))}
                        </div>
                      </div>
                      {hotel.booking_tip && (
                        <div className="border p-2 rounded text-sm">
                          <span className="font-semibold">Tip:</span> {hotel.booking_tip}
                        </div>
                      )}
                      {hotel.maps_link ? (
                        <a
                          href={hotel.maps_link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block"
                        >
                          <Button className="w-full" variant="outline" size="sm">
                            View on Maps
                          </Button>
                        </a>
                      ) : (
                        <p className="text-xs text-muted-foreground text-center">
                          Maps link omitted — offline catalog only.
                        </p>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>
          </Tabs>
          {/* Back Button */}
          <div className="text-center pt-8">
            <Button
              onClick={() => {
                setTravelPlan(null)
                setUserInput('')
              }}
              variant="outline"
            >
              Plan Another Trip
            </Button>
          </div>
        </div>
      )}

      </div>
    </div>
  );
}
