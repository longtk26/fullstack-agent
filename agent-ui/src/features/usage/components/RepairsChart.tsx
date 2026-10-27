"use client";

import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { repairHistogram } from "../lib/breakdown";
import type { TUsageReport } from "../types";

const config = { generations: { label: "Generations", color: "var(--chart-1)" } } satisfies ChartConfig;

type RepairsChartProps = {
  report: TUsageReport;
};

/** How many generations needed 0, 1, 2 or 3+ repair attempts. */
export function RepairsChart({ report }: RepairsChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Repair attempts</CardTitle>
        <CardDescription>Generations by number of repair attempts</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={config} className="h-48 w-full">
          <BarChart data={repairHistogram(report)} margin={{ left: 4, right: 4 }}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="attempts" tickLine={false} axisLine={false} tickMargin={8} />
            <YAxis tickLine={false} axisLine={false} width={32} allowDecimals={false} />
            <ChartTooltip
              content={<ChartTooltipContent labelFormatter={(value) => `${value} repair attempt(s)`} />}
            />
            <Bar dataKey="generations" fill="var(--color-generations)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
