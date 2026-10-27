"use client";

import { useMemo, useState } from "react";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import type { TNodeUsage } from "@/types/usage";
import { SPAN_KINDS, timeWindow, traceRows, type TTraceFilters } from "../lib/trace-tree";
import type { TTrace, TTraceSpan } from "../types";

export type TNodeSortKey = "node" | "attempts" | "durationMs" | "modelCalls" | "tokens" | "cost";

const DEFAULT_FILTERS: TTraceFilters = { kinds: SPAN_KINDS, lane: null, errorsOnly: false, slowest: null, search: "" };

function sortValue(row: TNodeUsage, key: TNodeSortKey): number | string {
  if (key === "node") return row.node;
  if (key === "tokens") return row.tokens.input + row.tokens.output;
  if (key === "cost") return row.cost.total;
  return row[key];
}

/** View state of the Trace tab: filters, folded spans, the selected span and the node table's sort order. */
export function useTraceView(trace: TTrace | undefined, now: number) {
  const [filters, setFilters] = useState<TTraceFilters>(DEFAULT_FILTERS);
  const [toggled, setToggled] = useState<ReadonlySet<string>>(new Set());
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sort, setSort] = useState<{ key: TNodeSortKey; desc: boolean }>({ key: "durationMs", desc: true });
  const search = useDebouncedValue(filters.search, 200);

  const spans = useMemo(() => trace?.spans ?? [], [trace]);
  const effective = useMemo(() => ({ ...filters, search }), [filters, search]);
  const rows = useMemo(() => traceRows(spans, toggled, effective, now), [spans, toggled, effective, now]);
  const range = useMemo(() => timeWindow(spans, now), [spans, now]);
  const lanes = useMemo(() => [...new Set(spans.map((span) => span.lane))].sort(), [spans]);
  const selected = useMemo<TTraceSpan | null>(
    () => spans.find((span) => span.spanId === selectedId) ?? null,
    [spans, selectedId],
  );
  const nodes = useMemo(() => {
    const rows = [...(trace?.usage.byNode ?? [])];
    rows.sort((a, b) => {
      const left = sortValue(a, sort.key);
      const right = sortValue(b, sort.key);
      const order = typeof left === "string" ? left.localeCompare(String(right)) : left - Number(right);
      return sort.desc ? -order : order;
    });
    return rows;
  }, [trace, sort]);

  return {
    filters,
    setFilters: (patch: Partial<TTraceFilters>) => setFilters((current) => ({ ...current, ...patch })),
    resetFilters: () => setFilters(DEFAULT_FILTERS),
    rows,
    range,
    lanes,
    toggle: (spanId: string) =>
      setToggled((current) => {
        const next = new Set(current);
        if (next.has(spanId)) next.delete(spanId);
        else next.add(spanId);
        return next;
      }),
    selected,
    select: setSelectedId,
    nodes,
    sort,
    sortBy: (key: TNodeSortKey) =>
      setSort((current) => ({ key, desc: current.key === key ? !current.desc : key !== "node" })),
  };
}
