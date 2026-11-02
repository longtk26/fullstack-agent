"use client";

import { useParams } from "next/navigation";
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

type TSearchParams = { get(name: string): string | null; has(name: string): boolean };

/**
 * The list parameters a section's controls put in the URL (search, filters, sort, page). Without search params (the
 * static export, before the URL is known) it gives the first page, unfiltered. Read the URL only in a component
 * inside its own `<Suspense>` (see `ControlledRecords`), so pages without controls still render at build time.
 */
export function controlParams(
  controls: TSectionControls | undefined,
  searchParams: TSearchParams | null,
): Record<string, unknown> {
  const urlParams: Record<string, unknown> = {};
  if (!controls) return urlParams;
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
  const limit = Number(searchParams?.get("limit") ?? pageSize) || pageSize;
  urlParams.limit = limit;
  urlParams.offset = searchParams?.has("offset") ? Number(searchParams.get("offset")) : (page - 1) * limit;
  return urlParams;
}

/**
 * A data section's records: the content collection's `items` (static, already in the page) or the response of its
 * operation (dynamic: the generated client, on mocks or the live backend). `record` is set for get operations.
 * `listParams` (from `controlParams`) add the controls' search, filters, sort and page to an operation's request.
 */
export function useSectionRecords(
  items: TRecord[] | undefined,
  binding: TBinding | undefined,
  listParams?: Record<string, unknown>,
) {
  const route = useParams<TRouteParams>() ?? {};
  const operationId = binding?.operationId;

  const mergedParams = { ...resolveParams(binding?.params ?? {}, route), ...(operationId ? listParams : undefined) };
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

export type TSectionRecords = ReturnType<typeof useSectionRecords>;
