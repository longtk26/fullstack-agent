"use client";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Stack } from "@/components/layout/Stack";
import { useTrace } from "../../hooks/use-trace";
import { useTraceView } from "../../hooks/use-trace-view";
import type { TGenerationDetail, TGenerationEvent } from "../../types";
import { NodeUsageTable } from "./NodeUsageTable";
import { SpanDrawer } from "./SpanDrawer";
import { TraceFilters } from "./TraceFilters";
import { TraceSummary } from "./TraceSummary";
import { TraceWaterfall } from "./TraceWaterfall";

type TraceTabProps = {
  detail: TGenerationDetail;
  events: TGenerationEvent[];
};

/** Story 9.4: totals, per-node summary and the span waterfall of one generation, live while it runs. */
export function TraceTab({ detail, events }: TraceTabProps) {
  const { trace, now } = useTrace(detail.generationId, detail.status, events);
  const view = useTraceView(trace.data, now);

  if (trace.isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Could not load the trace</AlertTitle>
        <AlertDescription>{trace.error.message}</AlertDescription>
      </Alert>
    );
  }
  if (!trace.data) return <Skeleton className="h-[640px] w-full" />;

  return (
    <Stack gap="lg">
      <TraceSummary usage={trace.data.usage} langsmithUrl={trace.data.langsmithUrl} />
      {view.nodes.length > 0 && (
        <Stack gap="sm">
          <h2 className="text-sm font-medium">Per node</h2>
          <NodeUsageTable nodes={view.nodes} sort={view.sort} onSort={view.sortBy} />
        </Stack>
      )}
      <Stack gap="sm">
        <h2 className="text-sm font-medium">Spans</h2>
        <TraceFilters filters={view.filters} lanes={view.lanes} onChange={view.setFilters} onReset={view.resetFilters} />
        <TraceWaterfall
          rows={view.rows}
          range={view.range}
          now={now}
          selectedId={view.selected?.spanId ?? null}
          onToggle={view.toggle}
          onSelect={view.select}
        />
      </Stack>
      <SpanDrawer
        generationId={detail.generationId}
        span={view.selected}
        langsmithUrl={trace.data.langsmithUrl}
        onClose={() => view.select(null)}
      />
    </Stack>
  );
}
