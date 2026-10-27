"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatUsd } from "@/lib/format-usage";
import { formatDuration, formatStep } from "@/features/generations/lib/status";
import { breakdownRows } from "../lib/breakdown";
import type { TBreakdownDimension, TBreakdownMetric, TUsageReport } from "../types";

const DIMENSIONS: { value: TBreakdownDimension; label: string }[] = [
  { value: "engine", label: "Engine" },
  { value: "model", label: "Model" },
  { value: "node", label: "Node" },
  { value: "lane", label: "Lane" },
];

const config = { value: { label: "Value", color: "var(--chart-1)" } } satisfies ChartConfig;

type BreakdownCardProps = {
  report: TUsageReport;
};

function formatCost(cost: number, estimated: boolean): string {
  return `${estimated ? "~" : ""}${formatUsd(cost)}${estimated ? " (incl. est.)" : ""}`;
}

/** Where time and money go: one bar per engine / model / node / lane, with the numbers in a table below. */
export function BreakdownCard({ report }: BreakdownCardProps) {
  const [dimension, setDimension] = useState<TBreakdownDimension>("node");
  const [metric, setMetric] = useState<TBreakdownMetric>("cost");
  const timeAvailable = dimension !== "model";
  const shown: TBreakdownMetric = timeAvailable ? metric : "cost";
  const rows = breakdownRows(report, dimension)
    .map((row) => ({ ...row, value: shown === "cost" ? row.cost : (row.timeMs ?? 0) / 60_000 }))
    .sort((a, b) => b.value - a.value);
  const perGeneration = dimension === "node";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Where it goes</CardTitle>
        <CardDescription>
          {shown === "cost" ? "Cost" : "Time (minutes)"}
          {perGeneration ? " per generation, averaged" : ", total for the period"}
        </CardDescription>
        <CardAction>
          <Tabs value={shown} onValueChange={(value) => setMetric(value as TBreakdownMetric)}>
            <TabsList>
              <TabsTrigger value="cost">Cost</TabsTrigger>
              <TabsTrigger value="time" disabled={!timeAvailable}>
                Time
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <Tabs value={dimension} onValueChange={(value) => setDimension(value as TBreakdownDimension)}>
          <TabsList>
            {DIMENSIONS.map((option) => (
              <TabsTrigger key={option.value} value={option.value}>
                {option.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        {rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">No data in this period.</p>
        ) : (
          <>
            <ChartContainer config={config} className="w-full" style={{ height: Math.max(120, rows.length * 32 + 24) }}>
              <BarChart data={rows} layout="vertical" margin={{ left: 4, right: 12 }}>
                <CartesianGrid horizontal={false} />
                <XAxis
                  type="number"
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value: number) => (shown === "cost" ? formatUsd(value) : `${Math.round(value)}m`)}
                />
                <YAxis
                  type="category"
                  dataKey="label"
                  tickLine={false}
                  axisLine={false}
                  width={150}
                  tickFormatter={(value: string) => (dimension === "node" ? formatStep(value) : value)}
                />
                <ChartTooltip
                  content={
                    <ChartTooltipContent
                      hideLabel
                      formatter={(_, __, item) =>
                        `${item.payload.label}: ${
                          shown === "cost"
                            ? formatCost(item.payload.cost, item.payload.estimated)
                            : formatDuration(item.payload.timeMs ?? 0)
                        }`
                      }
                    />
                  }
                />
                <Bar dataKey="value" fill="var(--color-value)" radius={[0, 4, 4, 0]} barSize={16} />
              </BarChart>
            </ChartContainer>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{DIMENSIONS.find((option) => option.value === dimension)?.label}</TableHead>
                  <TableHead className="text-right">{perGeneration ? "Avg cost" : "Cost"}</TableHead>
                  <TableHead className="text-right">{perGeneration ? "Avg time" : "Time"}</TableHead>
                  <TableHead className="text-right">Model calls</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row) => (
                  <TableRow key={row.label}>
                    <TableCell className="font-mono text-xs">{dimension === "node" ? formatStep(row.label) : row.label}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatCost(row.cost, row.estimated)}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {row.timeMs == null ? "—" : formatDuration(row.timeMs)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{row.modelCalls}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </>
        )}
      </CardContent>
    </Card>
  );
}
