"use client";

import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { formatUsd } from "@/lib/format-usage";
import { formatDuration } from "@/features/generations/lib/status";
import type { TUsageDay } from "../types";

const dayFormat = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", timeZone: "UTC" });

const costConfig = {
  reported: { label: "Reported", color: "var(--chart-1)" },
  estimated: { label: "Estimated", color: "var(--chart-2)" },
} satisfies ChartConfig;

const timeConfig = {
  minutes: { label: "Wall time", color: "var(--chart-1)" },
} satisfies ChartConfig;

type DailyChartsProps = {
  days: TUsageDay[];
};

/** Cost per day (reported and estimated stacked) and wall time per day: two charts, one axis each. */
export function DailyCharts({ days }: DailyChartsProps) {
  const data = days.map((day) => ({
    day: dayFormat.format(new Date(`${day.date}T00:00:00Z`)),
    reported: day.cost.reported,
    estimated: day.cost.estimated,
    minutes: day.wallMs / 60_000,
    wallMs: day.wallMs,
    generations: day.generations,
  }));
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Cost per day</CardTitle>
          <CardDescription>Estimated cost is tokens × list price (Antigravity reports none)</CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer config={costConfig} className="h-56 w-full">
            <BarChart data={data} margin={{ left: 4, right: 4 }}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="day" tickLine={false} axisLine={false} tickMargin={8} minTickGap={16} />
              <YAxis tickLine={false} axisLine={false} width={52} tickFormatter={(value: number) => formatUsd(value)} />
              <ChartTooltip
                content={
                  <ChartTooltipContent formatter={(value, name) => `${costConfig[name as keyof typeof costConfig]?.label ?? name}: ${formatUsd(Number(value))}`} />
                }
              />
              <ChartLegend content={<ChartLegendContent />} itemSorter={null} />
              <Bar dataKey="reported" stackId="cost" fill="var(--color-reported)" stroke="var(--card)" strokeWidth={2} />
              <Bar
                dataKey="estimated"
                stackId="cost"
                fill="var(--color-estimated)"
                stroke="var(--card)"
                strokeWidth={2}
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ChartContainer>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Wall time per day</CardTitle>
          <CardDescription>Sum of generation durations, in minutes</CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer config={timeConfig} className="h-56 w-full">
            <BarChart data={data} margin={{ left: 4, right: 4 }}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="day" tickLine={false} axisLine={false} tickMargin={8} minTickGap={16} />
              <YAxis tickLine={false} axisLine={false} width={40} allowDecimals={false} />
              <ChartTooltip
                content={
                  <ChartTooltipContent
                    formatter={(_, __, item) =>
                      `${formatDuration(Number(item.payload.wallMs))} · ${item.payload.generations} generation(s)`
                    }
                  />
                }
              />
              <Bar dataKey="minutes" fill="var(--color-minutes)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ChartContainer>
        </CardContent>
      </Card>
    </div>
  );
}
