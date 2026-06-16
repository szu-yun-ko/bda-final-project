import type { PlanResult, RouteOption, RoutePlan, UiStep } from "../types";

function stepsFromPlan(trip: Record<string, unknown>, plan: RoutePlan): UiStep[] {
  const legs = plan.legs ?? [];
  const charging = plan.charging_events ?? [];
  const stops = plan.stops ?? [];

  const steps: UiStep[] = [
    {
      type: "depart",
      title: "Depart",
      subtitle: "Origin",
      soc_pct: trip.soc_now_pct as number | undefined,
      duration_min: 0,
    },
  ];

  let chargeIdx = 0;
  for (const leg of legs) {
    steps.push({
      type: "drive",
      title: `Drive ${leg.distance_km_est} km`,
      subtitle: `${leg.from} → ${leg.to}`,
      duration_min: leg.drive_minutes_est,
      soc_start_pct: leg.soc_start_pct,
      soc_end_pct: leg.soc_end_pct,
      traffic_factor: leg.traffic_factor,
    });
    if (leg.to !== "destination" && chargeIdx < charging.length) {
      const ev = charging[chargeIdx];
      const stop = stops[chargeIdx] ?? {};
      steps.push({
        type: "charge",
        title: (stop.name as string) || (ev.station_name as string),
        subtitle: `${ev.energy_added_kwh_est} kWh · ${stop.max_power_kw} kW`,
        duration_min: ((ev.wait_minutes_est as number) || 0) + ((ev.charge_minutes_est as number) || 0),
        wait_min: ev.wait_minutes_est as number | undefined,
        charge_min: ev.charge_minutes_est as number | undefined,
        available_connectors: ev.available_connectors as number | undefined,
        lat: stop.lat as number | undefined,
        lon: stop.lon as number | undefined,
      });
      chargeIdx += 1;
    }
  }

  steps.push({
    type: "arrive",
    title: "Arrive",
    subtitle: "Destination",
    soc_pct: plan.final_soc_pct_est,
    duration_min: 0,
  });

  return steps;
}

function summaryFromPlan(trip: Record<string, unknown>, plan: RoutePlan): RouteOption["summary"] {
  const legs = plan.legs ?? [];
  const charging = plan.charging_events ?? [];
  const driveMin = legs.reduce((s, l) => s + (l.drive_minutes_est || 0), 0);
  const waitMin = charging.reduce((s, e) => s + ((e.wait_minutes_est as number) || 0), 0);
  const chargeMin = charging.reduce((s, e) => s + ((e.charge_minutes_est as number) || 0), 0);
  const distance = legs.reduce((s, l) => s + (l.distance_km_est || 0), 0);
  const total = plan.total_time_minutes_est;
  const fmt = (m: number) => {
    const t = Math.round(m);
    const h = Math.floor(t / 60);
    const min = t % 60;
    return h ? `${h} h ${min} min` : `${min} min`;
  };

  return {
    total_time_minutes_est: total,
    total_time_label: total != null ? fmt(total) : "-",
    drive_time_label: fmt(driveMin),
    charge_time_label: fmt(waitMin + chargeMin),
    distance_km_est: Math.round(distance * 10) / 10,
    stop_count: plan.stops?.length ?? 0,
    final_soc_pct_est: plan.final_soc_pct_est,
    needs_charge_stop: trip.needs_charge_stop as boolean | undefined,
  };
}

export function getRouteOptions(result: PlanResult): RouteOption[] {
  if (result.ui.route_options?.length) {
    return result.ui.route_options;
  }

  const trip = result.trip;
  const primary: RouteOption = {
    id: 0,
    label: "Recommended",
    is_best: true,
    summary: result.ui.summary,
    steps: result.ui.steps,
    stops: result.route_plan.stops,
    legs: result.route_plan.legs,
  };

  const alts = (result.alternatives ?? []).map((alt, i) => ({
    id: i + 1,
    label: `Option ${i + 2}`,
    is_best: false,
    summary: summaryFromPlan(trip, alt),
    steps: stepsFromPlan(trip, alt),
    stops: alt.stops,
    legs: alt.legs,
  }));

  return [primary, ...alts];
}

export function getActiveRoute(result: PlanResult, routeId: number): RouteOption {
  const options = getRouteOptions(result);
  return options.find((o) => o.id === routeId) ?? options[0];
}
