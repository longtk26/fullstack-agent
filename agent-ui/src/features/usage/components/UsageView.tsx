"use client";

import { ChartColumn } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Stack } from "@/components/layout/Stack";
import { useUsage } from "../hooks/use-usage";
import type { TUsagePeriod, TUsageScope } from "../types";
import { BreakdownCard } from "./BreakdownCard";
import { DailyCharts } from "./DailyCharts";
import { RepairsChart } from "./RepairsChart";
import { UsageGenerationsTable } from "./UsageGenerationsTable";
import { UsageTiles } from "./UsageTiles";

const PERIODS = [
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "90d", label: "Last 90 days" },
];
const SCOPES = [
  { value: "mine", label: "My generations" },
  { value: "all", label: "All users" },
];

/** Story 9.10: time, model calls, tokens and cost of the period, and where they went. */
export function UsageView() {
  const view = useUsage();
  const report = view.report.data;

  return (
    <Stack gap="lg">
      <div className="flex flex-wrap items-center gap-2">
        <Select items={PERIODS} value={view.period} onValueChange={(value) => view.setPeriod(value as TUsagePeriod)}>
          <SelectTrigger className="w-40" aria-label="Period">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PERIODS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {view.isAdmin && (
          <Select items={SCOPES} value={view.scope} onValueChange={(value) => view.setScope(value as TUsageScope)}>
            <SelectTrigger className="w-44" aria-label="Whose generations">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SCOPES.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        {report?.truncated && <span className="text-sm text-muted-foreground">Showing the newest 1000 generations</span>}
      </div>
      {view.report.isError && (
        <Alert variant="destructive">
          <AlertTitle>Could not load usage</AlertTitle>
          <AlertDescription>{view.report.error.message}</AlertDescription>
        </Alert>
      )}
      {!report && !view.report.isError && <Skeleton className="h-[600px] w-full" />}
      {report && report.totals.generations === 0 && (
        <Empty className="border">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <ChartColumn />
            </EmptyMedia>
            <EmptyTitle>No generations in this period</EmptyTitle>
            <EmptyDescription>Pick a longer period, or start a generation.</EmptyDescription>
          </EmptyHeader>
        </Empty>
      )}
      {report && report.totals.generations > 0 && (
        <>
          <UsageTiles totals={report.totals} />
          <DailyCharts days={report.byDay} />
          <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <BreakdownCard report={report} />
            <RepairsChart report={report} />
          </div>
          <Stack gap="sm">
            <h2 className="text-sm font-medium">Generations</h2>
            <UsageGenerationsTable
              rows={view.generations}
              options={view.options}
              filters={view.filters}
              onFilter={view.setFilter}
              sort={view.sort}
              onSort={view.sortBy}
            />
          </Stack>
        </>
      )}
    </Stack>
  );
}
