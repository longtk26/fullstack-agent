import type { TBreakdownDimension, TBreakdownRow, TUsageReport } from "../types";

/** Rows for the "where it goes" chart: one bar per engine / model / node / lane. Nodes use per-generation
 * averages, so the most expensive or slowest node stands out regardless of how often it ran. */
export function breakdownRows(report: TUsageReport, dimension: TBreakdownDimension): TBreakdownRow[] {
  switch (dimension) {
    case "engine":
      return report.byEngine.map((row) => ({
        label: row.engine,
        cost: row.cost.total,
        estimated: row.cost.estimated > 0,
        timeMs: row.wallMs,
        modelCalls: row.modelCalls,
      }));
    case "model":
      return report.byModel.map((row) => ({
        label: row.model,
        cost: row.cost.total,
        estimated: row.cost.estimated > 0,
        timeMs: null,
        modelCalls: row.modelCalls,
      }));
    case "node":
      return report.byNode.map((row) => ({
        label: row.node,
        cost: row.avgCost,
        estimated: row.cost.estimated > 0,
        timeMs: row.avgDurationMs,
        modelCalls: row.modelCalls,
      }));
    case "lane":
      return report.byLane.map((row) => ({
        label: row.lane,
        cost: row.cost.total,
        estimated: row.cost.estimated > 0,
        timeMs: row.wallMs,
        modelCalls: row.modelCalls,
      }));
  }
}

/** Generations per number of repair attempts (0, 1, 2, 3+). */
export function repairHistogram(report: TUsageReport): { attempts: string; generations: number }[] {
  const buckets = [0, 0, 0, 0];
  for (const row of report.generations) buckets[Math.min(row.repairAttempts, 3)] += 1;
  return buckets.map((generations, attempts) => ({ attempts: attempts === 3 ? "3+" : String(attempts), generations }));
}

export function isoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}
