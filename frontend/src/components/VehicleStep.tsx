import { ChevronLeft } from "lucide-react";
import { FieldLabel } from "./InfoTip";
import type { PlanConfig } from "../types";

const TERMS = {
  battery: "Total battery capacity in kilowatt-hours (kWh). Larger packs can drive farther between charges.",
  socNow: "State of Charge (SOC) — your current battery level as a percentage.",
  reserveSoc: "Minimum SOC you want to keep while driving. The planner avoids dropping below this between stops.",
  arrivalSoc: "Target battery level when you reach the destination.",
  connector: "Charging plug type your car accepts, e.g. CCS2 or CHAdeMO.",
  consumption: "Energy used per kilometer (kWh/km). Lower values mean better efficiency.",
  traffic: "Uses TDX live freeway and city traffic data to adjust drive-time estimates.",
  osrm: "Snaps the route to real roads using OSRM instead of straight-line distance.",
};

type Props = {
  config: PlanConfig;
  loading: boolean;
  onChange: (c: PlanConfig) => void;
  onBack: () => void;
  onPlan: () => void;
};

export default function VehicleStep({ config, loading, onChange, onBack, onPlan }: Props) {
  const set = <K extends keyof PlanConfig>(key: K, value: PlanConfig[K]) =>
    onChange({ ...config, [key]: value });

  return (
    <div className="panel-inner">
      <div className="stepper">
        <span>1. Trip</span>
        <span className="active">2. Vehicle</span>
      </div>

      <div className="grid2">
        <div className="field">
          <label><FieldLabel info={TERMS.battery}>Battery (kWh)</FieldLabel></label>
          <input type="number" value={config.battery_kwh} onChange={(e) => set("battery_kwh", +e.target.value)} />
        </div>
        <div className="field">
          <label><FieldLabel info={TERMS.socNow}>SOC now (%)</FieldLabel></label>
          <input type="number" value={config.soc_now_pct} onChange={(e) => set("soc_now_pct", +e.target.value)} />
        </div>
        <div className="field">
          <label><FieldLabel info={TERMS.reserveSoc}>Reserve SOC (%)</FieldLabel></label>
          <input type="number" value={config.reserve_soc_pct} onChange={(e) => set("reserve_soc_pct", +e.target.value)} />
        </div>
        <div className="field">
          <label><FieldLabel info={TERMS.arrivalSoc}>Arrival SOC (%)</FieldLabel></label>
          <input type="number" value={config.desired_arrival_soc_pct} onChange={(e) => set("desired_arrival_soc_pct", +e.target.value)} />
        </div>
        <div className="field">
          <label><FieldLabel info={TERMS.connector}>Connector</FieldLabel></label>
          <input value={config.vehicle_connector} onChange={(e) => set("vehicle_connector", e.target.value)} />
        </div>
        <div className="field">
          <label><FieldLabel info={TERMS.consumption}>Consumption (kWh/km)</FieldLabel></label>
          <input type="number" step="0.01" value={config.consumption_kwh_per_km} onChange={(e) => set("consumption_kwh_per_km", +e.target.value)} />
        </div>
      </div>

      <label className="check-row">
        <input type="checkbox" checked={config.use_traffic} onChange={(e) => set("use_traffic", e.target.checked)} />
        <FieldLabel info={TERMS.traffic}>TDX traffic for ETA</FieldLabel>
      </label>
      <label className="check-row">
        <input type="checkbox" checked={config.use_osm} onChange={(e) => set("use_osm", e.target.checked)} />
        <FieldLabel info={TERMS.osrm}>Road-following route (OSRM)</FieldLabel>
      </label>

      <div className="actions">
        <button type="button" className="btn btn-secondary" onClick={onBack}>
          <ChevronLeft size={16} style={{ verticalAlign: "middle", marginRight: 4 }} />
          Back
        </button>
        <button type="button" className="btn btn-primary" onClick={onPlan} disabled={loading}>
          {loading ? "Planning..." : "Plan route"}
        </button>
      </div>
    </div>
  );
}
