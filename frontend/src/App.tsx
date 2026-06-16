import { useState } from "react";
import { planRoute } from "./api";
import ResultsPanel from "./components/ResultsPanel";
import RouteMap from "./components/RouteMap";
import TripStep from "./components/TripStep";
import VehicleStep from "./components/VehicleStep";
import type { PlanConfig, PlanResult } from "./types";
import "./App.css";

type Step = "trip" | "vehicle" | "results";

const DEFAULT_CONFIG: PlanConfig = {
  mode: "tdx",
  city: "Taipei",
  cities: ["Taipei", "Taoyuan", "Hsinchu", "Taichung"],
  origin_lat: 25.0171,
  origin_lon: 121.5395,
  dest_lat: 24.1477,
  dest_lon: 120.6736,
  battery_kwh: 60,
  soc_now_pct: 90,
  reserve_soc_pct: 10,
  desired_arrival_soc_pct: 10,
  consumption_kwh_per_km: 0.18,
  vehicle_connector: "CCS2",
  avg_speed_kmh: 55,
  traffic_index: 0.9,
  charge_efficiency: 0.9,
  min_drive_before_charge_km: 25,
  max_stops: 2,
  use_osm: true,
  use_traffic: true,
};

export default function App() {
  const [step, setStep] = useState<Step>("trip");
  const [config, setConfig] = useState<PlanConfig>(DEFAULT_CONFIG);
  const [result, setResult] = useState<PlanResult | null>(null);
  const [selectedRouteId, setSelectedRouteId] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePlan = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await planRoute(config);
      setResult(data);
      setSelectedRouteId(0);
      setStep("results");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <div className="map-wrap">
        <RouteMap result={result} config={config} selectedRouteId={selectedRouteId} />
      </div>

      <div className={`panel ${step === "results" ? "panel-results" : "panel-config"}`}>
        {step === "trip" && (
          <>
            <div className="panel-header" style={{ padding: "20px 20px 0" }}>
              <h1>EV Route</h1>
              <span className="muted">Taiwan</span>
            </div>
            <TripStep config={config} onChange={setConfig} onNext={() => setStep("vehicle")} />
          </>
        )}
        {step === "vehicle" && (
          <>
            <div className="panel-header" style={{ padding: "20px 20px 0" }}>
              <h1>EV Route</h1>
              <span className="muted">Taiwan</span>
            </div>
            <VehicleStep
              config={config}
              loading={loading}
              onChange={setConfig}
              onBack={() => setStep("trip")}
              onPlan={handlePlan}
            />
            {error && <div className="error" style={{ margin: "0 20px 20px" }}>{error}</div>}
          </>
        )}
        {step === "results" && result && (
          <ResultsPanel
            result={result}
            selectedRouteId={selectedRouteId}
            onSelectRoute={setSelectedRouteId}
            onEdit={() => setStep("trip")}
          />
        )}
      </div>
    </div>
  );
}
