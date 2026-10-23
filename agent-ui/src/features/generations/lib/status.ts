import type { TGenerationStatus } from "../types";

export const GENERATION_STATUSES: TGenerationStatus[] = [
  "PENDING",
  "RUNNING",
  "VALIDATING",
  "REPAIRING",
  "COMPLETED",
  "FAILED",
  "CANCELLED",
];

const TERMINAL: ReadonlySet<string> = new Set(["COMPLETED", "FAILED", "CANCELLED"]);

export function isTerminal(status: string | null | undefined): boolean {
  return status != null && TERMINAL.has(status);
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.max(0, Math.round(ms))} ms`;
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

export function elapsedMs(startedAt: string | null, finishedAt: string | null, now: number): number | null {
  if (!startedAt) return null;
  const end = finishedAt ? Date.parse(finishedAt) : now;
  return end - Date.parse(startedAt);
}

export function formatStep(step: string | null | undefined): string {
  return step ? step.replaceAll("_", " ") : "—";
}
