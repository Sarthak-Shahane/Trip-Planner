"use client";

import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import type { LatLngExpression } from "leaflet";

type PlaceForMap = {
  name: string;
  location?: string;
  maps_link?: string;
  coordinates?: string;
  lat?: number;
  lng?: number;
};

const markerIcon = new L.Icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

function parseCoords(p: PlaceForMap): { lat: number; lng: number } | null {
  if (typeof p.lat === "number" && typeof p.lng === "number") return { lat: p.lat, lng: p.lng };
  const c = (p.coordinates ?? "").trim();
  if (!c || c === "N/A") return null;
  const m = c.match(/(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)/);
  if (!m) return null;
  return { lat: Number(m[1]), lng: Number(m[2]) };
}

function FitBounds({ points }: { points: LatLngExpression[] }) {
  const map = useMap();
  useEffect(() => {
    if (!points.length) return;
    if (points.length === 1) {
      map.setView(points[0], 13);
      return;
    }
    const b = L.latLngBounds(points);
    map.fitBounds(b, { padding: [24, 24] });
  }, [map, points]);
  return null;
}

export function PlacesMap({ places, className }: { places: PlaceForMap[]; className?: string }) {
  const points: { p: PlaceForMap; lat: number; lng: number }[] = [];
  for (const p of places) {
    const c = parseCoords(p);
    if (c) points.push({ p, ...c });
  }

  const center: LatLngExpression = points.length ? [points[0].lat, points[0].lng] : [20.5937, 78.9629]; // India default

  return (
    <div className={className}>
      <MapContainer
        center={center}
        zoom={points.length ? 12 : 4}
        scrollWheelZoom
        style={{ height: 420, width: "100%", borderRadius: 12 }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds points={points.map((x) => [x.lat, x.lng])} />
        {points.map(({ p, lat, lng }) => (
          <Marker key={`${p.name}-${lat}-${lng}`} position={[lat, lng]} icon={markerIcon}>
            <Popup>
              <div className="space-y-1">
                <div className="font-semibold">{p.name}</div>
                {p.location && <div className="text-xs text-muted-foreground">{p.location}</div>}
                {p.maps_link && (
                  <a className="text-xs underline" href={p.maps_link} target="_blank" rel="noreferrer">
                    Open in Maps
                  </a>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      {!points.length && (
        <p className="mt-3 text-sm text-muted-foreground">
          No coordinates available for this destination yet. Use “View on Maps” links in the cards.
        </p>
      )}
    </div>
  );
}

