import type { TSpanKind, TTraceSpan } from "../types";

export type TTraceFilters = {
  kinds: TSpanKind[];
  lane: string | null;
  errorsOnly: boolean;
  slowest: number | null;
  search: string;
};

export type TTraceRow = {
  span: TTraceSpan;
  depth: number;
  hasChildren: boolean;
  expanded: boolean;
  match: boolean;
};

export type TTimeWindow = { start: number; end: number };

export const SPAN_KINDS: TSpanKind[] = ["lane", "node", "engine", "llm", "tool", "check", "sandbox"];
/** Model calls and their tools start folded: a real run has hundreds of them. */
export const FOLDED_KINDS: ReadonlySet<TSpanKind> = new Set(["llm"]);

export function spanStart(span: TTraceSpan): number | null {
  return span.startedAt ? Date.parse(span.startedAt) : null;
}

/** End of a span; an open span (running job) ends "now". */
export function spanEnd(span: TTraceSpan, now: number): number | null {
  if (span.endedAt) return Date.parse(span.endedAt);
  return span.startedAt ? now : null;
}

export function timeWindow(spans: TTraceSpan[], now: number): TTimeWindow {
  let start = Infinity;
  let end = -Infinity;
  for (const span of spans) {
    const s = spanStart(span);
    const e = spanEnd(span, now);
    if (s != null) start = Math.min(start, s);
    if (e != null) end = Math.max(end, e);
  }
  if (!Number.isFinite(start)) return { start: now, end: now + 1 };
  return { start, end: Math.max(end, start + 1) };
}

export function childrenByParent(spans: TTraceSpan[]): Map<string | null, TTraceSpan[]> {
  const map = new Map<string | null, TTraceSpan[]>();
  for (const span of spans) {
    const list = map.get(span.parentId) ?? [];
    list.push(span);
    map.set(span.parentId, list);
  }
  for (const list of map.values()) {
    list.sort((a, b) => (spanStart(a) ?? Infinity) - (spanStart(b) ?? Infinity));
  }
  return map;
}

function filtersActive(filters: TTraceFilters): boolean {
  return (
    filters.kinds.length < SPAN_KINDS.length ||
    filters.lane != null ||
    filters.errorsOnly ||
    filters.slowest != null ||
    filters.search.trim() !== ""
  );
}

/** Spans that satisfy the filters, plus every ancestor so they stay in context. */
function visibleIds(spans: TTraceSpan[], filters: TTraceFilters, now: number): { keep: Set<string>; matches: Set<string> } {
  const byId = new Map(spans.map((span) => [span.spanId, span]));
  const search = filters.search.trim().toLowerCase();
  let candidates = spans.filter(
    (span) =>
      span.kind !== "generation" &&
      filters.kinds.includes(span.kind) &&
      (filters.lane == null || span.lane === filters.lane) &&
      (!filters.errorsOnly || span.error) &&
      (!search ||
        span.name.toLowerCase().includes(search) ||
        String(span.attrs.target ?? span.attrs.command ?? "").toLowerCase().includes(search)),
  );
  if (filters.slowest != null) {
    const duration = (span: TTraceSpan) => (spanEnd(span, now) ?? 0) - (spanStart(span) ?? 0);
    candidates = [...candidates].sort((a, b) => duration(b) - duration(a)).slice(0, filters.slowest);
  }
  const matches = new Set(candidates.map((span) => span.spanId));
  const keep = new Set<string>();
  for (const span of candidates) {
    let current: TTraceSpan | undefined = span;
    while (current && !keep.has(current.spanId)) {
      keep.add(current.spanId);
      current = current.parentId ? byId.get(current.parentId) : undefined;
    }
  }
  return { keep, matches };
}

/** Depth-first rows for the waterfall. With filters on, matching spans and their ancestors are shown expanded. */
export function traceRows(
  spans: TTraceSpan[],
  toggled: ReadonlySet<string>,
  filters: TTraceFilters,
  now: number,
): TTraceRow[] {
  const children = childrenByParent(spans);
  const filtering = filtersActive(filters);
  const { keep, matches } = filtering ? visibleIds(spans, filters, now) : { keep: null, matches: null };
  const rows: TTraceRow[] = [];

  const walk = (span: TTraceSpan, depth: number) => {
    if (keep && !keep.has(span.spanId) && span.kind !== "generation") return;
    const kids = (children.get(span.spanId) ?? []).filter((child) => !keep || keep.has(child.spanId));
    const folded = FOLDED_KINDS.has(span.kind) && !filtering;
    const expanded = toggled.has(span.spanId) ? folded : !folded;
    rows.push({
      span,
      depth,
      hasChildren: kids.length > 0,
      expanded,
      match: matches ? matches.has(span.spanId) : true,
    });
    if (expanded) for (const child of kids) walk(child, depth + 1);
  };
  for (const root of children.get(null) ?? []) walk(root, 0);
  return rows;
}
