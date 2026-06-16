import type { PlanConfig } from "../types";

type ExampleTrip = Pick<
  PlanConfig,
  "origin_lat" | "origin_lon" | "dest_lat" | "dest_lon" | "city" | "cities"
> & { label: string };

const TRIPS: ExampleTrip[] = [
  {
    label: "Taipei → Taichung",
    city: "Taipei",
    cities: ["Taipei", "Taoyuan", "Hsinchu", "Taichung"],
    origin_lat: 25.0171,
    origin_lon: 121.5395,
    dest_lat: 24.1477,
    dest_lon: 120.6736,
  },
  {
    label: "Taipei → Kaohsiung",
    city: "Taipei",
    cities: ["Taipei", "Taoyuan", "Taichung", "Tainan", "Kaohsiung"],
    origin_lat: 25.0171,
    origin_lon: 121.5395,
    dest_lat: 22.6273,
    dest_lon: 120.3014,
  },
  {
    label: "Taipei → Pingtung",
    city: "Taipei",
    cities: ["Taipei", "Taoyuan", "Taichung", "Kaohsiung", "Pingtung"],
    origin_lat: 25.0171,
    origin_lon: 121.5395,
    dest_lat: 22.0552,
    dest_lon: 120.7478,
  },
  {
    label: "Hsinchu → Tainan",
    city: "Hsinchu",
    cities: ["Hsinchu", "Miaoli", "Taichung", "Changhua", "Tainan"],
    origin_lat: 24.8138,
    origin_lon: 120.9675,
    dest_lat: 22.9997,
    dest_lon: 120.227,
  },
  {
    label: "Taichung → Hualien",
    city: "Taichung",
    cities: ["Taichung", "Nantou", "Hualien"],
    origin_lat: 24.1477,
    origin_lon: 120.6736,
    dest_lat: 23.9871,
    dest_lon: 121.6015,
  },
  {
    label: "Kaohsiung → Taitung",
    city: "Kaohsiung",
    cities: ["Kaohsiung", "Pingtung", "Taitung"],
    origin_lat: 22.6273,
    origin_lon: 120.3014,
    dest_lat: 22.7583,
    dest_lon: 121.1444,
  },
];

const BATTERIES = [48, 55, 60, 75, 82];
const CONNECTORS = ["CCS2", "CCS1", "CHAdeMO", "TYPE2"];
const CONSUMPTION = [0.15, 0.16, 0.18, 0.2, 0.22];

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function randInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

export function randomExample(current: PlanConfig): { config: PlanConfig; label: string } {
  const trip = pick(TRIPS);
  const battery = pick(BATTERIES);
  const socNow = randInt(55, 95);
  const reserve = randInt(8, 15);
  const arrival = randInt(8, 20);

  return {
    label: trip.label,
    config: {
      ...current,
      mode: Math.random() > 0.3 ? "tdx" : "sample",
      city: trip.city,
      cities: trip.cities,
      origin_lat: trip.origin_lat,
      origin_lon: trip.origin_lon,
      dest_lat: trip.dest_lat,
      dest_lon: trip.dest_lon,
      battery_kwh: battery,
      soc_now_pct: socNow,
      reserve_soc_pct: reserve,
      desired_arrival_soc_pct: arrival,
      consumption_kwh_per_km: pick(CONSUMPTION),
      vehicle_connector: pick(CONNECTORS),
      use_osm: true,
      use_traffic: Math.random() > 0.2,
    },
  };
}
