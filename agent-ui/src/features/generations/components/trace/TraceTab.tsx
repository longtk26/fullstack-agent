"use client";

import { Sparkles } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Stack } from "@/components/layout/Stack";
import { useSpecDraft } from "@/features/specs/hooks/use-spec-queries";
import { formatTokens } from "@/lib/format-usage";
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

/** Story 9.4 & 19.10: totals, drafting usage, per-node summary and the span waterfall of one generation. */
export function TraceTab({ detail, events }: TraceTabProps) {
  const { trace, now } = useTrace(detail.generationId, detail.status, events);
  const view = useTraceView(trace.data, now);
  const draftQuery = useSpecDraft(detail.options?.draftId ?? null);
  const draftUsage = draftQuery.data?.usage as
    | {
        calls?: number;
        input_tokens?: number;
        output_tokens?: number;
        costUsd?: number;
        cost_usd?: number;
        images?: { count?: number; cached?: number; costUsd?: number };
      }
    | undefined;

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
      {draftUsage && (
        <Card size="sm" className="border-muted bg-muted/20">
          <CardHeader className="py-2.5">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Sparkles className="size-3.5 text-primary" />
              Drafting Usage
            </CardTitle>
          </CardHeader>
          <CardContent className="py-2">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div>
                <span className="text-xs text-muted-foreground block">Drafting engine calls</span>
                <span className="text-sm font-semibold tabular-nums">{draftUsage.calls ?? 0}</span>
              </div>
              <div>
                <span className="text-xs text-muted-foreground block">Tokens in / out</span>
                <span className="text-sm font-semibold tabular-nums">
                  {formatTokens(draftUsage.input_tokens ?? 0)} / {formatTokens(draftUsage.output_tokens ?? 0)}
                </span>
              </div>
              {draftUsage.images && (
                <div>
                  <span className="text-xs text-muted-foreground block">Photos generated</span>
                  <span className="text-sm font-semibold tabular-nums">
                    {draftUsage.images.count ?? 0}
                    {draftUsage.images.cached ? ` (${draftUsage.images.cached} cached)` : ""}
                  </span>
                </div>
              )}
              <div>
                <span className="text-xs text-muted-foreground block">Drafting cost</span>
                <span className="text-sm font-semibold tabular-nums">
                  ${Number(draftUsage.costUsd ?? draftUsage.cost_usd ?? 0).toFixed(4)}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
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
