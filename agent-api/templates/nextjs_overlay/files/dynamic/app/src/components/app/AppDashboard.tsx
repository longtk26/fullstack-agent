"use client";

import { LayoutDashboard } from "lucide-react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { app, enumLabel, listOf, recordTitle, type TAppSection } from "./app";
import { useOperationQuery } from "./bindings";
import { LoadError } from "./AppList";

type TGroup = { key: unknown; value: number };

const numberFormat = new Intl.NumberFormat(app.locale, { maximumFractionDigits: 2 });
const COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];

/** Group keys as people read them: a parent's name for a foreign key (`bikeId` → the bike), an enum's label. */
function useGroupLabels(entityName: string | undefined, groupBy: string | undefined): (key: unknown) => string {
  const entity = app.entities[entityName ?? ""];
  const reference = groupBy ? entity?.references?.[groupBy] : undefined;
  const parent = reference ? app.entities[reference.entity] : undefined;
  const parents = useOperationQuery(parent?.listOperation ?? undefined, { limit: 100 });
  const names = new Map(listOf(parents.data).records.map((record) => [String(record.id), recordTitle(parent, record)]));
  return (key) => {
    if (key === null || key === undefined || key === "") return "None";
    if (reference) return names.get(String(key)) ?? String(key);
    return entity?.fields?.[groupBy ?? ""]?.type === "enum" ? enumLabel(String(key)) : String(key);
  };
}

function Chart({ section, groups }: { section: TAppSection; groups: TGroup[] }) {
  const kind = section.content?.kind ?? "bar";
  const label = useGroupLabels(section.content?.entity, section.content?.groupBy);
  const rows = groups.map((group, index) => ({ name: label(group.key), value: group.value, fill: COLORS[index % COLORS.length] }));
  // Each slice of a pie is named in the legend (its colour per group, from the theme's chart tokens).
  const config: ChartConfig = {
    value: { label: section.content?.label ?? "Value", color: "var(--chart-1)" },
    ...Object.fromEntries(rows.map((row) => [row.name, { label: row.name, color: row.fill }])),
  };
  if (kind === "pie") {
    return (
      <ChartContainer config={config} className="mx-auto aspect-square max-h-72">
        <PieChart>
          <ChartTooltip content={<ChartTooltipContent nameKey="name" hideLabel />} />
          <ChartLegend content={<ChartLegendContent nameKey="name" />} className="flex-wrap gap-2" />
          <Pie data={rows} dataKey="value" nameKey="name" innerRadius="55%" strokeWidth={2}>
            {rows.map((row) => (
              <Cell key={row.name} fill={row.fill} />
            ))}
          </Pie>
        </PieChart>
      </ChartContainer>
    );
  }
  const axes = (
    <>
      <CartesianGrid vertical={false} />
      <XAxis dataKey="name" tickLine={false} axisLine={false} tickMargin={8} interval={0} />
      <YAxis tickLine={false} axisLine={false} width={40} allowDecimals={false} />
      <ChartTooltip content={<ChartTooltipContent />} />
    </>
  );
  return (
    <ChartContainer config={config} className="h-56 w-full">
      {kind === "line" ? (
        <LineChart data={rows}>
          {axes}
          <Line dataKey="value" stroke="var(--color-value)" strokeWidth={2} dot={false} />
        </LineChart>
      ) : kind === "area" ? (
        <AreaChart data={rows}>
          {axes}
          <Area dataKey="value" stroke="var(--color-value)" fill="var(--color-value)" fillOpacity={0.2} />
        </AreaChart>
      ) : (
        <BarChart data={rows}>
          {axes}
          <Bar dataKey="value" fill="var(--color-value)" radius={4} />
        </BarChart>
      )}
    </ChartContainer>
  );
}

/** One dashboard item (Story 22.4): a figure (`{value}`) or a chart of a grouped aggregate (`[{key, value}]`). */
export function AppDashboard({ section }: { section: TAppSection }) {
  const query = useOperationQuery(section.data?.operationId, section.data?.params ?? {});
  const label = section.content?.label ?? "";
  if (!section.data) {
    return (
      <Empty className="border">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <LayoutDashboard aria-hidden />
          </EmptyMedia>
          <EmptyTitle>Nothing here yet</EmptyTitle>
          <EmptyDescription>Figures appear here as the app gets data.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }
  const chart = (section.content?.kind ?? "figure") !== "figure";
  const data = query.data as { value?: number } | TGroup[] | undefined;
  return (
    <Card size="sm" className="h-full">
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        {!chart && (
          <div className="text-3xl leading-tight font-semibold tracking-tight tabular-nums">
            {query.isLoading ? (
              <Skeleton className="h-9 w-20" />
            ) : (
              numberFormat.format(Number((data as { value?: number } | undefined)?.value ?? 0))
            )}
          </div>
        )}
      </CardHeader>
      {chart && (
        <CardContent>
          {query.isLoading ? (
            <Skeleton className="h-56 w-full" />
          ) : query.error ? (
            <LoadError onRetry={() => query.refetch()} />
          ) : Array.isArray(data) && data.length > 0 ? (
            <Chart section={section} groups={data} />
          ) : (
            <p className="py-10 text-center text-sm text-muted-foreground">No data yet</p>
          )}
        </CardContent>
      )}
      {!chart && query.error && (
        <CardContent>
          <p className="text-sm text-destructive">Could not load</p>
        </CardContent>
      )}
    </Card>
  );
}
