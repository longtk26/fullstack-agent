"use client";

import { useMemo, type ReactNode } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useOperationQuery } from "../bindings";
import { site, type TRecord, type TTreeBinding, type TTreeNode } from "../site";
import { useSectionRecords } from "../use-section-records";

type TMetricProps = { node: TTreeNode; pageId: string; children?: ReactNode } & Record<string, unknown>;
type TRow = { key: string; value: number };

const FUNCTIONS = ["count", "sum", "avg", "min", "max"] as const;
type TFn = (typeof FUNCTIONS)[number];

function fnOf(value: unknown): TFn {
  return (FUNCTIONS as readonly string[]).includes(String(value)) ? (value as TFn) : "count";
}

/** The value of `fn` over `field` of `records` (what the aggregate operation computes on the server). */
export function aggregate(records: TRecord[], fn: TFn, field?: string): number {
  if (fn === "count") return records.length;
  const values = records.map((r) => Number(r[field ?? ""])).filter((v) => Number.isFinite(v));
  if (values.length === 0) return 0;
  if (fn === "sum") return values.reduce((a, b) => a + b, 0);
  if (fn === "avg") return values.reduce((a, b) => a + b, 0) / values.length;
  if (fn === "min") return Math.min(...values);
  return Math.max(...values);
}

function inPeriod(record: TRecord, period: unknown, dateField: unknown): boolean {
  if (period !== "month" && period !== "week" && period !== "day" && period !== "year") return true;
  const field = typeof dateField === "string" ? dateField : Object.keys(record).find((k) => /date|at$/i.test(k));
  const value = field ? record[field] : undefined;
  const date = value ? new Date(String(value)) : null;
  if (!date || Number.isNaN(date.getTime())) return true;
  const now = new Date();
  if (period === "year") return date.getFullYear() === now.getFullYear();
  if (period === "month") return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth();
  if (period === "day") return date.toDateString() === now.toDateString();
  const weekAgo = new Date(now.getTime() - 7 * 86_400_000);
  return date >= weekAgo;
}

/**
 * Records to aggregate in the browser (a static collection, or a list operation when the API declares no aggregate
 * for this figure), or the server's answer (`{value}` / `[{key, value}]`) when it does.
 */
function useAggregate(binding: TTreeBinding | undefined) {
  const server = Boolean(binding?.operationId && !binding.computed);
  const items = binding?.operationId ? undefined : (site.collections[binding?.collection ?? ""] ?? []);
  const list = useSectionRecords(items, server ? undefined : binding, server ? undefined : { limit: 500 });
  const answer = useOperationQuery(server ? binding?.operationId : undefined, {});
  return {
    server,
    records: list.records,
    answer: answer.data as { value?: number } | TRow[] | undefined,
    isLoading: server ? answer.isLoading : list.isLoading,
  };
}

const formats: Record<string, (value: number) => string> = {
  money: (v) => new Intl.NumberFormat(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(v),
  percent: (v) => `${Math.round(v)}%`,
  count: (v) => new Intl.NumberFormat().format(Math.round(v)),
  number: (v) => new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(v),
};

/** One figure: `fn` of `field` over the collection (`count`, `sum`, `avg`, `min`, `max`), with a label and format. */
export function Metric({ node, pageId: _pageId, children: _children, ...props }: TMetricProps) {
  const fn = fnOf(props.fn);
  const field = typeof props.field === "string" ? props.field : undefined;
  const { server, records, answer, isLoading } = useAggregate(node.binding);
  const value = useMemo(() => {
    if (server) return Number((answer as { value?: number } | undefined)?.value ?? 0);
    return aggregate(records.filter((r) => inPeriod(r, props.period, props.dateField)), fn, field);
  }, [server, answer, records, fn, field, props.period, props.dateField]);
  const format = formats[String(props.format ?? (fn === "count" ? "count" : "number"))] ?? formats.number;
  return (
    <div className={typeof props.className === "string" ? props.className : "flex flex-col gap-1"}>
      {typeof props.label === "string" && <span className="text-sm text-muted-foreground">{props.label}</span>}
      <span className="font-heading text-3xl font-semibold tabular-nums" data-metric>
        {isLoading ? "…" : format(value)}
      </span>
    </div>
  );
}

const COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];

/** A chart of `fn` of `field` grouped by `groupBy`: bar, line, area or donut, in the theme's chart colours. */
export function Chart({ node, pageId: _pageId, children: _children, ...props }: TMetricProps) {
  const fn = fnOf(props.fn);
  const field = typeof props.field === "string" ? props.field : undefined;
  const groupBy = typeof props.groupBy === "string" ? props.groupBy : "category";
  const { server, records, answer } = useAggregate(node.binding);
  const series = useMemo<TRow[]>(() => {
    if (server) return Array.isArray(answer) ? answer : [];
    const groups = new Map<string, TRecord[]>();
    for (const record of records.filter((r) => inPeriod(r, props.period, props.dateField))) {
      const key = String(record[groupBy] ?? "—");
      groups.set(key, [...(groups.get(key) ?? []), record]);
    }
    return Array.from(groups, ([key, group]) => ({ key, value: aggregate(group, fn, field) }));
  }, [server, answer, records, groupBy, fn, field, props.period, props.dateField]);
  const kind = String(props.kind ?? "bar");
  const className = typeof props.className === "string" ? props.className : "h-64 w-full";
  return (
    <div className={className} data-chart={kind}>
      <ResponsiveContainer width="100%" height="100%">
        {kind === "donut" ? (
          <PieChart>
            <Pie data={series} dataKey="value" nameKey="key" innerRadius="55%" outerRadius="85%" stroke="none">
              {series.map((_, index) => (
                <Cell key={index} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        ) : kind === "line" ? (
          <LineChart data={series}>
            <XAxis dataKey="key" tickLine={false} axisLine={false} fontSize={12} />
            <YAxis tickLine={false} axisLine={false} fontSize={12} width={40} />
            <Tooltip />
            <Line type="monotone" dataKey="value" stroke={COLORS[0]} strokeWidth={2} dot={false} />
          </LineChart>
        ) : kind === "area" ? (
          <AreaChart data={series}>
            <XAxis dataKey="key" tickLine={false} axisLine={false} fontSize={12} />
            <YAxis tickLine={false} axisLine={false} fontSize={12} width={40} />
            <Tooltip />
            <Area type="monotone" dataKey="value" stroke={COLORS[0]} fill={COLORS[0]} fillOpacity={0.2} />
          </AreaChart>
        ) : (
          <BarChart data={series}>
            <XAxis dataKey="key" tickLine={false} axisLine={false} fontSize={12} />
            <YAxis tickLine={false} axisLine={false} fontSize={12} width={40} />
            <Tooltip />
            <Bar dataKey="value" fill={COLORS[0]} radius={[4, 4, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
