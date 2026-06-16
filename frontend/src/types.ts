export type PlanConfig = {
  mode: "sample" | "tdx";
  city: string;
  cities?: string[];
  origin_lat: number;
  origin_lon: number;
  dest_lat: number;
  dest_lon: number;
  battery_kwh: number;
  soc_now_pct: number;
  reserve_soc_pct: number;
  desired_arrival_soc_pct: number;
  consumption_kwh_per_km: number;
  vehicle_connector: string;
  avg_speed_kmh: number;
  traffic_index: number;
  charge_efficiency: number;
  min_drive_before_charge_km: number;
  max_stops: number;
  use_osm: boolean;
  use_traffic: boolean;
};

export type UiStep = {
  type: "depart" | "drive" | "charge" | "arrive";
  title: string;
  subtitle?: string;
  duration_min?: number;
  soc_pct?: number;
  soc_start_pct?: number;
  soc_end_pct?: number;
  wait_min?: number;
  charge_min?: number;
  available_connectors?: number;
  lat?: number;
  lon?: number;
  traffic_factor?: number;
};

export type RouteLeg = {
  from: string;
  to: string;
  distance_km_est: number;
  drive_minutes_est: number;
  polyline: [number, number][];
  soc_start_pct?: number;
  soc_end_pct?: number;
  traffic_factor?: number;
};

export type RoutePlan = {
  total_time_minutes_est?: number;
  final_soc_pct_est?: number;
  stops: Array<Record<string, unknown>>;
  legs: RouteLeg[];
  charging_events?: Array<Record<string, unknown>>;
  error?: string;
};

export type RouteSummary = {
  total_time_minutes_est?: number;
  total_time_label: string;
  drive_time_label: string;
  charge_time_label: string;
  distance_km_est: number;
  stop_count: number;
  final_soc_pct_est?: number;
  needs_charge_stop?: boolean;
};

export type RouteOption = {
  id: number;
  label: string;
  is_best: boolean;
  summary: RouteSummary;
  steps: UiStep[];
  stops: Array<Record<string, unknown>>;
  legs: RouteLeg[];
};

export type CorridorStation = {
  station_id: string;
  name: string;
  lat: number;
  lon: number;
  max_power_kw?: number;
  connector_types?: string[];
};

export type PlanResult = {
  trip: Record<string, unknown>;
  route_plan: RoutePlan;
  alternatives?: RoutePlan[];
  corridor_stations?: CorridorStation[];
  ui: {
    summary: RouteSummary;
    steps: UiStep[];
    alternatives: Array<{
      total_time_label: string;
      stops: string[];
      final_soc_pct_est?: number;
    }>;
    route_options?: RouteOption[];
    origin: { lat: number; lon: number };
    destination: { lat: number; lon: number };
  };
  meta: {
    data_source: string;
    traffic_enabled?: boolean;
    traffic?: { sensor_count: number };
  };
  error?: string;
};
