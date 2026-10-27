"use client";

import { useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { AlertCircle, ChevronRight, LoaderCircle } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { formatTokens, formatUsd } from "@/lib/format-usage";
import { cn } from "@/lib/utils";
import { KIND_STYLE } from "../../lib/span-style";
import { formatDuration } from "../../lib/status";
import { spanEnd, spanStart, type TTimeWindow, type TTraceRow } from "../../lib/trace-tree";
import type { TSpanKind, TTraceSpan } from "../../types";

const ROW_HEIGHT = 28;
const TICKS = [0, 0.25, 0.5, 0.75, 1];
const LEGEND_KINDS: TSpanKind[] = ["node", "engine", "llm", "tool", "check", "sandbox"];

type TraceWaterfallProps = {
  rows: TTraceRow[];
  range: TTimeWindow;
  now: number;
  selectedId: string | null;
  onToggle: (spanId: string) => void;
  onSelect: (spanId: string) => void;
};

function spanFacts(span: TTraceSpan): string[] {
  const attrs = span.attrs as Record<string, number | string | undefined>;
  const facts: string[] = [];
  if (attrs.model) facts.push(String(attrs.model));
  if (attrs.inputTokens != null) facts.push(`${formatTokens(Number(attrs.inputTokens))} in / ${formatTokens(Number(attrs.outputTokens ?? 0))} out`);
  if (attrs.costUsd != null) facts.push(`${attrs.costSource === "estimated" ? "~" : ""}${formatUsd(Number(attrs.costUsd))}${attrs.costSource === "estimated" ? " est." : ""}`);
  if (attrs.summary) facts.push(String(attrs.summary));
  return facts;
}

export function TraceWaterfall({ rows, range, now, selectedId, onToggle, onSelect }: TraceWaterfallProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Virtual returns non-memoizable functions
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 12,
  });
  const total = range.end - range.start;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground" aria-label="Span kinds">
        {LEGEND_KINDS.map((kind) => (
          <span key={kind} className="inline-flex items-center gap-1.5">
            <span className={cn("h-2 w-3 rounded-sm", KIND_STYLE[kind].bar)} />
            {KIND_STYLE[kind].label}
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5">
          <AlertCircle className="size-3 text-destructive" /> Error
        </span>
      </div>
      <div className="overflow-hidden rounded-lg border">
        <div className="grid grid-cols-[minmax(220px,38%)_1fr] border-b bg-muted/40 text-xs text-muted-foreground">
          <div className="px-3 py-1.5">Span</div>
          <div className="relative h-7">
            {TICKS.map((tick) => (
              <span
                key={tick}
                className={cn("absolute top-1.5 tabular-nums", tick === 1 ? "right-2" : "-translate-x-1/2", tick === 0 && "translate-x-0 pl-2")}
                style={tick === 1 ? undefined : { left: `${tick * 100}%` }}
              >
                {formatDuration(total * tick)}
              </span>
            ))}
          </div>
        </div>
        <div ref={scrollRef} className="max-h-[560px] overflow-auto">
          <div className="relative" style={{ height: virtualizer.getTotalSize() }}>
            {virtualizer.getVirtualItems().map((item) => {
              const row = rows[item.index];
              return (
                <WaterfallRow
                  key={row.span.spanId}
                  row={row}
                  top={item.start}
                  range={range}
                  now={now}
                  selected={row.span.spanId === selectedId}
                  onToggle={onToggle}
                  onSelect={onSelect}
                />
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

type WaterfallRowProps = {
  row: TTraceRow;
  top: number;
  range: TTimeWindow;
  now: number;
  selected: boolean;
  onToggle: (spanId: string) => void;
  onSelect: (spanId: string) => void;
};

function WaterfallRow({ row, top, range, now, selected, onToggle, onSelect }: WaterfallRowProps) {
  const { span, depth } = row;
  const start = spanStart(span);
  const end = spanEnd(span, now);
  const open = span.startedAt != null && span.endedAt == null;
  const total = range.end - range.start;
  const left = start != null ? ((start - range.start) / total) * 100 : 0;
  const width = start != null && end != null ? ((end - start) / total) * 100 : 0;
  const duration = start != null && end != null ? end - start : null;
  const style = KIND_STYLE[span.kind];

  return (
    <div
      className={cn(
        "absolute inset-x-0 grid grid-cols-[minmax(220px,38%)_1fr] items-center border-b border-border/50 text-xs hover:bg-muted/50",
        selected && "bg-muted",
        !row.match && "opacity-60",
      )}
      style={{ top, height: ROW_HEIGHT }}
    >
      <div className="flex min-w-0 items-center gap-1 pr-2" style={{ paddingLeft: 8 + depth * 14 }}>
        {row.hasChildren ? (
          <button
            type="button"
            className="flex size-4 shrink-0 items-center justify-center rounded text-muted-foreground hover:bg-muted"
            aria-label={row.expanded ? "Collapse" : "Expand"}
            onClick={() => onToggle(span.spanId)}
          >
            <ChevronRight className={cn("size-3 transition-transform", row.expanded && "rotate-90")} />
          </button>
        ) : (
          <span className="size-4 shrink-0" />
        )}
        <span className={cn("size-2 shrink-0 rounded-full", style.dot)} aria-hidden />
        <button
          type="button"
          className="min-w-0 flex-1 truncate text-left font-mono hover:underline"
          title={span.name}
          onClick={() => onSelect(span.spanId)}
        >
          {span.name}
        </button>
        {span.error && <AlertCircle className="size-3.5 shrink-0 text-destructive" aria-label="error" />}
        {open && <LoaderCircle className="size-3.5 shrink-0 animate-spin text-muted-foreground" aria-label="running" />}
        <span className="shrink-0 text-muted-foreground tabular-nums">
          {duration != null ? formatDuration(duration) : "—"}
        </span>
      </div>
      <div className="relative h-full">
        {start != null && (
          <Tooltip>
            <TooltipTrigger
              render={
                <button
                  type="button"
                  aria-label={`${span.name}, ${duration != null ? formatDuration(duration) : "no duration"}`}
                  onClick={() => onSelect(span.spanId)}
                  className="absolute top-1/2 h-4 -translate-y-1/2 py-0.5"
                  style={{ left: `${left}%`, width: `max(${width}%, 4px)` }}
                />
              }
            >
              <span
                className={cn(
                  "block h-full w-full rounded-sm",
                  style.bar,
                  span.error && "ring-2 ring-destructive ring-offset-1 ring-offset-background",
                  open && "animate-pulse",
                )}
              />
            </TooltipTrigger>
            <TooltipContent>
              <div className="flex flex-col gap-0.5">
                <span className="font-medium">{span.name}</span>
                <span>
                  {style.label} · {span.status} · {duration != null ? formatDuration(duration) : "—"}
                  {open && " (running)"}
                </span>
                {spanFacts(span).map((fact) => (
                  <span key={fact} className="max-w-80 truncate">
                    {fact}
                  </span>
                ))}
              </div>
            </TooltipContent>
          </Tooltip>
        )}
      </div>
    </div>
  );
}
