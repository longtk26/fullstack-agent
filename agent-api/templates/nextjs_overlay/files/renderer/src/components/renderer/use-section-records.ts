"use client";

import { useParams, useSearchParams } from "next/navigation";
import { useOperationQuery } from "./bindings";
import type { TBinding, TRecord, TRecordLink, TSectionControls } from "./site";

type TRouteParams = Record<string, string | string[] | undefined>;

/** `$route.<name>` values become the current route's parameters; everything else stays as written. */
export function resolveParams(params: Record<string, unknown>, route: TRouteParams): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(params).map(([name, value]) => {
      if (typeof value === "string" && value.startsWith("$route.")) {
        const resolved = route[value.slice("$route.".length)];
        return [name, Array.isArray(resolved) ? resolved[0] : resolved];
      }
      return [name, value];
    }),
  );
}

/** The href of a record's own page, or undefined when the site has none. */
export function recordHref(link: TRecordLink | undefined, record: TRecord): string | undefined {
  if (!link) return undefined;
  return Object.entries(link.params).reduce(
    (href, [param, field]) => href.replace(`[${param}]`, encodeURIComponent(String(record[field] ?? ""))),
    link.route,
  );
}

/**
 * A data section's records: the content collection's `items` (static, already in the page) or the response of its
 * operation (dynamic: the generated client, on mocks or the live backend). `record` is set for get operations.
 */
export function useSectionRecords(
  items: TRecord[] | undefined,
  binding: TBinding | undefined,
  controls?: TSectionControls,
) {
  const route = useParams<TRouteParams>() ?? {};
  const searchParams = useSearchParams();
  const operationId = binding?.operationId;

  const urlParams: Record<string, unknown> = {};
  if (operationId && controls) {
    if (controls.search) {
      const q = searchParams?.get("q");
      if (q) urlParams.q = q;
    }
    for (const filterKey of controls.filters ?? []) {
      const val = searchParams?.get(filterKey);
      if (val && val !== "ALL") urlParams[filterKey] = val;
    }
    if (controls.sort?.length) {
      const sort = searchParams?.get("sort");
      if (sort && sort !== "DEFAULT") urlParams.sort = sort;
    }
    const pageSize = controls.pageSize ?? 10;
    const page = Number(searchParams?.get("page") ?? 1) || 1;
    urlParams.limit = Number(searchParams?.get("limit") ?? pageSize) || pageSize;
    urlParams.offset = searchParams?.has("offset")
      ? Number(searchParams.get("offset"))
      : (page - 1) * (urlParams.limit as number);
  }

  const mergedParams = { ...resolveParams(binding?.params ?? {}, route), ...urlParams };
  const query = useOperationQuery(operationId, mergedParams);

  if (!operationId) {
    return { records: items ?? [], record: undefined, total: items?.length ?? 0, isLoading: false, error: null };
  }

  const data = query.data as
    | { items?: TRecord[]; total?: number; count?: number }
    | TRecord[]
    | TRecord
    | undefined;

  let list: TRecord[] = [];
  let total: number | undefined = undefined;

  if (Array.isArray(data)) {
    list = data;
    total = data.length;
  } else if (data && typeof data === "object") {
    if (Array.isArray((data as { items?: TRecord[] }).items)) {
      list = (data as { items: TRecord[] }).items;
      total = (data as { total?: number }).total ?? (data as { count?: number }).count ?? list.length;
    }
  }

  const record = binding?.action === "get" ? (data as TRecord | undefined) : undefined;
  return { records: list, record, total: total ?? list.length, isLoading: query.isLoading, error: query.error };
}
