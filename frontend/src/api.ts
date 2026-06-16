import type { PlanConfig, PlanResult } from "./types";

export async function planRoute(config: PlanConfig): Promise<PlanResult> {
  const res = await fetch("/api/plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "Failed to plan route");
  }
  return data as PlanResult;
}
