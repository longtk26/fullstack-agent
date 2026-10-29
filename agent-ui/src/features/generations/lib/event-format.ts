import { Activity, Ban, Bot, CirclePlay, DatabaseZap, FileCheck, FileJson, Flag, Layers, Puzzle, RotateCcw, ShieldCheck, Terminal, TriangleAlert, WandSparkles } from "lucide-react";
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
  "validation.autofix": WandSparkles,
  "lane.changed": Layers,
  "inputs.valid": FileCheck,
  "spec.invalid": TriangleAlert,
  "contract.ready": FileJson,
  "frontend.plan.ready": FileJson,
  "frontend.scaffold.done": FileCheck,
  "frontend.rendered": FileCheck,
  "component.cache_hit": DatabaseZap,
  "component.generated": Puzzle,
  "component.fallback": TriangleAlert,
  "component.evicted": TriangleAlert,
  "integration.switched_to_live": ShieldCheck,
  "integration.kept_mocks": TriangleAlert,
};

function text(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

function num(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}

function names(value: unknown): string {
  return Array.isArray(value) && value.length ? value.join(", ") : "Component";
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
    case "validation.autofix": {
      const fixed = Array.isArray(p.fixed) ? p.fixed.length : 0;
      const restored = Array.isArray(p.restored) ? p.restored.length : 0;
      const parts = [
        fixed ? `fixed ${fixed} file(s) with ruff / eslint` : null,
        restored ? `restored ${restored} generator-owned file(s)` : null,
      ].filter(Boolean);
      return `Auto-fix before checks: ${parts.join(", ")}`;
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
    case "frontend.plan.ready":
      return `Frontend plan: ${num(p.routes) ?? "?"} route(s), ${num(p.components) ?? "?"} component(s), ${num(p.tests) ?? "?"} test(s)`;
    case "frontend.scaffold.done":
      return `Frontend base ready (${text(p.mode) ?? "?"}): ${num(p.shadcn) ?? "?"} shadcn primitive(s), ${num(p.generated) ?? "?"} generated file(s)`;
    case "frontend.rendered": {
      const calls = num(p.engineCalls) ?? 0;
      const custom = num(p.customComponents);
      const parts = [`${num(p.pages) ?? "?"} page(s)`, `${num(p.sections) ?? "?"} section(s)`];
      if (custom) parts.push(`${custom} custom component(s), ${num(p.cacheHits) ?? 0} from the cache`);
      parts.push(calls ? `${calls} engine call(s)` : "no engine call");
      return `Site rendered from the spec: ${parts.join(", ")}`;
    }
    case "component.cache_hit": {
      const saved = num(p.savedMs);
      return `${names(p.components)} taken from the component cache${saved ? ` (saved ${formatDuration(saved)} of engine time)` : ""}`;
    }
    case "component.generated":
      return `${names(p.components)} generated (${num(p.engineCalls) ?? "?"} engine call(s))${p.cached ? ", passed its checks and cached" : ""}`;
    case "component.fallback": {
      const fallback = Array.isArray(p.fallback) ? p.fallback.join(", ") : "a library section";
      return `${names(p.components)} falls back to ${fallback}: ${text(p.reason) ?? "it could not be generated"}`;
    }
    case "component.evicted":
      return `Evicted ${Array.isArray(p.keys) ? p.keys.length : "?"} cached component(s) that broke the site; generating them again`;
    case "preview.status": {
      const kind = text(p.kind) === "frontend" ? "Site" : "API";
      const detail = text(p.url) ?? text(p.error) ?? text(p.reason);
      return `${kind} preview → ${(event.status ?? "?").toLowerCase()}${detail ? ` (${detail})` : ""}`;
    }
    case "contract.ready":
      return `API contract ready: ${num(p.operations) ?? "?"} operation(s), sha256 ${(text(p.sha256) ?? "").slice(0, 12)}`;
    case "integration.switched_to_live":
      return `Switched frontend preview to live API (${text(p.apiBaseUrl) ?? "backend"})`;
    case "integration.kept_mocks":
      return `Kept frontend preview on mocks (${text(p.reason) ?? "backend unavailable"})`;
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
    event.type === "component.fallback" ||
    event.type === "component.evicted" ||
    (event.type === "validation.check" && event.status === "failed") ||
    (event.type === "engine.finished" && event.status !== "ok")
  );
}
