"use client";

import { useParams } from "next/navigation";
import { useOperationQuery } from "./bindings";
import type { TBinding, TRecord, TRecordLink } from "./site";

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
export function useSectionRecords(items: TRecord[] | undefined, binding: TBinding | undefined) {
  const route = useParams<TRouteParams>() ?? {};
  const operationId = binding?.operationId;
  const query = useOperationQuery(operationId, resolveParams(binding?.params ?? {}, route));
  if (!operationId) {
    return { records: items ?? [], record: undefined, isLoading: false, error: null };
  }
  const data = query.data as { items?: TRecord[] } | TRecord | undefined;
  const list = data && Array.isArray((data as { items?: TRecord[] }).items) ? (data as { items: TRecord[] }).items : [];
  const record = binding?.action === "get" ? (data as TRecord | undefined) : undefined;
  return { records: list, record, isLoading: query.isLoading, error: query.error };
}
