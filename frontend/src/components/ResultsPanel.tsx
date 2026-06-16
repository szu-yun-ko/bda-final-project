import { Car, ChevronLeft, Flag, MapPin, Zap } from "lucide-react";
import { getRouteOptions } from "../lib/routeOptions";
import type { PlanResult, RouteOption, UiStep } from "../types";

type Props = {
  result: PlanResult;
  selectedRouteId: number;
  onSelectRoute: (id: number) => void;
  onEdit: () => void;
};

function StepIcon({ type }: { type: UiStep["type"] }) {
  const size = 16;
  if (type === "drive") return <Car size={size} />;
  if (type === "charge") return <Zap size={size} />;
  if (type === "depart") return <MapPin size={size} />;
  return <Flag size={size} />;
}

function RouteCard({
  option,
  selected,
  fastest,
  onSelect,
}: {
  option: RouteOption;
  selected: boolean;
  fastest: boolean;
  onSelect: () => void;
}) {
  const { summary } = option;
  const stopLabel =
    summary.stop_count === 0
      ? "No stops"
      : `${summary.stop_count} stop${summary.stop_count === 1 ? "" : "s"}`;

  return (
    <button
      type="button"
      className={`route-card ${selected ? "route-card-active" : ""}`}
      onClick={onSelect}
    >
      <div className="route-card-top">
        <span className="route-card-label">{option.label}</span>
        {fastest && <span className="route-badge">Fastest</span>}
      </div>
      <div className="route-card-time">{summary.total_time_label}</div>
      <div className="route-card-meta">
        <span>{stopLabel}</span>
        <span>{summary.distance_km_est} km</span>
        <span>{summary.final_soc_pct_est?.toFixed?.(0) ?? summary.final_soc_pct_est}% at arrival</span>
      </div>
      {option.stops.length > 0 && (
        <div className="route-card-stops muted">
          via {option.stops.map((s) => s.name as string).join(", ")}
        </div>
      )}
    </button>
  );
}

export default function ResultsPanel({ result, selectedRouteId, onSelectRoute, onEdit }: Props) {
  const planError = result.route_plan.error;
  const options = getRouteOptions(result);
  const active = options.find((o) => o.id === selectedRouteId) ?? options[0];
  const fastestId = options.reduce((best, o) =>
    (o.summary.total_time_minutes_est ?? Infinity) < (best.summary.total_time_minutes_est ?? Infinity) ? o : best
  ).id;

  return (
    <div className="panel-inner">
      <div className="panel-header">
        <h1>Your route</h1>
        <button type="button" className="btn-ghost" onClick={onEdit}>
          <ChevronLeft size={14} />
          Edit
        </button>
      </div>

      {planError && (
        <>
          <div className="error" style={{ marginBottom: 16 }}>{planError}</div>
          {(result.corridor_stations?.length ?? 0) > 0 && (
            <p className="muted" style={{ marginBottom: 16 }}>
              Gray markers on the map show {result.corridor_stations!.length} charging stations along your corridor.
            </p>
          )}
        </>
      )}

      {!planError && options.length > 1 && (
        <div className="route-compare">
          <div className="route-compare-title">Compare routes</div>
          {options.map((opt) => (
            <RouteCard
              key={opt.id}
              option={opt}
              selected={opt.id === active.id}
              fastest={opt.id === fastestId}
              onSelect={() => onSelectRoute(opt.id)}
            />
          ))}
        </div>
      )}

      {!planError && (
      <>
      <div className="summary-top">
        <div className="total-time">{active.summary.total_time_label}</div>
        {(() => {
          const target = (result.trip.constraints as { desired_arrival_soc_pct?: number } | undefined)
            ?.desired_arrival_soc_pct;
          const actual = active.summary.final_soc_pct_est;
          if (target != null && actual != null && actual < target - 0.5) {
            return (
              <p className="soc-warning">
                Arrival SOC ({actual}%) is below your {target}% target. No feasible route met all constraints — try CCS2 or allow more stops.
              </p>
            );
          }
          return null;
        })()}
        <div className="summary-stats">
          <span className="stat"><Car size={14} /> {active.summary.drive_time_label}</span>
          <span className="stat"><Zap size={14} /> {active.summary.charge_time_label}</span>
          <span>{active.summary.distance_km_est} km</span>
          <span>{active.summary.stop_count} stop{active.summary.stop_count === 1 ? "" : "s"}</span>
        </div>
        <p className="muted" style={{ marginTop: 8 }}>
          {result.meta.data_source}
          {result.meta.traffic?.sensor_count ? ` · ${result.meta.traffic.sensor_count} sensors` : ""}
        </p>
      </div>

      <ol className="steps">
        {active.steps.map((step, i) => (
          <li key={i} className="step">
            <div className="step-icon">
              <StepIcon type={step.type} />
            </div>
            <div>
              <div className="step-title">{step.title}</div>
              {step.subtitle && <div className="step-sub">{step.subtitle}</div>}
              <div className="step-meta">
                {step.duration_min ? <span>{Math.round(step.duration_min)} min</span> : null}
                {step.soc_pct != null && <span>{step.soc_pct}% SOC</span>}
                {step.soc_end_pct != null && <span>to {step.soc_end_pct}%</span>}
              </div>
            </div>
          </li>
        ))}
      </ol>
      </>
      )}
    </div>
  );
}
