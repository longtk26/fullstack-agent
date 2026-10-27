import { Activity, Ban, Bot, CirclePlay, FileCheck, FileJson, Flag, Layers, RotateCcw, ShieldCheck, Terminal, TriangleAlert } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { TGenerationEvent } from "../types";
import { formatDuration, formatStep } from "./status";

export type TEventCategory = "status" | "step" | "engine" | "validation" | "job";

export const EVENT_CATEGORIES: { value: TEventCategory | "all"; label: string }[] = [
  { value: "all", label: "All events" },
  { value: "status", label: "Status" },
  { value: "step", label: "Steps" },
  { value: "engine", label: "Engine" },
  { value: "validation", label: "Validation" },
  { value: "job", label: "Job" },
];

export function eventCategory(event: TGenerationEvent): TEventCategory {
  if (event.type === "status.changed" || event.type === "lane.changed") return "status";
  if (event.type.startsWith("step.")) return "step";
  if (event.type.startsWith("engine.")) return "engine";
  if (event.type.startsWith("validation.")) return "validation";
  return "job";
}

export const EVENT_ICONS: Record<string, LucideIcon> = {
  "status.changed": Flag,
  "job.started": CirclePlay,
  "job.resumed": RotateCcw,
  "step.started": Activity,
  "step.finished": Activity,
  "engine.started": Bot,
  "engine.event": Terminal,
  "engine.finished": Bot,
  "engine.retry": TriangleAlert,
  "cancel.requested": Ban,
  "validation.check": ShieldCheck,
  "lane.changed": Layers,
  "inputs.valid": FileCheck,
  "spec.invalid": TriangleAlert,
  "contract.ready": FileJson,
};

function text(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

function num(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}

/** One human-readable line per event for the log. */
export function describeEvent(event: TGenerationEvent): string {
  const p = event.payload;
  const step = formatStep(event.step);
  switch (event.type) {
    case "status.changed": {
      const reason = [text(p.errorCode), text(p.errorSummary)].filter(Boolean).join(": ");
      return `Status → ${event.status ?? "?"}${reason ? ` (${reason})` : ""}`;
    }
    case "job.started":
      return `Job started on ${text(p.engine) ?? "engine"}`;
    case "job.resumed":
      return `Resumed after a worker loss (resume #${num(p.resumeCount) ?? "?"})`;
    case "step.started":
      return `${step} started${num(p.attempt) && num(p.attempt)! > 1 ? ` (attempt ${p.attempt})` : ""}`;
    case "step.finished": {
      const error = text(p.error);
      return `${step} ${event.status ?? "finished"}${error ? `: ${error}` : ""}`;
    }
    case "engine.started":
      return `${text(p.engine) ?? "engine"} · ${text(p.purpose) ?? "run"} started`;
    case "engine.event":
      return [text(p.kind), text(p.summary)].filter(Boolean).join(": ") || "engine event";
    case "engine.finished": {
      const parts = [`${text(p.purpose) ?? "run"} ${event.status ?? "finished"}`];
      const duration = num(p.durationMs);
      if (duration !== null) parts.push(formatDuration(duration));
      if (num(p.turns) !== null) parts.push(`${p.turns} turns`);
      const reason = text(p.errorReason);
      if (reason) parts.push(reason);
      return parts.join(" · ");
    }
    case "engine.retry":
      return `Retrying the engine (attempt ${num(p.attempt) ?? "?"})`;
    case "validation.check": {
      const summary = text(p.summary);
      return `${text(p.check) ?? "check"} ${event.status ?? ""}${summary ? `: ${summary}` : ""}`;
    }
    case "cancel.requested":
      return "Cancel requested";
    case "lane.changed": {
      const reason = text(p.reason);
      return `${event.lane ?? "lane"} lane → ${(event.status ?? "?").toLowerCase()}${reason ? ` (${reason})` : ""}`;
    }
    case "inputs.valid":
      return `Inputs valid: ${num(p.pages) ?? "?"} page(s), ${num(p.warnings) ?? 0} warning(s)`;
    case "spec.invalid": {
      const errors = Array.isArray(p.errors) ? (p.errors as Record<string, unknown>[]) : [];
      const first = errors[0];
      const where = first ? ` first: ${[text(first.spec), text(first.path), text(first.message)].filter(Boolean).join(" ")}` : "";
      return `${num(p.total) ?? errors.length} input error(s);${where}`;
    }
    case "contract.ready":
      return `API contract ready: ${num(p.operations) ?? "?"} operation(s), sha256 ${(text(p.sha256) ?? "").slice(0, 12)}`;
    default:
      return `${event.type} ${JSON.stringify(p).slice(0, 120)}`;
  }
}

const timeFormat = new Intl.DateTimeFormat(undefined, {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h23",
});

export function eventTime(event: TGenerationEvent): string {
  return event.ts ? timeFormat.format(new Date(event.ts)) : "";
}

export function isProblem(event: TGenerationEvent): boolean {
  return (
    event.status === "failed" ||
    event.status === "FAILED" ||
    event.type === "engine.retry" ||
    event.type === "spec.invalid" ||
    (event.type === "validation.check" && event.status === "failed") ||
    (event.type === "engine.finished" && event.status !== "ok")
  );
}
