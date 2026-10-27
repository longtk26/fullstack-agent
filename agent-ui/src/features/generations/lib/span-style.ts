import type { TSpanKind } from "../types";

/** One categorical slot per span kind, in the palette's fixed order (globals.css --chart-*). */
export const KIND_STYLE: Record<TSpanKind, { label: string; bar: string; dot: string }> = {
  generation: { label: "Generation", bar: "bg-muted-foreground/50", dot: "bg-muted-foreground" },
  lane: { label: "Lane", bar: "bg-muted-foreground/40", dot: "bg-muted-foreground" },
  node: { label: "Node", bar: "bg-chart-1", dot: "bg-chart-1" },
  engine: { label: "Engine", bar: "bg-chart-2", dot: "bg-chart-2" },
  llm: { label: "Model call", bar: "bg-chart-3", dot: "bg-chart-3" },
  tool: { label: "Tool", bar: "bg-chart-4", dot: "bg-chart-4" },
  check: { label: "Check", bar: "bg-chart-5", dot: "bg-chart-5" },
  sandbox: { label: "Sandbox", bar: "bg-chart-6", dot: "bg-chart-6" },
};
