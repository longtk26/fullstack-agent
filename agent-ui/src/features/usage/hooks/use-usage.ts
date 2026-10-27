"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useCurrentUser } from "@/features/auth/hooks/use-current-user";
import { fetchUsage } from "../api/usage-api";
import { isoDate } from "../lib/breakdown";
import { usageKeys } from "../query-keys";
import type {
  TGenerationFilters,
  TGenerationSortKey,
  TUsageGeneration,
  TUsagePeriod,
  TUsageScope,
} from "../types";

const PERIOD_DAYS: Record<TUsagePeriod, number> = { "7d": 7, "30d": 30, "90d": 90 };
const ALL = "all";

function sortValue(row: TUsageGeneration, key: TGenerationSortKey): number {
  if (key === "createdAt") return row.createdAt ? Date.parse(row.createdAt) : 0;
  if (key === "tokens") return row.tokens.input + row.tokens.output;
  if (key === "cost") return row.cost.total;
  return row[key] ?? 0;
}

/** Usage & traces page (Story 9.10): period and scope drive the report; the table filters and sorts locally. */
export function useUsage() {
  const user = useCurrentUser();
  const [period, setPeriod] = useState<TUsagePeriod>("7d");
  const [scope, setScope] = useState<TUsageScope>("mine");
  const [filters, setFilters] = useState<TGenerationFilters>({ engine: ALL, mode: ALL, status: ALL });
  const [sort, setSort] = useState<{ key: TGenerationSortKey; desc: boolean }>({ key: "createdAt", desc: true });

  const { from, to } = useMemo(() => {
    const end = new Date();
    const start = new Date(end);
    start.setUTCDate(end.getUTCDate() - (PERIOD_DAYS[period] - 1));
    return { from: isoDate(start), to: isoDate(end) };
  }, [period]);

  const report = useQuery({
    queryKey: usageKeys.report(from, to, scope),
    queryFn: () => fetchUsage(from, to, scope),
    refetchInterval: 30_000,
  });

  const generations = useMemo(() => {
    const rows = (report.data?.generations ?? []).filter(
      (row) =>
        (filters.engine === ALL || row.engine === filters.engine) &&
        (filters.mode === ALL || row.mode === filters.mode) &&
        (filters.status === ALL || row.status === filters.status),
    );
    rows.sort((a, b) => (sort.desc ? -1 : 1) * (sortValue(a, sort.key) - sortValue(b, sort.key)));
    return rows;
  }, [report.data, filters, sort]);

  const options = useMemo(() => {
    const rows = report.data?.generations ?? [];
    const unique = (values: string[]) => [...new Set(values)].sort();
    return {
      engines: unique(rows.map((row) => row.engine)),
      modes: unique(rows.map((row) => row.mode)),
      statuses: unique(rows.map((row) => row.status)),
    };
  }, [report.data]);

  return {
    report,
    period,
    setPeriod,
    scope,
    setScope,
    isAdmin: user.data?.role === "ADMIN",
    generations,
    options,
    filters,
    setFilter: (patch: Partial<TGenerationFilters>) => setFilters((current) => ({ ...current, ...patch })),
    sort,
    sortBy: (key: TGenerationSortKey) => setSort((current) => ({ key, desc: current.key === key ? !current.desc : true })),
  };
}
