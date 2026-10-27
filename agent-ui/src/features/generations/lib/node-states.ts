import type { TGenerationEvent, TGenerationStatus } from "../types";
import { isSucceeded, isTerminal } from "./status";

export type TNodeState = "pending" | "running" | "passed" | "failed" | "skipped" | "cancelled";

export type TNodeProgress = {
  state: TNodeState;
  attempts: number;
};

export const START_NODE = "__start__";
export const END_NODE = "__end__";
export const REPAIR_NODE = "repair_code";
export const VALIDATION_NODE = "run_validation";

const FINISHED_STATE: Record<string, TNodeState> = {
  succeeded: "passed",
  failed: "failed",
  skipped: "skipped",
  cancelled: "cancelled",
};

/** Replays step events into the current state of every workflow node. */
export function deriveNodeStates(
  events: TGenerationEvent[],
  jobStatus: TGenerationStatus | undefined,
): Record<string, TNodeProgress> {
  const progress: Record<string, TNodeProgress> = {};
  for (const event of events) {
    if (!event.step) continue;
    const current = progress[event.step] ?? { state: "pending", attempts: 0 };
    if (event.type === "step.started") {
      const attempt = typeof event.payload.attempt === "number" ? event.payload.attempt : current.attempts + 1;
      progress[event.step] = { state: "running", attempts: Math.max(current.attempts, attempt) };
    } else if (event.type === "step.finished") {
      progress[event.step] = { ...current, state: FINISHED_STATE[event.status ?? ""] ?? "passed" };
    }
  }

  const terminal = isTerminal(jobStatus);
  if (terminal) {
    for (const node of Object.values(progress)) {
      if (node.state === "running") node.state = jobStatus === "CANCELLED" ? "cancelled" : "failed";
    }
  }
  if (events.length > 0 || (jobStatus && jobStatus !== "PENDING")) {
    progress[START_NODE] = { state: "passed", attempts: 1 };
  }
  if (terminal) {
    progress[END_NODE] = {
      state: isSucceeded(jobStatus) ? "passed" : jobStatus === "CANCELLED" ? "cancelled" : "failed",
      attempts: 1,
    };
  }
  return progress;
}
