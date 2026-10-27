import type { TCostSplit } from "@/types/usage";

const compact = new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 });

export function formatTokens(value: number | null | undefined): string {
  return value == null ? "—" : compact.format(value);
}

export function formatUsd(value: number | null | undefined): string {
  if (value == null) return "—";
  if (value === 0) return "$0";
  if (value < 0.01) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(value < 10 ? 2 : 0)}`;
}

/** "$1.20 + ~$0.31 est." — estimated cost is always labelled as such (Story 8.4). */
export function formatCostSplit(cost: TCostSplit | null | undefined): string {
  if (!cost) return "—";
  if (!cost.estimated) return formatUsd(cost.reported);
  if (!cost.reported) return `~${formatUsd(cost.estimated)} est.`;
  return `${formatUsd(cost.reported)} + ~${formatUsd(cost.estimated)} est.`;
}

export function formatPercent(part: number, whole: number): string {
  return whole > 0 ? `${Math.round((part / whole) * 100)}%` : "—";
}
