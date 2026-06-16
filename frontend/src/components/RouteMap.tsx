import { useEffect, useMemo, useRef } from "react";
import Map, { Layer, Marker, Source } from "react-map-gl";
import type { MapRef } from "react-map-gl";
import { PlugZap } from "lucide-react";
import "mapbox-gl/dist/mapbox-gl.css";
import { getActiveRoute, getRouteOptions } from "../lib/routeOptions";
import type { CorridorStation, PlanConfig, PlanResult } from "../types";

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string | undefined;

type Props = {
  result: PlanResult | null;
  config: PlanConfig;
  selectedRouteId: number;
};

function legsToGeoJson(legs: { polyline?: [number, number][] }[]) {
  const features = legs
    .filter((leg) => (leg.polyline?.length ?? 0) > 2)
    .map((leg, i) => ({
      type: "Feature" as const,
      properties: { index: i },
      geometry: {
        type: "LineString" as const,
        coordinates: leg.polyline!,
      },
    }));
  return { type: "FeatureCollection" as const, features };
}

export default function RouteMap({ result, config, selectedRouteId }: Props) {
  const mapRef = useRef<MapRef>(null);

  const previewCenter = useMemo(
    () => ({
      lat: (config.origin_lat + config.dest_lat) / 2,
      lon: (config.origin_lon + config.dest_lon) / 2,
    }),
    [config]
  );

  const activeRoute = result ? getActiveRoute(result, selectedRouteId) : null;
  const allOptions = result ? getRouteOptions(result) : [];

  const activeGeoJson = useMemo(
    () => (activeRoute ? legsToGeoJson(activeRoute.legs) : null),
    [activeRoute]
  );

  const altGeoJson = useMemo(() => {
    if (!result) return null;
    const features = allOptions
      .filter((o) => o.id !== selectedRouteId)
      .flatMap((o) =>
        legsToGeoJson(o.legs).features.map((f) => ({
          ...f,
          properties: { ...f.properties, routeId: o.id },
        }))
      );
    return features.length ? { type: "FeatureCollection" as const, features } : null;
  }, [result, allOptions, selectedRouteId]);

  const selectedStopIds = useMemo(
    () => new Set((activeRoute?.stops ?? []).map((s) => String(s.station_id))),
    [activeRoute]
  );

  const corridorStations = useMemo(() => {
    if (!result?.corridor_stations) return [];
    return result.corridor_stations.filter(
      (s) => !selectedStopIds.has(String(s.station_id))
    );
  }, [result, selectedStopIds]);

  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (!map || !activeGeoJson?.features.length) return;

    const coords = activeGeoJson.features.flatMap((f) => f.geometry.coordinates);
    if (coords.length < 2) return;

    let minLon = coords[0][0];
    let maxLon = coords[0][0];
    let minLat = coords[0][1];
    let maxLat = coords[0][1];
    for (const [lon, lat] of coords) {
      minLon = Math.min(minLon, lon);
      maxLon = Math.max(maxLon, lon);
      minLat = Math.min(minLat, lat);
      maxLat = Math.max(maxLat, lat);
    }
    map.fitBounds(
      [
        [minLon, minLat],
        [maxLon, maxLat],
      ],
      { padding: { top: 60, bottom: 60, left: result ? 400 : 60, right: 60 }, duration: 800 }
    );
  }, [activeGeoJson, result]);

  if (!MAPBOX_TOKEN) {
    return (
      <div className="map-fallback">
        <div>
          <p>Add a Mapbox token to enable the map.</p>
          <p className="muted">Set <code>VITE_MAPBOX_TOKEN</code> in <code>frontend/.env</code></p>
        </div>
      </div>
    );
  }

  const origin = result?.ui.origin ?? { lat: config.origin_lat, lon: config.origin_lon };
  const destination = result?.ui.destination ?? { lat: config.dest_lat, lon: config.dest_lon };
  const selectedStops = activeRoute?.stops ?? [];
  const desiredArrival = (result?.trip?.constraints as { desired_arrival_soc_pct?: number } | undefined)
    ?.desired_arrival_soc_pct;

  return (
    <Map
      ref={mapRef}
      mapboxAccessToken={MAPBOX_TOKEN}
      initialViewState={{
        longitude: previewCenter.lon,
        latitude: previewCenter.lat,
        zoom: 7,
      }}
      mapStyle="mapbox://styles/mapbox/light-v11"
      style={{ width: "100%", height: "100%" }}
    >
      {altGeoJson && (
        <Source id="alt-routes" type="geojson" data={altGeoJson}>
          <Layer
            id="alt-route-line"
            type="line"
            paint={{
              "line-color": "#999999",
              "line-width": 2,
              "line-opacity": 0.45,
              "line-dasharray": [2, 2],
            }}
            layout={{ "line-cap": "round", "line-join": "round" }}
          />
        </Source>
      )}

      {activeGeoJson && (
        <Source id="route" type="geojson" data={activeGeoJson}>
          <Layer
            id="route-line"
            type="line"
            paint={{
              "line-color": "#000000",
              "line-width": 4,
              "line-opacity": 0.9,
            }}
            layout={{ "line-cap": "round", "line-join": "round" }}
          />
        </Source>
      )}

      {corridorStations.map((s) => (
        <CorridorMarker key={String(s.station_id)} station={s} />
      ))}

      <Marker longitude={origin.lon} latitude={origin.lat} anchor="bottom">
        <div style={{ textAlign: "center" }}>
          {result && (
            <div className="marker-label" style={{ marginBottom: 4 }}>
              {result.trip.soc_now_pct as number}%
            </div>
          )}
          <div className="marker-dot origin" />
        </div>
      </Marker>

      <Marker longitude={destination.lon} latitude={destination.lat} anchor="bottom">
        <div style={{ textAlign: "center" }}>
          {activeRoute && (
            <div
              className={`marker-label ${desiredArrival != null && (activeRoute.summary.final_soc_pct_est ?? 0) < desiredArrival ? "marker-label-warn" : ""}`}
              style={{ marginBottom: 4 }}
            >
              {activeRoute.summary.final_soc_pct_est}%
            </div>
          )}
          <div className="marker-dot dest" />
        </div>
      </Marker>

      {selectedStops.map((s) => (
        <Marker key={String(s.station_id)} longitude={s.lon as number} latitude={s.lat as number} anchor="bottom">
          <div className="charge-marker charge-marker-selected" title={s.name as string}>
            <PlugZap size={14} strokeWidth={2.25} />
          </div>
        </Marker>
      ))}
    </Map>
  );
}

function CorridorMarker({ station }: { station: CorridorStation }) {
  const title = [station.name, station.max_power_kw ? `${station.max_power_kw} kW` : null]
    .filter(Boolean)
    .join(" · ");

  return (
    <Marker longitude={station.lon} latitude={station.lat} anchor="bottom">
      <div className="charge-marker charge-marker-corridor" title={title}>
        <PlugZap size={12} strokeWidth={2} />
      </div>
    </Marker>
  );
}
