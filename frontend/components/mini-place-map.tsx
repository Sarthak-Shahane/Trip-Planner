"use client";

import { MapContainer, Marker, TileLayer } from "react-leaflet";
import L from "leaflet";

const markerIcon = new L.Icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [20, 32],
  iconAnchor: [10, 32],
});

function parseCoordinates(coordinates?: string): { lat: number; lng: number } | null {
  const c = (coordinates ?? "").trim();
  if (!c || c === "N/A") return null;
  const m = c.match(/(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)/);
  if (!m) return null;
  return { lat: Number(m[1]), lng: Number(m[2]) };
}

export function MiniPlaceMap({ coordinates }: { coordinates?: string }) {
  const parsed = parseCoordinates(coordinates);
  if (!parsed) return null;

  return (
    <div className="overflow-hidden rounded-md border">
      <MapContainer
        center={[parsed.lat, parsed.lng]}
        zoom={13}
        scrollWheelZoom={false}
        dragging={false}
        doubleClickZoom={false}
        touchZoom={false}
        zoomControl={false}
        attributionControl={false}
        style={{ height: 120, width: "100%" }}
      >
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <Marker position={[parsed.lat, parsed.lng]} icon={markerIcon} />
      </MapContainer>
    </div>
  );
}

