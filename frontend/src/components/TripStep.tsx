import { useState } from "react";
import { Dices, MapPin, Navigation } from "lucide-react";
import { FieldLabel } from "./InfoTip";
import { randomExample } from "../lib/randomExample";
import type { PlanConfig } from "../types";

const TERMS = {
  dataSource: "TDX is Taiwan's transport data platform. Sample mode uses bundled demo data.",
  city: "Primary city used to load nearby charging stations along the route.",
  origin: "Starting point as latitude and longitude.",
  destination: "End point as latitude and longitude.",
};

type Props = {
  config: PlanConfig;
  onChange: (c: PlanConfig) => void;
  onNext: () => void;
};

export default function TripStep({ config, onChange, onNext }: Props) {
  const [exampleLabel, setExampleLabel] = useState<string | null>(null);

  const set = <K extends keyof PlanConfig>(key: K, value: PlanConfig[K]) =>
    onChange({ ...config, [key]: value });

  const loadExample = () => {
    const { config: next, label } = randomExample(config);
    onChange(next);
    setExampleLabel(label);
  };

  return (
    <div className="panel-inner">
      <div className="stepper">
        <span className="active">1. Trip</span>
        <span>2. Vehicle</span>
      </div>

      <button type="button" className="example-btn" onClick={loadExample}>
        <Dices size={14} />
        Try a random example
      </button>
      {exampleLabel && (
        <p className="example-hint muted">Loaded: {exampleLabel}</p>
      )}

      <div className="field">
        <label><FieldLabel info={TERMS.dataSource}>Data source</FieldLabel></label>
        <select value={config.mode} onChange={(e) => set("mode", e.target.value as PlanConfig["mode"])}>
          <option value="tdx">TDX live data</option>
          <option value="sample">Sample data</option>
        </select>
      </div>

      <div className="field">
        <label><FieldLabel info={TERMS.city}>City</FieldLabel></label>
        <input value={config.city} onChange={(e) => set("city", e.target.value)} />
      </div>

      <div className="field">
        <label>
          <FieldLabel info={TERMS.origin}>
            <MapPin size={12} style={{ display: "inline", verticalAlign: "middle", marginRight: 4 }} />
            Origin
          </FieldLabel>
        </label>
        <div className="grid2">
          <input type="number" step="0.0001" value={config.origin_lat} onChange={(e) => set("origin_lat", +e.target.value)} placeholder="Lat" />
          <input type="number" step="0.0001" value={config.origin_lon} onChange={(e) => set("origin_lon", +e.target.value)} placeholder="Lon" />
        </div>
      </div>

      <div className="field">
        <label>
          <FieldLabel info={TERMS.destination}>
            <Navigation size={12} style={{ display: "inline", verticalAlign: "middle", marginRight: 4 }} />
            Destination
          </FieldLabel>
        </label>
        <div className="grid2">
          <input type="number" step="0.0001" value={config.dest_lat} onChange={(e) => set("dest_lat", +e.target.value)} placeholder="Lat" />
          <input type="number" step="0.0001" value={config.dest_lon} onChange={(e) => set("dest_lon", +e.target.value)} placeholder="Lon" />
        </div>
      </div>

      <div className="actions">
        <button type="button" className="btn btn-primary" onClick={onNext}>
          Next
        </button>
      </div>
    </div>
  );
}
