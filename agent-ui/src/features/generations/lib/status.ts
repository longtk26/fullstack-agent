import type { TGenerationStatus } from "../types";

export const GENERATION_STATUSES: TGenerationStatus[] = [
  "DRAFTING",
  "NEEDS_REVIEW",
  "PENDING",
  "RUNNING",
  "VALIDATING",
  "REPAIRING",
  "COMPLETED",
  "COMPLETED_WITH_WARNINGS",
  "FAILED",
  "CANCELLED",
];

const TERMINAL: ReadonlySet<string> = new Set(["COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED", "CANCELLED"]);

export function isSucceeded(status: string | null | undefined): boolean {
  return status === "COMPLETED" || status === "COMPLETED_WITH_WARNINGS";
}

export function isTerminal(status: string | null | undefined): boolean {
  return status != null && TERMINAL.has(status);
}


export function formatStep(step: string | null | undefined): string {
  return step ? step.replaceAll("_", " ") : "—";
}

export { elapsedMs, formatDuration } from "@/lib/format-duration";
